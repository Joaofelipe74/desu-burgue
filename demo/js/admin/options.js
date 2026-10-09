// Aba "Opções": grupos de personalização (ponto da carne, tipo de pão,
// retirar ingredientes, sabores...) e suas escolhas.
import { centsToInput, h, money, parseMoneyToCents, toast } from '../lib.js';
import { adminApi, checkbox, field, flash, sectionTitle, withBusy } from './core.js';

const KIND_LABEL = { single: 'Escolha única', multi: 'Várias escolhas' };

/** "Brioche; 2,00" → { name: 'Brioche', priceCents: 200 } */
function parseChoiceLine(line) {
  const [name, price] = line.split(';').map((s) => s.trim());
  if (!name) return null;
  const priceCents = price ? parseMoneyToCents(price) : 0;
  if (priceCents === null) throw new Error(`Preço inválido em "${line}". Use o formato Nome; 2,00`);
  return { name, priceCents };
}

export function createOptionsTab(panel) {
  const openGroups = new Set(); // grupos abertos continuam abertos depois de salvar
  const alert = h('div', { class: 'alert alert-error', role: 'alert' });
  const list = h('div', { class: 'data-list' });

  // ----- novo grupo -----
  const name = h('input', { type: 'text', maxlength: 60, placeholder: 'Ex.: Ponto da carne' });
  const kind = h('select', {}, h('option', { value: 'single', text: KIND_LABEL.single }), h('option', { value: 'multi', text: KIND_LABEL.multi }));
  const required = checkbox('Obrigatório (o cliente precisa escolher)', true);
  const max = h('input', { type: 'number', min: 1, max: 30, placeholder: 'Sem limite' });
  const choices = h('textarea', { rows: 4, placeholder: 'Uma opção por linha. Preço extra opcional depois de ";"\nAo ponto\nBem passado\nPão brioche; 2,00' });
  const add = h('button', { class: 'btn btn-secondary', type: 'submit', text: 'Criar grupo' });
  const maxField = field('Máximo de escolhas', max, 'só para "várias escolhas"');
  kind.addEventListener('change', () => (maxField.hidden = kind.value !== 'multi'));
  maxField.hidden = true;
  const form = h(
    'form',
    { class: 'card', novalidate: true },
    h('p', {
      class: 'muted small',
      text: 'Grupos de opções aparecem para o cliente ao adicionar o produto. Depois de criar, vincule o grupo aos produtos em Cardápio → Editar.',
    }),
    h('div', { class: 'row row-2' }, field('Nome do grupo', name), field('Tipo', kind)),
    h('div', { class: 'row row-2' }, h('div', { class: 'field' }, required.el), maxField),
    field('Opções', choices),
    add
  );
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    let parsed;
    try {
      parsed = choices.value.split('\n').map((l) => l.trim()).filter(Boolean).map(parseChoiceLine).filter(Boolean);
    } catch (err) {
      return flash(alert, err.message);
    }
    withBusy(add, async () => {
      await adminApi('/api/admin/option-groups', {
        body: {
          name: name.value,
          kind: kind.value,
          required: required.input.checked,
          maxChoices: kind.value === 'multi' && max.value ? Number(max.value) : null,
          choices: parsed,
        },
      });
      form.reset();
      maxField.hidden = true;
      required.input.checked = true;
      toast('Grupo criado.');
      await load();
    }, alert);
  });

  panel.append(sectionTitle('Opções de personalização'), alert, form, h('div', { class: 'mt-8' }, list));

  async function load() {
    try {
      const { groups } = await adminApi('/api/admin/option-groups');
      list.textContent = '';
      if (!groups.length) list.append(h('p', { class: 'state', text: 'Nenhum grupo de opções ainda.' }));
      for (const g of groups) list.append(groupCard(g));
    } catch (err) {
      flash(alert, err.message);
    }
  }

  const putGroup = (g, body, msg) =>
    adminApi(`/api/admin/option-groups/${g.id}`, { method: 'PUT', body })
      .then(() => toast(msg))
      .then(load)
      .catch((err) => flash(alert, err.message));

  const putChoice = (c, body, msg) =>
    adminApi(`/api/admin/option-choices/${c.id}`, { method: 'PUT', body })
      .then(() => toast(msg))
      .then(load)
      .catch((err) => flash(alert, err.message));

  function groupCard(g) {
    const card = h('details', { class: `card option-admin${g.archived ? ' is-archived' : ''}`, open: openGroups.has(g.id) });
    card.addEventListener('toggle', () => (card.open ? openGroups.add(g.id) : openGroups.delete(g.id)));
    const body = h('div', { class: 'option-admin-body' });
    const summary = [
      KIND_LABEL[g.kind],
      g.required ? 'obrigatório' : 'opcional',
      g.kind === 'multi' && g.maxChoices ? `até ${g.maxChoices}` : null,
      `${g.productCount} produto(s)`,
      g.archived ? 'arquivado' : null,
    ]
      .filter(Boolean)
      .join(' · ');

    const header = h(
      'summary',
      {},
      h('span', { class: 'grow' }, h('strong', { text: g.name }), h('span', { class: 'muted small summary-meta', text: summary }))
    );
    const actions = h(
      'div',
      { class: 'toolbar' },
      h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Editar grupo', onclick: () => editGroup() }),
      h('button', {
        class: 'btn btn-secondary btn-small',
        type: 'button',
        text: g.archived ? 'Restaurar' : 'Arquivar',
        onclick: () => putGroup(g, { archived: !g.archived }, g.archived ? 'Grupo restaurado.' : 'Grupo arquivado (some do cardápio).'),
      })
    );

    const choicesList = h('div', { class: 'data-list' });
    for (const c of g.choices) choicesList.append(choiceRow(c));

    const cName = h('input', { type: 'text', maxlength: 60, placeholder: 'Nova opção' });
    const cPrice = h('input', { type: 'text', inputmode: 'decimal', placeholder: '0,00' });
    const cAdd = h('button', { class: 'btn btn-secondary btn-small', type: 'submit', text: 'Adicionar opção' });
    const addForm = h(
      'form',
      { class: 'inline-form mt-8', novalidate: true },
      h('label', { class: 'visually-hidden', for: `nc-${g.id}`, text: 'Nome da nova opção' }),
      Object.assign(cName, { id: `nc-${g.id}` }),
      h('label', { class: 'visually-hidden', for: `np-${g.id}`, text: 'Preço extra' }),
      Object.assign(cPrice, { id: `np-${g.id}` }),
      cAdd
    );
    addForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const priceCents = cPrice.value.trim() ? parseMoneyToCents(cPrice.value) : 0;
      if (priceCents === null) return flash(alert, 'Preço inválido. Use o formato 2,00.');
      withBusy(cAdd, async () => {
        await adminApi(`/api/admin/option-groups/${g.id}/choices`, { body: { name: cName.value, priceCents } });
        toast('Opção adicionada.');
        await load();
      }, alert);
    });

    body.append(actions, choicesList, addForm);
    card.append(header, body);

    function editGroup() {
      body.textContent = '';
      const n = h('input', { type: 'text', value: g.name, maxlength: 60 });
      const k = h(
        'select',
        {},
        h('option', { value: 'single', text: KIND_LABEL.single, selected: g.kind === 'single' }),
        h('option', { value: 'multi', text: KIND_LABEL.multi, selected: g.kind === 'multi' })
      );
      const r = checkbox('Obrigatório', g.required);
      const m = h('input', { type: 'number', min: 1, max: 30, value: g.maxChoices ? String(g.maxChoices) : '' });
      const save = h('button', { class: 'btn btn-primary btn-small', type: 'button', text: 'Salvar' });
      save.addEventListener('click', () =>
        withBusy(save, () =>
          putGroup(
            g,
            { name: n.value, kind: k.value, required: r.input.checked, maxChoices: k.value === 'multi' && m.value ? Number(m.value) : null },
            'Grupo atualizado.'
          ), alert)
      );
      body.append(
        h('div', { class: 'row row-2' }, field('Nome', n), field('Tipo', k)),
        h('div', { class: 'row row-2' }, h('div', { class: 'field' }, r.el), field('Máximo (várias escolhas)', m)),
        h('div', { class: 'toolbar' }, save, h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Cancelar', onclick: load }))
      );
      n.focus();
    }
    return card;
  }

  function choiceRow(c) {
    const row = h('div', { class: `data-item${c.archived ? ' is-archived' : ''}` });
    const view = () => {
      row.textContent = '';
      row.append(
        h('div', { class: 'grow' }, h('span', { text: c.name }), h('span', { class: 'muted small', text: c.priceCents ? `  + ${money(c.priceCents)}` : '  sem custo' })),
        checkbox('Disponível', c.available, {
          disabled: c.archived,
          onchange: (e) => putChoice(c, { available: e.target.checked }, 'Opção atualizada.'),
        }).el,
        h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Editar', onclick: edit }),
        h('button', {
          class: 'btn btn-secondary btn-small',
          type: 'button',
          text: c.archived ? 'Restaurar' : 'Arquivar',
          onclick: () => putChoice(c, { archived: !c.archived }, c.archived ? 'Opção restaurada.' : 'Opção arquivada.'),
        })
      );
    };
    const edit = () => {
      row.textContent = '';
      const n = h('input', { type: 'text', value: c.name, maxlength: 60 });
      const p = h('input', { type: 'text', inputmode: 'decimal', value: centsToInput(c.priceCents) });
      const save = h('button', { class: 'btn btn-primary btn-small', type: 'button', text: 'Salvar' });
      save.addEventListener('click', () => {
        const priceCents = parseMoneyToCents(p.value || '0');
        if (priceCents === null) return flash(alert, 'Preço inválido.');
        withBusy(save, () => putChoice(c, { name: n.value, priceCents }, 'Opção atualizada.'), alert);
      });
      row.append(
        h('div', { class: 'grow' }, field('Nome', n)),
        field('Preço extra (R$)', p),
        save,
        h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Cancelar', onclick: view })
      );
      n.focus();
    };
    view();
    return row;
  }

  return { start: load };
}
