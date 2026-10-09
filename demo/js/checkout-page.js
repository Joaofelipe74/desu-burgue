// Checkout: dados do cliente, entrega/retirada, pagamento, cupom e revisão.
// Os valores exibidos no resumo vêm do servidor (/api/orders/quote).
import { cart } from './cart.js';
import { api, h, money, optionsText, parseMoneyToCents, uuid } from './lib.js';

const $ = (sel) => document.querySelector(sel);
const form = $('#checkout-form');
let store = null;
let lastQuote = null;
let appliedCoupon = '';
let submitting = false;
// Um identificador por tentativa: se a conexão cair e o cliente clicar de novo,
// o servidor reconhece e não cria pedido duplicado.
let idempotencyKey = uuid();

function fulfillment() {
  return form.querySelector('input[name="fulfillment"]:checked')?.value || null;
}

function payment() {
  return form.querySelector('input[name="payment"]:checked')?.value || null;
}

function setFieldError(id, message) {
  const input = document.getElementById(id);
  const err = document.getElementById(`${id}-error`);
  if (err) err.textContent = message || '';
  if (input) input.setAttribute('aria-invalid', message ? 'true' : 'false');
}

function showFormAlert(message) {
  const el = $('#form-alert');
  el.textContent = message || '';
  if (message) el.focus();
}

// ---------- carregamento ----------

async function init() {
  const status = $('#page-status');
  if (cart.count() === 0) {
    status.textContent = '';
    status.append(h('p', { text: 'Seu carrinho está vazio.' }), h('a', { class: 'btn btn-primary', href: '/desu-burgue/demo/', text: 'Ver cardápio' }));
    return;
  }
  try {
    const menu = await api('/api/menu');
    store = menu.store;
  } catch (err) {
    status.textContent = err.message;
    return;
  }
  document.querySelectorAll('[data-store-name]').forEach((el) => (el.textContent = store.storeName));

  // entrega / retirada conforme configuração da loja
  const pickup = form.querySelector('input[value="retirada"]');
  const delivery = form.querySelector('input[value="entrega"]');
  pickup.disabled = !store.pickupEnabled;
  delivery.disabled = !store.deliveryEnabled;
  $('#delivery-fee-label').textContent = store.deliveryEnabled
    ? store.deliveryFeeCents > 0
      ? `Taxa ${money(store.deliveryFeeCents)}`
      : 'Sem taxa'
    : 'Indisponível no momento';
  if (store.pickupEnabled) pickup.checked = true;
  else if (store.deliveryEnabled) delivery.checked = true;
  if (store.pickupAddress) {
    const pa = $('#pickup-address');
    pa.textContent = `Endereço para retirada: ${store.pickupAddress}`;
  }

  // formas de pagamento habilitadas
  const box = $('#payment-options');
  for (const pm of store.paymentMethods) {
    box.append(
      h('label', { class: 'choice' }, h('input', { type: 'radio', name: 'payment', value: pm.id, required: true }), h('span', { text: pm.label }))
    );
  }

  status.textContent = '';
  form.hidden = false;
  updateVisibility();
  await refreshQuote();
}

function updateVisibility() {
  const f = fulfillment();
  $('#address-box').hidden = f !== 'entrega';
  $('#pickup-address').hidden = f !== 'retirada' || !store?.pickupAddress;
  $('#change-box').hidden = payment() !== 'dinheiro';
}

// ---------- orçamento (valores calculados pelo servidor) ----------

async function refreshQuote({ couponCode = appliedCoupon } = {}) {
  const qs = $('#quote-status');
  qs.textContent = 'Calculando valores…';
  try {
    const q = await api('/api/orders/quote', {
      body: { items: cart.toRequest(), couponCode, fulfillment: fulfillment() || 'retirada' },
    });
    renderQuote(q);
    qs.textContent = '';
    return q;
  } catch (err) {
    qs.textContent = '';
    $('#summary-alert').textContent = err.message;
    lastQuote = null;
    updateSubmitState();
    return null;
  }
}

function renderQuote(q) {
  lastQuote = q;
  const list = $('#summary-items');
  list.textContent = '';
  for (const l of q.lines) {
    const meta = [
      l.options?.length ? optionsText(l.options) : null,
      l.addons.length ? `+ ${l.addons.map((a) => a.name).join(', ')}` : null,
      l.notes ? `Obs.: ${l.notes}` : null,
    ].filter(Boolean);
    list.append(
      h(
        'li',
        {},
        h('span', {}, `${l.quantity}× ${l.name}`, meta.map((m) => h('span', { class: 'meta', text: m }))),
        h('span', { text: money(l.lineTotalCents) })
      )
    );
  }
  $('#sum-subtotal').textContent = money(q.subtotalCents);
  $('#sum-discount-row').hidden = q.discountCents === 0;
  $('#sum-discount').textContent = `− ${money(q.discountCents)}`;
  $('#sum-fee-row').hidden = fulfillment() !== 'entrega';
  $('#sum-fee').textContent = q.deliveryFeeCents ? money(q.deliveryFeeCents) : 'Grátis';
  $('#sum-total').textContent = money(q.totalCents);
  $('#summary-alert').textContent = q.issues.map((i) => i.message).join(' ');

  const msg = $('#coupon-msg');
  if (q.coupon) msg.textContent = `Cupom ${q.coupon.code} aplicado: ${q.coupon.description}.`;
  else if (q.couponError) msg.textContent = q.couponError;
  else msg.textContent = '';
  updateSubmitState();
}

