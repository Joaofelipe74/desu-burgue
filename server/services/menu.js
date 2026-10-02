// Cardápio: categorias, produtos e adicionais.
import { nowIso, transaction } from '../db.js';
import { badRequest, conflict, notFound } from '../http/errors.js';
import { boolean, idList, integer, oneOf, onlyKeys, text } from '../validation.js';
import { ILLUSTRATIONS } from './illustrations.js';

const bool = (v) => v === 1;

/** Foto enviada pelo painel; se não houver, a ilustração escolhida; senão null (aviso "Foto em breve"). */
function imageInfo(p) {
  if (p.image_file) {
    return {
      kind: 'upload',
      src: `/uploads/products/${p.image_file}`,
      thumbSrc: p.image_thumb_file ? `/uploads/products/${p.image_thumb_file}` : null,
      width: p.image_width,
      height: p.image_height,
      alt: p.image_alt || p.name,
      illustrative: bool(p.image_is_illustrative),
    };
  }
  if (p.illustration && ILLUSTRATIONS[p.illustration]) {
    return {
      kind: 'illustration',
      src: `/img/ilustracoes/${p.illustration}.svg`,
      thumbSrc: null,
      width: 400,
      height: 300,
      alt: p.image_alt || `Ilustração de ${p.name}`,
      illustrative: true, // desenho nunca é apresentado como foto real
    };
  }
  return null;
}

function addonLinks(db) {
  const links = new Map();
  for (const { product_id, addon_id } of db.prepare('SELECT product_id, addon_id FROM product_addons').all()) {
    if (!links.has(product_id)) links.set(product_id, new Set());
    links.get(product_id).add(addon_id);
  }
  return links;
}

/** Cardápio público: só categorias ativas e produtos não arquivados. */
export function getPublicMenu(db) {
  const categories = db
    .prepare('SELECT id, name FROM categories WHERE active = 1 ORDER BY sort_order, name')
    .all();
  const products = db
    .prepare(
      `SELECT p.* FROM products p JOIN categories c ON c.id = p.category_id
        WHERE p.archived = 0 AND c.active = 1
        ORDER BY p.sort_order, p.name`
    )
    .all();
  const addons = new Map(
    db.prepare('SELECT id, name, price_cents, available FROM addons WHERE archived = 0').all().map((a) => [a.id, a])
  );
  const links = addonLinks(db);

  return categories
    .map((c) => ({
      id: c.id,
      name: c.name,
      products: products
        .filter((p) => p.category_id === c.id)
        .map((p) => ({
          id: p.id,
          name: p.name,
          description: p.description,
          priceCents: p.price_cents,
          available: bool(p.available),
          featured: bool(p.featured),
          image: imageInfo(p),
          addons: [...(links.get(p.id) || [])]
            .map((id) => addons.get(id))
            .filter(Boolean)
            .map((a) => ({ id: a.id, name: a.name, priceCents: a.price_cents, available: bool(a.available) }))
            .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')),
        })),
    }))
    .filter((c) => c.products.length > 0);
}

/** Catálogo completo para o cálculo de preços. */
export function loadCatalog(db) {
  const products = new Map(
    db
      .prepare(
        `SELECT p.id, p.name, p.price_cents, p.available, p.archived, c.active AS category_active
           FROM products p JOIN categories c ON c.id = p.category_id`
      )
      .all()
      .map((p) => [p.id, { ...p, available: bool(p.available), archived: bool(p.archived), category_active: bool(p.category_active) }])
  );
  const addons = new Map(
    db
      .prepare('SELECT id, name, price_cents, available, archived FROM addons')
      .all()
      .map((a) => [a.id, { ...a, available: bool(a.available), archived: bool(a.archived) }])
  );
  return { products, addons, links: addonLinks(db) };
}

// ---------- Administração: categorias ----------

export function listCategories(db) {
  return db
    .prepare(
      `SELECT c.id, c.name, c.sort_order AS sortOrder, c.active,
              (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.archived = 0) AS productCount
         FROM categories c ORDER BY c.sort_order, c.name`
    )
    .all()
    .map((c) => ({ ...c, active: bool(c.active) }));
}

function categoryInput(body, partial) {
  onlyKeys(body, ['name', 'sortOrder', 'active'], 'categoria');
  const out = {};
  if (!partial || 'name' in body) out.name = text(body.name, { field: 'o nome da categoria', min: 1, max: 60 });
  if (!partial || 'sortOrder' in body) out.sort_order = integer(body.sortOrder ?? 0, { field: 'a ordem', min: 0, max: 9999 });
  if (!partial || 'active' in body) out.active = boolean(body.active ?? true, { field: 'ativa' }) ? 1 : 0;
  return out;
}

