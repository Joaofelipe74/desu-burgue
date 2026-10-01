// Cupons de desconto (cadastrados pelo administrador; nenhum vem pronto).
import { badRequest, conflict, notFound } from '../http/errors.js';
import { boolean, integer, oneOf, onlyKeys, text } from '../validation.js';

export function normalizeCouponCode(value) {
  if (value === undefined || value === null || value === '') return '';
  if (typeof value !== 'string') throw badRequest('Cupom inválido.');
  const code = value.trim().toUpperCase();
  if (!/^[A-Z0-9]{3,20}$/.test(code)) throw badRequest('Cupom inválido. Use de 3 a 20 letras ou números.');
  return code;
}

export function findCoupon(db, code) {
  if (!code) return null;
  return db.prepare('SELECT * FROM coupons WHERE code = ?').get(code) || null;
}

const toApi = (c) => ({
  id: c.id,
  code: c.code,
  kind: c.kind,
  value: c.value,
  minOrderCents: c.min_order_cents,
  maxUses: c.max_uses,
  uses: c.uses,
  validUntil: c.valid_until,
  active: c.active === 1,
  createdAt: c.created_at,
});

export function listCoupons(db) {
  return db.prepare('SELECT * FROM coupons ORDER BY active DESC, created_at DESC').all().map(toApi);
}

function couponInput(body, partial) {
  onlyKeys(body, ['code', 'kind', 'value', 'minOrderCents', 'maxUses', 'validUntil', 'active'], 'cupom');
  const out = {};
  if (!partial) {
    out.code = normalizeCouponCode(body.code);
    if (!out.code) throw badRequest('Informe o código do cupom.');
  } else if ('code' in body) {
    throw badRequest('O código do cupom não pode ser alterado. Crie um novo cupom.');
  }
  if (!partial || 'kind' in body) out.kind = oneOf(body.kind, ['percent', 'fixed'], { field: 'o tipo do cupom' });
  if (!partial || 'value' in body) {
    out.value = integer(body.value, { field: 'o valor do cupom', min: 1, max: 10000000 });
  }
  if (!partial || 'minOrderCents' in body) {
    out.min_order_cents = integer(body.minOrderCents ?? 0, { field: 'o pedido mínimo do cupom', min: 0, max: 10000000 });
  }
  if (!partial || 'maxUses' in body) {
    out.max_uses = integer(body.maxUses, { field: 'o limite de usos', min: 1, max: 1000000, required: false });
  }
  if (!partial || 'validUntil' in body) {
    const v = text(body.validUntil, { field: 'a validade', max: 10, pattern: /^\d{4}-\d{2}-\d{2}$/, patternMsg: 'Validade inválida (use AAAA-MM-DD).' });
    out.valid_until = v || null;
  }
  if (!partial || 'active' in body) out.active = boolean(body.active ?? true, { field: 'ativo' }) ? 1 : 0;
  return out;
}

export function createCoupon(db, body) {
  const c = couponInput(body, false);
  if (c.kind === 'percent' && c.value > 100) throw badRequest('Cupom percentual deve ser de 1 a 100%.');
  const cols = Object.keys(c);
  try {
    const r = db.prepare(`INSERT INTO coupons (${cols.join(', ')}) VALUES (${cols.map((k) => ':' + k).join(', ')})`).run(c);
    return Number(r.lastInsertRowid);
  } catch (err) {
    if (/UNIQUE/i.test(err.message)) throw conflict('Já existe um cupom com esse código.');
    throw err;
  }
}

export function updateCoupon(db, id, body) {
  const c = couponInput(body, true);
  const existing = db.prepare('SELECT * FROM coupons WHERE id = ?').get(id);
  if (!existing) throw notFound('Cupom não encontrado.');
  const kind = c.kind ?? existing.kind;
  const value = c.value ?? existing.value;
  if (kind === 'percent' && value > 100) throw badRequest('Cupom percentual deve ser de 1 a 100%.');
  const sets = Object.keys(c).map((k) => `${k} = :${k}`);
  if (sets.length) db.prepare(`UPDATE coupons SET ${sets.join(', ')} WHERE id = :id`).run({ ...c, id });
}
