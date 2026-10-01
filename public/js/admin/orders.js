// Aba "Pedidos": lista, atualização automática e mudança de status.
import { formatDateTime, formatTime, h, money } from '../lib.js';
import { adminApi, flash, sectionTitle, withBusy } from './core.js';

const SCOPES = [
  ['abertos', 'Em aberto'],
  ['todos', 'Todos (últimos 100)'],
  ['recebido', 'Recebidos'],
  ['em_preparo', 'Em preparo'],
  ['pronto', 'Prontos para retirada'],
  ['saiu_para_entrega', 'Saiu para entrega'],
  ['concluido', 'Concluídos'],
  ['cancelado', 'Cancelados'],
];

export function createOrdersTab(panel) {
  let scope = 'abertos';
  let timer = null;
  let seen = null; // ids já vistos (para destacar pedidos novos)
  const grid = h('div', { class: 'order-grid', 'aria-live': 'polite' });
  const alert = h('div', { class: 'alert alert-error', role: 'alert' });
  const updated = h('span', { class: 'muted small', role: 'status' });
  const select = h(
    'select',
    { id: 'orders-scope', onchange: (e) => ((scope = e.target.value), (seen = null), load()) },
    SCOPES.map(([v, l]) => h('option', { value: v, text: l }))
  );
  const auto = h('input', { type: 'checkbox', checked: true, id: 'orders-auto' });
  const refreshBtn = h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Atualizar', onclick: () => load() });

  panel.append(
    sectionTitle('Pedidos'),
    h(
      'div',
      { class: 'toolbar' },
      h('label', { for: 'orders-scope', class: 'visually-hidden', text: 'Filtrar pedidos' }),
      select,
      refreshBtn,
      h('label', { class: 'switch' }, auto, h('span', { text: 'Atualizar sozinho' })),
      h('span', { class: 'spacer' }),
      updated
    ),
    alert,
    grid
  );

  async function load() {
    try {
      const data = await adminApi(`/api/admin/orders?scope=${encodeURIComponent(scope)}`);
      render(data.orders);
      alert.textContent = '';
      updated.textContent = `Atualizado às ${formatTime(data.serverTime)}`;
    } catch (err) {
      flash(alert, `Não foi possível carregar os pedidos: ${err.message}`);
    }
  }

  function render(orders) {
    const newIds = seen ? orders.filter((o) => !seen.has(o.id)).map((o) => o.id) : [];
    seen = new Set([...(seen || []), ...orders.map((o) => o.id)]);
    grid.textContent = '';
    if (orders.length === 0) {
      grid.append(h('p', { class: 'state', text: scope === 'abertos' ? 'Nenhum pedido em aberto agora.' : 'Nenhum pedido encontrado.' }));
    }
    for (const o of orders) grid.append(orderCard(o, newIds.includes(o.id)));
    const open = orders.filter((o) => o.status === 'recebido').length;
    document.title = open && scope === 'abertos' ? `(${open}) Pedidos — Painel` : 'Painel — Desu Burguer';
  }

  function orderCard(o, isNew) {
    const addr = o.address;
    const actions = h('div', { class: 'order-actions' });
    for (const next of o.nextStatuses) {
      if (next.status === 'cancelado') {
        const btn = h('button', { class: 'btn btn-danger btn-small', type: 'button', text: 'Cancelar pedido' });
        btn.addEventListener('click', () => {
          if (btn.dataset.confirm === '1') return changeStatus(o, next.status, btn);
          btn.dataset.confirm = '1';
          btn.textContent = 'Confirmar cancelamento';
          setTimeout(() => {
            btn.dataset.confirm = '';
            btn.textContent = 'Cancelar pedido';
          }, 5000);
        });
        actions.append(btn);
      } else {
        actions.append(
          h('button', {
            class: 'btn btn-primary btn-small',
            type: 'button',
            text: `Marcar: ${next.label}`,
            onclick: (e) => changeStatus(o, next.status, e.currentTarget),
          })
        );
      }
    }
    const phoneHref = o.customer.phone ? `tel:+55${o.customer.phone.replace(/\D/g, '')}` : null;
    return h(
      'article',
      { class: `order-card${isNew ? ' is-new' : ''}`, 'aria-labelledby': `o-${o.id}` },
      h(
        'header',
        {},
        h('div', {}, h('h3', { id: `o-${o.id}`, text: `${o.code}${isNew ? ' · novo' : ''}` }), h('span', { class: 'muted small', text: formatDateTime(o.createdAt) })),
        h('span', { class: `status-pill s-${o.status}`, text: o.statusLabel })
      ),
      h('p', { class: 'small' }, h('strong', { text: o.fulfillment === 'entrega' ? 'Entrega' : 'Retirada' }), ` · ${o.paymentLabel}`, o.changeForCents ? ` · troco para ${money(o.changeForCents)}` : ''),
      o.personalDataPurged
        ? h('p', { class: 'muted small', text: 'Dados pessoais removidos (prazo de retenção).' })
        : h(
            'div',
            { class: 'small' },
            h('div', { text: o.customer.name }),
            phoneHref ? h('a', { href: phoneHref, text: formatPhone(o.customer.phone) }) : null,
            addr
              ? h(
                  'div',
                  { class: 'muted' },
                  `${addr.street}, ${addr.number}${addr.complement ? ` — ${addr.complement}` : ''} · ${addr.district}`,
                  addr.reference ? h('div', { text: `Ref.: ${addr.reference}` }) : null
                )
              : null
          ),
      h(
        'ul',
        { class: 'small' },
        o.items.map((it) =>
          h(
            'li',
            {},
            `${it.quantity}× ${it.name}`,
            it.addons.length ? h('span', { class: 'muted', text: ` + ${it.addons.map((a) => a.name).join(', ')}` }) : null,
            it.notes ? h('div', { class: 'muted', text: `Obs.: ${it.notes}` }) : null
          )
        )
      ),
      o.notes ? h('p', { class: 'small alert alert-info', text: `Observações: ${o.notes}` }) : null,
      h(
        'p',
        { class: 'small' },
        h('strong', { text: `Total ${money(o.totalCents)}` }),
        o.discountCents ? ` (desconto ${money(o.discountCents)}${o.couponCode ? `, cupom ${o.couponCode}` : ''})` : '',
        o.deliveryFeeCents ? ` · taxa ${money(o.deliveryFeeCents)}` : ''
      ),
      actions
    );
  }

  async function changeStatus(o, status, button) {
    await withBusy(
      button,
      async () => {
        try {
          await adminApi(`/api/admin/orders/${o.id}/status`, { method: 'PATCH', body: { status, fromStatus: o.status } });
        } finally {
          await load();
        }
      },
      alert
    );
  }

  function start() {
    load();
    clearInterval(timer);
    timer = setInterval(() => {
      if (auto.checked && document.visibilityState === 'visible') load();
    }, 15000);
  }

  function stop() {
    clearInterval(timer);
  }

  return { start, stop, load };
}

function formatPhone(d) {
  const s = String(d || '');
  if (s.length === 11) return `(${s.slice(0, 2)}) ${s.slice(2, 7)}-${s.slice(7)}`;
  if (s.length === 10) return `(${s.slice(0, 2)}) ${s.slice(2, 6)}-${s.slice(6)}`;
  return s;
}