function uniqueGuard(fn, msg) {
  try {
    return fn();
  } catch (err) {
    if (/UNIQUE constraint failed/i.test(err.message)) throw conflict(msg);
    throw err;
  }
}

export function createCategory(db, body) {
  const c = categoryInput(body, false);
  const r = uniqueGuard(
    () => db.prepare('INSERT INTO categories (name, sort_order, active) VALUES (?, ?, ?)').run(c.name, c.sort_order, c.active),
    'Já existe uma categoria com esse nome.'
  );
  return Number(r.lastInsertRowid);
}

export function updateCategory(db, id, body) {
  const c = categoryInput(body, true);
  const existing = db.prepare('SELECT id FROM categories WHERE id = ?').get(id);
  if (!existing) throw notFound('Categoria não encontrada.');
  const sets = Object.keys(c).map((k) => `${k} = :${k}`);
  if (sets.length === 0) return;
  uniqueGuard(
    () => db.prepare(`UPDATE categories SET ${sets.join(', ')}, updated_at = :now WHERE id = :id`).run({ ...c, now: nowIso(), id }),
    'Já existe uma categoria com esse nome.'
  );
}

export function deleteCategory(db, id) {
  const used = db.prepare('SELECT COUNT(*) AS n FROM products WHERE category_id = ?').get(id).n;
  if (used > 0) {
    throw conflict('Esta categoria tem produtos (inclusive arquivados). Mova-os ou desative a categoria.');
  }
  const r = db.prepare('DELETE FROM categories WHERE id = ?').run(id);
  if (r.changes === 0) throw notFound('Categoria não encontrada.');
}

// ---------- Administração: produtos ----------

export function listProducts(db) {
  const links = addonLinks(db);
  return db
    .prepare(
      `SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON c.id = p.category_id
        ORDER BY p.archived, c.sort_order, p.sort_order, p.name`
    )
    .all()
    .map((p) => ({
      id: p.id,
      categoryId: p.category_id,
      categoryName: p.category_name,
      name: p.name,
      description: p.description,
      priceCents: p.price_cents,
      available: bool(p.available),
      archived: bool(p.archived),
      sortOrder: p.sort_order,
      image: imageInfo(p),
      imageAlt: p.image_alt,
      imageIsIllustrative: bool(p.image_is_illustrative),
      illustration: p.illustration || '',
      featured: bool(p.featured),
      addonIds: [...(links.get(p.id) || [])],
    }));
}

function productInput(db, body, partial) {
  onlyKeys(
    body,
    ['categoryId', 'name', 'description', 'priceCents', 'available', 'archived', 'sortOrder', 'imageAlt', 'imageIsIllustrative', 'addonIds', 'illustration', 'featured'],
    'produto'
  );
  const out = {};
  if (!partial || 'categoryId' in body) {
    out.category_id = integer(body.categoryId, { field: 'a categoria', min: 1, max: 2 ** 31 });
    if (!db.prepare('SELECT id FROM categories WHERE id = ?').get(out.category_id)) throw badRequest('Categoria inexistente.');
  }
  if (!partial || 'name' in body) out.name = text(body.name, { field: 'o nome do produto', min: 1, max: 80 });
  if (!partial || 'description' in body) out.description = text(body.description, { field: 'a descrição', max: 300 });
  if (!partial || 'priceCents' in body) out.price_cents = integer(body.priceCents, { field: 'o preço', min: 0, max: 100000000 });
  if (!partial || 'available' in body) out.available = boolean(body.available ?? true, { field: 'disponível' }) ? 1 : 0;
  if ('archived' in body) out.archived = boolean(body.archived, { field: 'arquivado' }) ? 1 : 0;
  if (!partial || 'sortOrder' in body) out.sort_order = integer(body.sortOrder ?? 0, { field: 'a ordem', min: 0, max: 9999 });
  if (!partial || 'imageAlt' in body) out.image_alt = text(body.imageAlt, { field: 'o texto alternativo da imagem', max: 160 });
  if (!partial || 'imageIsIllustrative' in body) {
    out.image_is_illustrative = boolean(body.imageIsIllustrative ?? true, { field: 'imagem ilustrativa' }) ? 1 : 0;
  }
  if (!partial || 'illustration' in body) {
    const ill = body.illustration ?? '';
    out.illustration = ill === '' ? null : oneOf(ill, Object.keys(ILLUSTRATIONS), { field: 'a ilustração' });
  }
  if (!partial || 'featured' in body) out.featured = boolean(body.featured ?? false, { field: 'destaque' }) ? 1 : 0;
  let addonIds;
  if (!partial || 'addonIds' in body) {
    addonIds = idList(body.addonIds, { field: 'os adicionais', max: 50 });
    for (const id of addonIds) {
      if (!db.prepare('SELECT id FROM addons WHERE id = ?').get(id)) throw badRequest('Adicional inexistente.');
    }
  }
  return { fields: out, addonIds };
}

