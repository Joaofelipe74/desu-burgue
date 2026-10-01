// Configurações da loja (aberta/fechada, entrega, retirada, taxa, pagamentos).
import { DEFAULT_SETTINGS, transaction } from '../db.js';
import { badRequest } from '../http/errors.js';
import { boolean, integer, onlyKeys, text } from '../validation.js';

export const PAYMENT_LABELS = {
  dinheiro: 'Dinheiro',
  cartao: 'Cartão (maquininha na entrega/retirada)',
  pix: 'Pix (na entrega/retirada)',
};

export function getSettings(db) {
  const rows = db.prepare('SELECT key, value FROM settings').all();
  const out = structuredClone(DEFAULT_SETTINGS);
  for (const { key, value } of rows) {
    if (key in DEFAULT_SETTINGS) out[key] = JSON.parse(value);
  }
  return out;
}

/** Apenas o que o cliente precisa saber (nada interno). */
export function publicSettings(s) {
  return {
    storeName: s.store_name,
    acceptingOrders: s.accepting_orders,
    closedMessage: s.closed_message,
    pickupEnabled: s.pickup_enabled,
    pickupAddress: s.pickup_address,
    deliveryEnabled: s.delivery_enabled,
    deliveryFeeCents: s.delivery_fee_cents,
    minOrderCents: s.min_order_cents,
    paymentMethods: Object.entries(s.payment_methods)
      .filter(([, on]) => on)
      .map(([id]) => ({ id, label: PAYMENT_LABELS[id] })),
    contactPhone: s.contact_phone,
  };
}

export function updateSettings(db, body) {
  onlyKeys(body, Object.keys(DEFAULT_SETTINGS), 'configurações');
  const current = getSettings(db);
  const next = { ...current };
  if ('store_name' in body) next.store_name = text(body.store_name, { field: 'o nome da loja', min: 2, max: 60 });
  if ('accepting_orders' in body) next.accepting_orders = boolean(body.accepting_orders, { field: 'loja aberta' });
  if ('closed_message' in body) next.closed_message = text(body.closed_message, { field: 'a mensagem de loja fechada', max: 200 });
  if ('pickup_enabled' in body) next.pickup_enabled = boolean(body.pickup_enabled, { field: 'retirada' });
  if ('pickup_address' in body) next.pickup_address = text(body.pickup_address, { field: 'o endereço de retirada', max: 200 });
  if ('delivery_enabled' in body) next.delivery_enabled = boolean(body.delivery_enabled, { field: 'entrega' });
  if ('delivery_fee_cents' in body) {
    next.delivery_fee_cents = integer(body.delivery_fee_cents, { field: 'a taxa de entrega', min: 0, max: 100000 });
  }
  if ('min_order_cents' in body) {
    next.min_order_cents = integer(body.min_order_cents, { field: 'o pedido mínimo', min: 0, max: 1000000 });
  }
  if ('contact_phone' in body) next.contact_phone = text(body.contact_phone, { field: 'o telefone de contato', max: 30 });
  if ('payment_methods' in body) {
    const pm = onlyKeys(body.payment_methods, Object.keys(PAYMENT_LABELS), 'formas de pagamento');
    next.payment_methods = { ...current.payment_methods };
    for (const k of Object.keys(pm)) next.payment_methods[k] = boolean(pm[k], { field: `pagamento ${k}` });
  }
  if (!next.pickup_enabled && !next.delivery_enabled) {
    throw badRequest('Ative pelo menos uma opção: entrega ou retirada.');
  }
  if (!Object.values(next.payment_methods).some(Boolean)) {
    throw badRequest('Ative pelo menos uma forma de pagamento.');
  }
  const save = db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value');
  transaction(db, () => {
    for (const [k, v] of Object.entries(next)) save.run(k, JSON.stringify(v));
  });
  return next;
}
