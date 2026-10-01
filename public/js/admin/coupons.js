// Aba "Cupons".
import { centsToInput, formatDateTime, h, money, parseMoneyToCents, toast } from '../lib.js';
import { adminApi, checkbox, field, flash, sectionTitle, withBusy } from './core.js';

function describe(c) {
  const value = c.kind === 'percent' ? `${c.value}%` : money(c.value);
  const parts = [`${value} de desconto`];
  if (c.minOrderCents) parts.push(`mínimo ${money(c.minOrderCents)}`);
  parts.push(c.maxUses ? `${c.uses}/${c.maxUses} usos` : `${c.uses} uso(s)`);
  if (c.validUntil) parts.push(`válido até ${c.validUntil.split('-').reverse().join('/')}`);
  return parts.join(' · ');
}

export function createCouponsTab(panel) {
  const alert = h('div', { class: 'alert alert-error', role: 'alert' });
  const list = h('div', { class: 'data-list' });

  const code = h('input', { type: 'text', maxlength: 20, autocapitalize: 'characters', placeholder: 'EX.: BEMVINDO10' });
  const kind = h('select', {}, h('option', { value: 'percent', text: 'Porcentagem (%)' }), h('option', { value: 'fixed', text: 'Valor fixo (R$)' }));
  const value = h('input', { type: 'text', inputmode: 'decimal', placeholder: '10' });
  const minOrder = h('input', { type: 'text', inputmode: 'decimal', placeholder: '0,00' });
  const maxUses = h('input', { type: 'number', min: 1, placeholder: 'Sem limite' });
  const validUntil = h('input', { type: 'date' });
  const add = h('button', { class: 'btn btn-secondary', type: 'submit', text: 'Criar cupom' });
  const form = h(
    'form',
    { class: 'card', novalidate: true },
    h('p', { class: 'muted small', text: 'O desconto vale sobre os produtos (não sobre a taxa de entrega). Um cupom por pedido.' }),
    h('div', { class: 'row row-2' }, field('Código', code, '3 a 20 letras/números'), field('Tipo', kind)),
    h('div', { class: 'row row-2' }, field('Valor', value, '% ou R$'), field('Pedido mínimo (R$)', minOrder, 'opcional')),
    h('div', { class: 'row row-2' }, field('Limite de usos', maxUses, 'opcional'), field('Válido até', validUntil, 'opcional')),
    add
  );

  function readValue() {
    if (kind.value === 'percent') {
      const n = Number(value.value);
      return Number.isInteger(n) && n >= 1 && n <= 100 ? n : null;
    }
    const c = parseMoneyToCents(value.value);
    return c && c > 0 ? c : null;
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const v = readValue();
    if (v === null) return flash(alert, kind.value === 'percent' ? 'Informe uma porcentagem de 1 a 100.' : 'Informe um valor em reais, ex.: 5,00.');
    const min = minOrder.value.trim() ? parseMoneyToCents(minOrder.value) : 0;
    if (min === null) return flash(alert, 'Pedido mínimo inválido.');
    withBusy(add, async () => {
      await adminApi('/api/admin/coupons', {
        body: {
          code: code.value.trim().toUpperCase(),
          kind: kind.value,
          value: v,
          minOrderCents: min,
          maxUses: maxUses.value ? Number(maxUses.value) : null,
          validUntil: validUntil.value || null,
          active: true,
        },
      });
      form.reset();
      toast('Cupom criado.');
      await load();
    }, alert);
  });

  panel.append(sectionTitle('Cupons'), alert, form, h('div', { class: 'mt-8' }, list));

  async function load() {
    try {
      const { coupons } = await adminApi('/api/admin/coupons');
      list.textContent = '';
      if (!coupons.length) list.append(h('p', { class: 'state', text: 'Nenhum cupom cadastrado.' }));
      for (const c of coupons) list.append(row(c));
    } catch (err) {
      flash(alert, err.message);
    }
  }

  function row(c) {
    const el = h('div', { class: `data-item${c.active ? '' : ' is-archived'}` });
    const view = () => {
      el.textContent = '';
      el.append(
        h('div', { class: 'grow' }, h('strong', { text: c.code }), h('div', { class: 'muted small', text: describe(c) }), h('div', { class: 'muted small', text: `Criado em ${formatDateTime(c.createdAt)}` })),
        checkbox('Ativo', c.active, {
          onchange: (e) =>
            adminApi(`/api/admin/coupons/${c.id}`, { method: 'PUT', body: { active: e.target.checked } })
              .then(() => toast(e.target.checked ? 'Cupom ativado.' : 'Cupom desativado.'))
              .then(load)
              .catch((err) => flash(alert, err.message)),
        }).el,
        h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Editar', onclick: edit })
      );
    };
    const edit = () => {
      el.textContent = '';
      const v = h('input', { type: 'text', inputmode: 'decimal', value: c.kind === 'percent' ? String(c.value) : centsToInput(c.value) });
      const mo = h('input', { type: 'text', inputmode: 'decimal', value: centsToInput(c.minOrderCents) });
      const mu = h('input', { type: 'number', min: 1, value: c.maxUses ? String(c.maxUses) : '' });
      const vu = h('input', { type: 'date', value: c.validUntil || '' });
      const save = h('button', { class: 'btn btn-primary btn-small', type: 'button', text: 'Salvar' });
      save.addEventListener('click', () => {
        const value = c.kind === 'percent' ? Number(v.value) : parseMoneyToCents(v.value);
        const min = parseMoneyToCents(mo.value || '0');
        if (!Number.isInteger(value) || value < 1 || min === null) return flash(alert, 'Valores inválidos.');
        withBusy(save, async () => {
          await adminApi(`/api/admin/coupons/${c.id}`, {
            method: 'PUT',
            body: { value, minOrderCents: min, maxUses: mu.value ? Number(mu.value) : null, validUntil: vu.value || null },
          });
          toast('Cupom atualizado.');
          await load();
        }, alert);
      });
      el.append(
        h('strong', { text: c.code }),
        field(c.kind === 'percent' ? 'Valor (%)' : 'Valor (R$)', v),
        field('Pedido mínimo (R$)', mo),
        field('Limite de usos', mu),
        field('Válido até', vu),
        save,
        h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Cancelar', onclick: view })
      );
    };
    view();
    return el;
  }

  return { start: load };
}
