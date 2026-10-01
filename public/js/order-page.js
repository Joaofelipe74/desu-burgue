// Acompanhamento do pedido. O código secreto fica depois do "#" no endereço,
// então não é enviado em logs de servidor nem para outros sites.
import { api, formatDateTime, formatTime, h, money, toast } from './lib.js';

const $ = (sel) => document.querySelector(sel);
const token = decodeURIComponent(location.hash.slice(1));
const FINAL = new Set(['concluido', 'cancelado']);
let timer = null;
let lastStatus = null;

function steps(fulfillment) {
  return [
    ['recebido', 'Pedido recebido'],
    ['em_preparo', 'Em preparo'],
    fulfillment === 'entrega' ? ['saiu_para_entrega', 'Saiu para entrega'] : ['pronto', 'Pronto para retirada'],
    ['concluido', fulfillment === 'entrega' ? 'Entregue' : 'Retirado'],
  ];
}

function render(o) {
  $('#page-status').textContent = '';
  $('#order').hidden = false;
  document.title = `Pedido ${o.code} — Desu Burguer`;
  $('#greeting').textContent = o.customerFirstName ? `Obrigado, ${o.customerFirstName}!` : '';
  $('#order-title').textContent = `Pedido ${o.code}`;
  const pill = $('#status-pill');
  pill.className = `status-pill s-${o.status}`;
  pill.textContent = o.statusLabel;

  const ol = $('#steps');
  ol.textContent = '';
  const when = new Map(o.history.map((x) => [x.status, x.at]));
  if (o.status === 'cancelado') {
    ol.append(
      h('li', { class: 'is-done' }, 'Pedido recebido', h('time', { datetime: when.get('recebido'), text: formatDateTime(when.get('recebido')) })),
      h('li', { class: 'is-current' }, 'Pedido cancelado', h('time', { datetime: when.get('cancelado'), text: formatDateTime(when.get('cancelado')) })),
      h('li', { class: 'muted', text: o.contactPhone ? `Dúvidas? Fale com a loja: ${o.contactPhone}` : 'Em caso de dúvida, fale com a loja.' })
    );
  } else {
    const list = steps(o.fulfillment);
    const idx = list.findIndex(([s]) => s === o.status);
    list.forEach(([s, label], i) => {
      const cls = i < idx ? 'is-done' : i === idx ? 'is-done is-current' : '';
      ol.append(
        h(
          'li',
          { class: cls, 'aria-current': i === idx ? 'step' : undefined },
          label,
          when.get(s) ? h('time', { datetime: when.get(s), text: formatTime(when.get(s)) }) : null
        )
      );
    });
  }

  const items = $('#items');
  items.textContent = '';
  for (const it of o.items) {
    const meta = [it.addons.length ? `+ ${it.addons.map((a) => a.name).join(', ')}` : null, it.notes ? `Obs.: ${it.notes}` : null].filter(Boolean);
    items.append(h('li', {}, h('span', {}, `${it.quantity}× ${it.name}`, meta.map((m) => h('span', { class: 'meta', text: m }))), h('span', { text: money(it.lineTotalCents) })));
  }
  $('#sum-subtotal').textContent = money(o.subtotalCents);
  $('#sum-discount-row').hidden = !o.discountCents;
  $('#sum-discount').textContent = `− ${money(o.discountCents)}${o.couponCode ? ` (${o.couponCode})` : ''}`;
  $('#sum-fee-row').hidden = o.fulfillment !== 'entrega';
  $('#sum-fee').textContent = o.deliveryFeeCents ? money(o.deliveryFeeCents) : 'Grátis';
  $('#sum-total').textContent = money(o.totalCents);
  $('#payment-info').textContent =
    `Pagamento: ${o.paymentMethod}, ${o.fulfillment === 'entrega' ? 'na entrega' : 'na retirada'}.` +
    (o.changeForCents ? ` Troco para ${money(o.changeForCents)}.` : '');

  const pickup = $('#pickup-info');
  pickup.hidden = !o.pickupAddress;
  pickup.textContent = o.pickupAddress ? `Retirada em: ${o.pickupAddress}` : '';
  const contact = $('#contact-info');
  contact.hidden = !o.contactPhone;
  contact.textContent = o.contactPhone ? `Contato da loja: ${o.contactPhone}` : '';

  $('#refresh-note').hidden = FINAL.has(o.status);
  if (lastStatus && lastStatus !== o.status) toast(`Status atualizado: ${o.statusLabel}`);
  lastStatus = o.status;
}

async function load() {
  try {
    const o = await api('/api/orders/track', { body: { token } });
    render(o);
    if (!FINAL.has(o.status)) schedule();
  } catch (err) {
    if (err.status === 404) {
      $('#page-status').textContent = 'Pedido não encontrado. Confira se o link está completo.';
      $('#order').hidden = true;
    } else if (lastStatus) {
      schedule(); // erro temporário: mantém o que já está na tela e tenta de novo
    } else {
      $('#page-status').textContent = err.message;
    }
  }
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    if (document.visibilityState === 'visible') load();
    else schedule();
  }, 20000);
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && lastStatus && !FINAL.has(lastStatus)) load();
});

$('#copy-link').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(location.href);
    toast('Link copiado.');
  } catch {
    toast('Não foi possível copiar. Copie o endereço da barra do navegador.');
  }
});

if (!/^[A-Za-z0-9_-]{32}$/.test(token)) {
  $('#page-status').textContent = 'Link de pedido inválido. Confira se o endereço está completo.';
} else {
  load();
}