function updateSubmitState() {
  const btn = $('#submit-order');
  const blocked = submitting || !lastQuote || lastQuote.issues.length > 0 || Boolean(lastQuote.couponError);
  btn.disabled = blocked;
  btn.textContent = submitting ? 'Enviando pedido…' : lastQuote ? `Confirmar pedido · ${money(lastQuote.totalCents)}` : 'Confirmar pedido';
}

// ---------- eventos ----------

// Limpa a mensagem de erro do campo assim que o cliente corrige.
form.addEventListener('input', (e) => {
  if (e.target.id && e.target.getAttribute('aria-invalid') === 'true') setFieldError(e.target.id, '');
});

form.addEventListener('change', (e) => {
  if (e.target.name === 'fulfillment') {
    setFieldError('fulfillment', '');
    updateVisibility();
    refreshQuote();
  }
  if (e.target.name === 'payment') {
    setFieldError('payment', '');
    updateVisibility();
  }
});

$('#apply-coupon').addEventListener('click', async () => {
  const code = $('#coupon').value.trim().toUpperCase();
  if (code && !/^[A-Z0-9]{3,20}$/.test(code)) {
    $('#coupon-msg').textContent = 'Cupom inválido. Use de 3 a 20 letras ou números.';
    return;
  }
  appliedCoupon = code;
  const q = await refreshQuote({ couponCode: code });
  if (q?.couponError) {
    // mantém a mensagem, mas recalcula sem o cupom inválido para liberar o pedido
    appliedCoupon = '';
    const msg = q.couponError;
    await refreshQuote({ couponCode: '' });
    $('#coupon-msg').textContent = msg;
  }
});

function validate() {
  let firstInvalid = null;
  const check = (id, ok, message) => {
    setFieldError(id, ok ? '' : message);
    if (!ok && !firstInvalid) firstInvalid = document.getElementById(id) || form.querySelector(`[name="${id}"]`);
  };
  const name = $('#name').value.trim();
  check('name', name.length >= 2, 'Informe seu nome.');
  const digits = $('#phone').value.replace(/\D/g, '').replace(/^55(?=\d{10,11}$)/, '');
  check('phone', /^[1-9]{2}9?\d{8}$/.test(digits), 'Telefone inválido. Use DDD + número.');
  check('fulfillment', Boolean(fulfillment()), 'Escolha entrega ou retirada.');
  if (fulfillment() === 'entrega') {
    check('street', $('#street').value.trim().length >= 3, 'Informe a rua.');
    check('number', $('#number').value.trim().length >= 1, 'Informe o número.');
    check('district', $('#district').value.trim().length >= 2, 'Informe o bairro.');
  }
  check('payment', Boolean(payment()), 'Escolha a forma de pagamento.');
  if (payment() === 'dinheiro' && $('#change').value.trim()) {
    const cents = parseMoneyToCents($('#change').value);
    check('change', cents !== null && (!lastQuote || cents >= lastQuote.totalCents), 'Informe um valor maior ou igual ao total.');
  } else {
    setFieldError('change', '');
  }
  if (firstInvalid) {
    showFormAlert('Confira os campos destacados.');
    firstInvalid.focus();
    return false;
  }
  return true;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (submitting || !lastQuote) return;
  showFormAlert('');
  if (!validate()) return;

  const f = fulfillment();
  const body = {
    idempotencyKey,
    items: cart.toRequest(),
    couponCode: appliedCoupon,
    fulfillment: f,
    customer: { name: $('#name').value.trim(), phone: $('#phone').value.trim() },
    paymentMethod: payment(),
    notes: $('#notes').value.trim(),
    expectedTotalCents: lastQuote.totalCents,
  };
  if (f === 'entrega') {
    body.address = {
      street: $('#street').value.trim(),
      number: $('#number').value.trim(),
      district: $('#district').value.trim(),
      complement: $('#complement').value.trim(),
      reference: $('#reference').value.trim(),
    };
  }
  if (body.paymentMethod === 'dinheiro' && $('#change').value.trim()) {
    body.changeForCents = parseMoneyToCents($('#change').value);
  }

  submitting = true;
  updateSubmitState();
  try {
    const result = await api('/api/orders', { body, timeoutMs: 20000 });
    cart.clear();
    idempotencyKey = uuid();
    location.assign(`/desu-burgue/demo/pedido.html#${encodeURIComponent(result.trackingToken)}`);
    return;
  } catch (err) {
    if (err.status === 409 && err.data.quote) {
      renderQuote(err.data.quote);
      showFormAlert(
        err.data.code === 'total_alterado'
          ? `${err.message} Novo total: ${money(err.data.quote.totalCents)}. Clique em "Confirmar pedido" novamente se estiver de acordo.`
          : err.message
      );
    } else if (err.status === 0) {
      showFormAlert(`${err.message} Se você tentar de novo, não haverá pedido duplicado.`);
    } else {
      showFormAlert(err.message);
    }
  } finally {
    submitting = false;
    updateSubmitState();
  }
});

init();
