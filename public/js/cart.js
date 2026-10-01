// Carrinho guardado no navegador. Guarda só O QUE o cliente escolheu
// (produto, adicionais, quantidade, observação) — nunca preços.
// Os preços exibidos vêm do cardápio e o valor final é calculado pelo servidor.
import { storage } from './lib.js';

const KEY = 'desu.cart.v1';
const MAX_QTY = 20;
const listeners = new Set();

function sanitize(items) {
  if (!Array.isArray(items)) return [];
  return items
    .filter((i) => i && Number.isInteger(i.productId) && Number.isInteger(i.quantity))
    .map((i) => ({
      productId: i.productId,
      addonIds: Array.isArray(i.addonIds) ? i.addonIds.filter(Number.isInteger).sort((a, b) => a - b) : [],
      quantity: Math.min(MAX_QTY, Math.max(1, i.quantity)),
      notes: typeof i.notes === 'string' ? i.notes.slice(0, 140) : '',
    }))
    .slice(0, 30);
}

let items = sanitize(storage.get(KEY, []));

const keyOf = (i) => `${i.productId}|${i.addonIds.join(',')}|${i.notes.trim().toLowerCase()}`;

function save() {
  storage.set(KEY, items);
  for (const fn of listeners) fn(items);
}

export const cart = {
  MAX_QTY,
  items: () => items.map((i) => ({ ...i, addonIds: [...i.addonIds] })),
  count: () => items.reduce((s, i) => s + i.quantity, 0),
  subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
  add(item) {
    const clean = sanitize([item])[0];
    if (!clean) return;
    const existing = items.find((i) => keyOf(i) === keyOf(clean));
    if (existing) existing.quantity = Math.min(MAX_QTY, existing.quantity + clean.quantity);
    else items.push(clean);
    save();
  },
  setQuantity(index, quantity) {
    if (!items[index]) return;
    if (quantity <= 0) items.splice(index, 1);
    else items[index].quantity = Math.min(MAX_QTY, quantity);
    save();
  },
  remove(index) {
    items.splice(index, 1);
    save();
  },
  clear() {
    items = [];
    save();
  },
  /** Para enviar ao servidor (formato exato que a API aceita). */
  toRequest: () => items.map((i) => ({ productId: i.productId, quantity: i.quantity, addonIds: i.addonIds, notes: i.notes })),
};

// Mantém abas abertas sincronizadas.
window.addEventListener('storage', (e) => {
  if (e.key === KEY) {
    items = sanitize(storage.get(KEY, []));
    for (const fn of listeners) fn(items);
  }
});