function setProductAddons(db, productId, addonIds) {
  if (!addonIds) return;
  db.prepare('DELETE FROM product_addons WHERE product_id = ?').run(productId);
  const ins = db.prepare('INSERT INTO product_addons (product_id, addon_id) VALUES (?, ?)');
  for (const a of addonIds) ins.run(productId, a);
}

export function createProduct(db, body) {
  const { fields, addonIds } = productInput(db, body, false);
  return transaction(db, () => {
    const cols = Object.keys(fields);
    const r = db
      .prepare(`INSERT INTO products (${cols.join(', ')}) VALUES (${cols.map((c) => ':' + c).join(', ')})`)
      .run(fields);
    const id = Number(r.lastInsertRowid);
    setProductAddons(db, id, addonIds);
    return id;
  });
}

export function updateProduct(db, id, body) {
  const { fields, addonIds } = productInput(db, body, true);
  transaction(db, () => {
    if (!db.prepare('SELECT id FROM products WHERE id = ?').get(id)) throw notFound('Produto não encontrado.');
    const sets = Object.keys(fields).map((k) => `${k} = :${k}`);
    db.prepare(`UPDATE products SET ${[...sets, 'updated_at = :now'].join(', ')} WHERE id = :id`).run({ ...fields, now: nowIso(), id });
    setProductAddons(db, id, addonIds);
  });
}

export function getProduct(db, id) {
  const p = db.prepare('SELECT * FROM products WHERE id = ?').get(id);
  if (!p) throw notFound('Produto não encontrado.');
  return p;
}

export function setProductImage(db, id, image) {
  db.prepare(
    `UPDATE products SET image_file = ?, image_thumb_file = ?, image_width = ?, image_height = ?, updated_at = ? WHERE id = ?`
  ).run(image?.file ?? null, image?.thumbFile ?? null, image?.width ?? null, image?.height ?? null, nowIso(), id);
}

// ---------- Administração: adicionais ----------

export function listAddons(db) {
  return db
    .prepare('SELECT id, name, price_cents AS priceCents, available, archived FROM addons ORDER BY archived, name')
    .all()
    .map((a) => ({ ...a, available: bool(a.available), archived: bool(a.archived) }));
}

function addonInput(body, partial) {
  onlyKeys(body, ['name', 'priceCents', 'available', 'archived'], 'adicional');
  const out = {};
  if (!partial || 'name' in body) out.name = text(body.name, { field: 'o nome do adicional', min: 1, max: 60 });
  if (!partial || 'priceCents' in body) out.price_cents = integer(body.priceCents, { field: 'o preço', min: 0, max: 10000000 });
  if (!partial || 'available' in body) out.available = boolean(body.available ?? true, { field: 'disponível' }) ? 1 : 0;
  if ('archived' in body) out.archived = boolean(body.archived, { field: 'arquivado' }) ? 1 : 0;
  return out;
}

export function createAddon(db, body) {
  const a = addonInput(body, false);
  const cols = Object.keys(a);
  const r = uniqueGuard(
    () => db.prepare(`INSERT INTO addons (${cols.join(', ')}) VALUES (${cols.map((c) => ':' + c).join(', ')})`).run(a),
    'Já existe um adicional com esse nome.'
  );
  return Number(r.lastInsertRowid);
}

export function updateAddon(db, id, body) {
  const a = addonInput(body, true);
  if (!db.prepare('SELECT id FROM addons WHERE id = ?').get(id)) throw notFound('Adicional não encontrado.');
  const sets = Object.keys(a).map((k) => `${k} = :${k}`);
  uniqueGuard(
    () => db.prepare(`UPDATE addons SET ${[...sets, 'updated_at = :now'].join(', ')} WHERE id = :id`).run({ ...a, now: nowIso(), id }),
    'Já existe um adicional com esse nome.'
  );
}
