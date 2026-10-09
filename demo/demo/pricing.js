// Cálculo do pedido — feito SEMPRE no servidor, com preços do banco.
// Valores em centavos (inteiros) para evitar erros de arredondamento.
// Módulo puro (sem banco e sem Node): a demonstração estática reaproveita este mesmo cálculo.
import { resolveItemOptions } from './option-rules.js';

const NO_OPTIONS = { groups: new Map(), choices: new Map(), productGroups: new Map() };

export const LIMITS = {
  maxLines: 30, // itens diferentes no carrinho
  maxQuantityPerLine: 20,
  maxTotalUnits: 60,
  maxItemNotes: 140,
};

/** Data de hoje no fuso de São Paulo, no formato AAAA-MM-DD. */
export function todayInSaoPaulo(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(now);
}

/**
 * Verifica se um cupom pode ser usado. Devolve null se estiver ok
 * ou uma mensagem explicando o motivo.
 */
export function couponProblem(coupon, subtotalCents, now = new Date()) {
  if (!coupon || !coupon.active) return 'Cupom inválido ou expirado.';
  if (coupon.valid_until && coupon.valid_until < todayInSaoPaulo(now)) return 'Cupom inválido ou expirado.';
  if (coupon.max_uses !== null && coupon.max_uses !== undefined && coupon.uses >= coupon.max_uses) {
    return 'Este cupom atingiu o limite de usos.';
  }
  if (subtotalCents < coupon.min_order_cents) {
    const min = (coupon.min_order_cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    return `Este cupom vale para pedidos a partir de ${min}.`;
  }
  return null;
}

export function couponDiscount(coupon, subtotalCents) {
  const raw = coupon.kind === 'percent' ? Math.floor((subtotalCents * coupon.value) / 100) : coupon.value;
  return Math.max(0, Math.min(raw, subtotalCents));
}

/**
 * Calcula o pedido.
 * @param items   [{ productId, quantity, addonIds, optionIds, notes }] (já validados quanto ao formato)
 * @param catalog { products: Map, addons: Map, links: Map<productId, Set<addonId>> }
 * @param opts    { fulfillment, settings, coupon, couponCode, now }
 * @returns {{ lines, subtotalCents, discountCents, deliveryFeeCents, totalCents, coupon, issues }}
 *   `issues` lista problemas que impedem fechar o pedido (produto indisponível, loja fechada...).
 */
export function calculateOrder(items, catalog, { fulfillment, settings, coupon = null, couponCode = '', now = new Date() }) {
  const issues = [];
  const lines = [];

  items.forEach((item, index) => {
    const product = catalog.products.get(item.productId);
    if (!product || product.archived || !product.category_active) {
      issues.push({ index, code: 'produto_inexistente', message: 'Um item do carrinho não existe mais no cardápio.' });
      return;
    }
    if (!product.available) {
      issues.push({ index, code: 'produto_indisponivel', message: `${product.name} está indisponível no momento.` });
    }
    const allowed = catalog.links.get(product.id) || new Set();
    const addons = [];
    for (const addonId of item.addonIds) {
      const addon = catalog.addons.get(addonId);
      if (!addon || addon.archived || !allowed.has(addonId)) {
        issues.push({ index, code: 'adicional_invalido', message: `Um adicional de ${product.name} não está mais disponível.` });
        continue;
      }
      if (!addon.available) {
        issues.push({ index, code: 'adicional_indisponivel', message: `O adicional ${addon.name} está indisponível no momento.` });
      }
      addons.push({ id: addon.id, name: addon.name, priceCents: addon.price_cents });
    }
    const opt = resolveItemOptions(product, item.optionIds || [], catalog.options || NO_OPTIONS, index);
    issues.push(...opt.issues);
    const unitPriceCents = product.price_cents + opt.extraCents + addons.reduce((s, a) => s + a.priceCents, 0);
    lines.push({
      index,
      productId: product.id,
      name: product.name,
      basePriceCents: product.price_cents,
      options: opt.options,
      addons,
      unitPriceCents,
      quantity: item.quantity,
      lineTotalCents: unitPriceCents * item.quantity,
      notes: item.notes,
    });
  });

  const subtotalCents = lines.reduce((s, l) => s + l.lineTotalCents, 0);

  if (!settings.accepting_orders) {
    issues.push({ code: 'loja_fechada', message: settings.closed_message || 'A loja está fechada no momento.' });
  }
  if (fulfillment === 'entrega' && !settings.delivery_enabled) {
    issues.push({ code: 'entrega_indisponivel', message: 'No momento não estamos fazendo entregas.' });
  }
  if (fulfillment === 'retirada' && !settings.pickup_enabled) {
    issues.push({ code: 'retirada_indisponivel', message: 'No momento não estamos aceitando retirada no local.' });
  }
  if (lines.length > 0 && subtotalCents < settings.min_order_cents) {
    const min = (settings.min_order_cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    issues.push({ code: 'pedido_minimo', message: `O pedido mínimo é de ${min}.` });
  }

  let discountCents = 0;
  let appliedCoupon = null;
  let couponError = null;
  if (couponCode) {
    couponError = couponProblem(coupon, subtotalCents, now);
    if (!couponError) {
      discountCents = couponDiscount(coupon, subtotalCents);
      appliedCoupon = {
        code: coupon.code,
        description: coupon.kind === 'percent' ? `${coupon.value}% de desconto` : 'Desconto fixo',
      };
    }
  }

  const deliveryFeeCents = fulfillment === 'entrega' ? settings.delivery_fee_cents : 0;
  const totalCents = subtotalCents - discountCents + deliveryFeeCents;

  return { lines, subtotalCents, discountCents, deliveryFeeCents, totalCents, coupon: appliedCoupon, couponError, issues };
}
