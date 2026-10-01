// Testes do cálculo do pedido (regras de preço, cupom, taxa e disponibilidade).
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { DEFAULT_SETTINGS } from '../server/db.js';
import { calculateOrder, couponDiscount, couponProblem, todayInSaoPaulo } from '../server/services/pricing.js';

const settings = { ...DEFAULT_SETTINGS, delivery_enabled: true, delivery_fee_cents: 700 };

function catalog() {
  return {
    products: new Map([
      [1, { id: 1, name: 'X-Bacon', price_cents: 2490, available: true, archived: false, category_active: true }],
      [2, { id: 2, name: 'X-Salada', price_cents: 1990, available: false, archived: false, category_active: true }],
      [3, { id: 3, name: 'Antigo', price_cents: 1000, available: true, archived: true, category_active: true }],
    ]),
    addons: new Map([
      [10, { id: 10, name: 'Bacon extra', price_cents: 400, available: true, archived: false }],
      [11, { id: 11, name: 'Cheddar', price_cents: 350, available: false, archived: false }],
      [12, { id: 12, name: 'Ovo', price_cents: 250, available: true, archived: false }],
    ]),
    links: new Map([[1, new Set([10, 11])]]),
  };
}

const item = (o = {}) => ({ productId: 1, quantity: 1, addonIds: [], notes: '', ...o });

describe('calculateOrder', () => {
  it('soma preço base + adicionais multiplicado pela quantidade', () => {
    const r = calculateOrder([item({ quantity: 3, addonIds: [10] })], catalog(), { fulfillment: 'retirada', settings });
    assert.equal(r.lines[0].unitPriceCents, 2890);
    assert.equal(r.lines[0].lineTotalCents, 8670);
    assert.equal(r.subtotalCents, 8670);
    assert.equal(r.totalCents, 8670);
    assert.deepEqual(r.issues, []);
  });

  it('cobra taxa de entrega só na entrega', () => {
    const entrega = calculateOrder([item()], catalog(), { fulfillment: 'entrega', settings });
    const retirada = calculateOrder([item()], catalog(), { fulfillment: 'retirada', settings });
    assert.equal(entrega.deliveryFeeCents, 700);
    assert.equal(entrega.totalCents, 2490 + 700);
    assert.equal(retirada.deliveryFeeCents, 0);
  });

  it('aponta produto indisponível, arquivado ou inexistente', () => {
    const r = calculateOrder([item({ productId: 2 }), item({ productId: 3 }), item({ productId: 99 })], catalog(), {
      fulfillment: 'retirada',
      settings,
    });
    const codes = r.issues.map((i) => i.code);
    assert.ok(codes.includes('produto_indisponivel'));
    assert.equal(codes.filter((c) => c === 'produto_inexistente').length, 2);
  });

  it('rejeita adicional não vinculado ao produto e aponta adicional indisponível', () => {
    const r = calculateOrder([item({ addonIds: [11, 12] })], catalog(), { fulfillment: 'retirada', settings });
    const codes = r.issues.map((i) => i.code);
    assert.ok(codes.includes('adicional_indisponivel'));
    assert.ok(codes.includes('adicional_invalido'));
    // o adicional não vinculado (Ovo) não entra no preço
    assert.equal(r.lines[0].addons.some((a) => a.id === 12), false);
  });

  it('respeita loja fechada, entrega desativada e pedido mínimo', () => {
    const s = { ...settings, accepting_orders: false, delivery_enabled: false, min_order_cents: 5000 };
    const r = calculateOrder([item()], catalog(), { fulfillment: 'entrega', settings: s });
    const codes = r.issues.map((i) => i.code);
    assert.deepEqual(codes.sort(), ['entrega_indisponivel', 'loja_fechada', 'pedido_minimo']);
  });

  it('aplica cupom percentual (arredondando para baixo) sem descontar a taxa', () => {
    const coupon = { code: 'DEZ', kind: 'percent', value: 10, min_order_cents: 0, max_uses: null, uses: 0, valid_until: null, active: true };
    const r = calculateOrder([item({ quantity: 1 })], catalog(), { fulfillment: 'entrega', settings, coupon, couponCode: 'DEZ' });
    assert.equal(r.discountCents, 249); // 10% de 24,90 = 2,49
    assert.equal(r.totalCents, 2490 - 249 + 700);
    assert.equal(r.coupon.code, 'DEZ');
  });

  it('cupom de valor fixo nunca deixa o subtotal negativo', () => {
    const coupon = { code: 'GRANDE', kind: 'fixed', value: 10000, min_order_cents: 0, max_uses: null, uses: 0, active: true };
    assert.equal(couponDiscount(coupon, 2490), 2490);
  });

  it('recusa cupom expirado, esgotado, inativo ou abaixo do mínimo', () => {
    const base = { kind: 'percent', value: 10, min_order_cents: 0, max_uses: null, uses: 0, valid_until: null, active: true };
    assert.match(couponProblem({ ...base, valid_until: '2000-01-01' }, 5000), /expirado/);
    assert.match(couponProblem({ ...base, max_uses: 2, uses: 2 }, 5000), /limite/);
    assert.match(couponProblem({ ...base, active: false }, 5000), /inválido/);
    assert.match(couponProblem({ ...base, min_order_cents: 6000 }, 5000), /a partir de/);
    assert.equal(couponProblem({ ...base, valid_until: todayInSaoPaulo() }, 5000), null, 'vale até o fim do dia');
    assert.match(couponProblem(null, 5000), /inválido/);
  });
});
