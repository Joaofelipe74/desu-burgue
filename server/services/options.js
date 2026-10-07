// Grupos de opções de personalização: "Ponto da carne", "Tipo de pão",
// "Retirar ingredientes", sabores etc. Cada grupo tem escolhas (com preço opcional)
// e é vinculado aos produtos pelo painel. Tudo é validado e somado no servidor.
import { nowIso, transaction } from '../db.js';
import { badRequest, conflict, notFound } from '../http/errors.js';
import { boolean, idList, integer, oneOf, onlyKeys, text } from '../validation.js';

const bool = (v) => v === 1;

function uniqueGuard(fn, msg) {
  try {
    return fn();
  } catch (err) {
    if (/UNIQUE constraint failed/i.test(err.message)) throw conflict(msg);
    throw err;
  }
}

/** Mapas usados no cálculo do pedido e no cardápio público. */
export function loadOptionCatalog(db) {
  const groups = new Map(
    db
      .prepare('SELECT * FROM option_groups')
      .all()
      .map((g) => [g.id, { ...g, required: bool(g.required), archived: bool(g.archived) }])
  );
  const choices = new Map(
    db
      .prepare('SELECT * FROM option_choices ORDER BY sort_order, id')
      .all()
      .map((c) => [c.id, { ...c, available: bool(c.available), archived: bool(c.archived) }])
  );
  const productGroups = new Map();
  for (const row of db.prepare('SELECT product_id, group_id FROM product_option_groups ORDER BY sort_order, group_id').all()) {
    if (!productGroups.has(row.product_id)) productGroups.set(row.product_id, []);
    productGroups.get(row.product_id).push(row.group_id);
  }
  return { groups, choices, productGroups };
}

/** Grupos (não arquivados) de um produto, no formato do cardápio público. */
export function publicGroupsFor(productId, cat) {
  return (cat.productGroups.get(productId) || [])
    .map((gid) => cat.groups.get(gid))
    .filter((g) => g && !g.archived)
    .map((g) => ({
      id: g.id,
      name: g.name,
      kind: g.kind,
      required: g.required,
      maxChoices: g.kind === 'single' ? 1 : g.max_choices,
      choices: [...cat.choices.values()]
        .filter((c) => c.group_id === g.id && !c.archived)
        .map((c) => ({ id: c.id, name: c.name, priceCents: c.price_cents, available: c.available })),
    }))
    .filter((g) => g.choices.length > 0);
}

/**
 * Confere as escolhas de um item. Devolve { options, extraCents, issues }.
 * Regras: a escolha precisa pertencer a um grupo do produto; grupo de escolha única
 * aceita no máximo 1; múltipla respeita o máximo; grupo obrigatório precisa de escolha.
 */
export function resolveItemOptions(product, optionIds, cat, index) {
  const issues = [];
  const byGroup = new Map();
  const allowed = new Set(cat.productGroups.get(product.id) || []);
  for (const cid of optionIds) {
    const choice = cat.choices.get(cid);
    const group = choice && cat.groups.get(choice.group_id);
    if (!choice || choice.archived || !group || group.archived || !allowed.has(group.id)) {
      issues.push({ index, code: 'opcao_invalida', message: `Uma opção de ${product.name} não está mais disponível.` });
      continue;
    }
    if (!choice.available) {
      issues.push({ index, code: 'opcao_indisponivel', message: `A opção "${choice.name}" está indisponível no momento.` });
    }
    if (!byGroup.has(group.id)) byGroup.set(group.id, []);
    byGroup.get(group.id).push(choice);
  }
  const options = [];
  for (const gid of cat.productGroups.get(product.id) || []) {
    const group = cat.groups.get(gid);
    if (!group || group.archived) continue;
    const hasChoices = [...cat.choices.values()].some((c) => c.group_id === gid && !c.archived);
    const chosen = byGroup.get(gid) || [];
    const max = group.kind === 'single' ? 1 : group.max_choices;
    if (group.required && hasChoices && chosen.length === 0) {
      issues.push({ index, code: 'opcao_obrigatoria', message: `Escolha "${group.name}" para ${product.name}.` });
    }
    if (max && chosen.length > max) {
      issues.push({ index, code: 'opcao_excesso', message: `Em "${group.name}" escolha no máximo ${max}.` });
    }
    for (const c of chosen) options.push({ groupName: group.name, choiceId: c.id, name: c.name, priceCents: c.price_cents });
  }
  const extraCents = options.reduce((s, o) => s + o.priceCents, 0);
  return { options, extraCents, issues };
}

// ---------- Administração ----------

export function listOptionGroups(db) {
  const cat = loadOptionCatalog(db);
  const usage = new Map(
    db.prepare('SELECT group_id, COUNT(*) AS n FROM product_option_groups GROUP BY group_id').all().map((r) => [r.group_id, r.n])
  );
  return [...cat.groups.values()]
    .sort((a, b) => Number(a.archived) - Number(b.archived) || a.name.localeCompare(b.name, 'pt-BR'))
    .map((g) => ({
      id: g.id,
      name: g.name,
      kind: g.kind,
      required: g.required,
      maxChoices: g.max_choices,
      archived: g.archived,
      productCount: usage.get(g.id) || 0,
      choices: [...cat.choices.values()]
        .filter((c) => c.group_id === g.id)
        .map((c) => ({ id: c.id, name: c.name, priceCents: c.price_cents, available: c.available, archived: c.archived })),
    }));
}

function groupInput(body, partial) {
  onlyKeys(body, ['name', 'kind', 'required', 'maxChoices', 'archived', 'choices'], 'grupo de opções');
  const out = {};
  if (!partial || 'name' in body) out.name = text(body.name, { field: 'o nome do grupo', min: 1, max: 60 });
  if (!partial || 'kind' in body) out.kind = oneOf(body.kind, ['single', 'multi'], { field: 'o tipo do grupo' });
  if (!partial || 'required' in body) out.required = boolean(body.required ?? false, { field: 'obrigatório' }) ? 1 : 0;
  if (!partial || 'maxChoices' in body) {
    out.max_choices = integer(body.maxChoices, { field: 'o máximo de escolhas', min: 1, max: 30, required: false });
  }
  if ('archived' in body) out.archived = boolean(body.archived, { field: 'arquivado' }) ? 1 : 0;
  if (out.kind === 'single') out.max_choices = null;
  return out;
}

function choiceInput(body, partial) {
  onlyKeys(body, ['name', 'priceCents', 'available', 'archived'], 'opção');
  const out = {};
  if (!partial || 'name' in body) out.name = text(body.name, { field: 'o nome da opção', min: 1, max: 60 });
  if (!partial || 'priceCents' in body) out.price_cents = integer(body.priceCents ?? 0, { field: 'o preço da opção', min: 0, max: 1000000 });
  if (!partial || 'available' in body) out.available = boolean(body.available ?? true, { field: 'disponível' }) ? 1 : 0;
  if ('archived' in body) out.archived = boolean(body.archived, { field: 'arquivada' }) ? 1 : 0;
  return out;
}

function insertChoice(db, groupId, c, sortOrder) {
  return uniqueGuard(
    () =>
      Number(
        db
          .prepare('INSERT INTO option_choices (group_id, name, price_cents, available, sort_order) VALUES (?, ?, ?, ?, ?)')
          .run(groupId, c.name, c.price_cents, c.available, sortOrder).lastInsertRowid
      ),
    'Já existe uma opção com esse nome neste grupo.'
  );
}

export function createOptionGroup(db, body) {
  const g = groupInput(body, false);
  const choices = Array.isArray(body.choices) ? body.choices.slice(0, 30).map((c) => choiceInput(c, false)) : [];
  if (body.choices !== undefined && !Array.isArray(body.choices)) throw badRequest('As opções devem ser uma lista.');
  return transaction(db, () => {
    const id = uniqueGuard(
      () =>
        Number(
          db
            .prepare('INSERT INTO option_groups (name, kind, required, max_choices) VALUES (?, ?, ?, ?)')
            .run(g.name, g.kind, g.required, g.max_choices).lastInsertRowid
        ),
      'Já existe um grupo com esse nome.'
    );
    choices.forEach((c, i) => insertChoice(db, id, c, i + 1));
    return id;
  });
}

export function updateOptionGroup(db, id, body) {
  if (body && 'choices' in body) throw badRequest('Edite as opções individualmente.');
  const g = groupInput(body, true);
  const existing = db.prepare('SELECT * FROM option_groups WHERE id = ?').get(id);
  if (!existing) throw notFound('Grupo não encontrado.');
  if (g.kind === undefined && existing.kind === 'single' && 'max_choices' in g) g.max_choices = null;
  const sets = Object.keys(g).map((k) => `${k} = :${k}`);
  if (!sets.length) return;
  uniqueGuard(
    () => db.prepare(`UPDATE option_groups SET ${[...sets, 'updated_at = :now'].join(', ')} WHERE id = :id`).run({ ...g, now: nowIso(), id }),
    'Já existe um grupo com esse nome.'
  );
}

export function createOptionChoice(db, groupId, body) {
  if (!db.prepare('SELECT id FROM option_groups WHERE id = ?').get(groupId)) throw notFound('Grupo não encontrado.');
  const c = choiceInput(body, false);
  const next = db.prepare('SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM option_choices WHERE group_id = ?').get(groupId).n;
  return insertChoice(db, groupId, c, next);
}

export function updateOptionChoice(db, id, body) {
  const c = choiceInput(body, true);
  if (!db.prepare('SELECT id FROM option_choices WHERE id = ?').get(id)) throw notFound('Opção não encontrada.');
  const sets = Object.keys(c).map((k) => `${k} = :${k}`);
  if (!sets.length) return;
  uniqueGuard(
    () => db.prepare(`UPDATE option_choices SET ${sets.join(', ')} WHERE id = :id`).run({ ...c, id }),
    'Já existe uma opção com esse nome neste grupo.'
  );
}

/** Valida a lista de grupos enviada no cadastro do produto. */
export function parseGroupIds(db, value) {
  const ids = idList(value, { field: 'os grupos de opções', max: 20 });
  for (const id of ids) {
    if (!db.prepare('SELECT id FROM option_groups WHERE id = ?').get(id)) throw badRequest('Grupo de opções inexistente.');
  }
  return ids;
}

export function setProductOptionGroups(db, productId, groupIds) {
  if (!groupIds) return;
  db.prepare('DELETE FROM product_option_groups WHERE product_id = ?').run(productId);
  const ins = db.prepare('INSERT INTO product_option_groups (product_id, group_id, sort_order) VALUES (?, ?, ?)');
  groupIds.forEach((g, i) => ins.run(productId, g, i + 1));
}
