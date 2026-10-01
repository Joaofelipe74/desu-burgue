// Pedidos: orçamento, criação (com proteção contra duplicidade),
// acompanhamento pelo cliente e mudança de status pelo administrador.
import crypto from 'node:crypto';
import { nowIso, transaction } from '../db.js';
import { badRequest, conflict, notFound, HttpError } from '../http/errors.js';
import { integer, idList, oneOf, onlyKeys, phoneBR, text } from '../validation.js';
import { findCoupon, normalizeCouponCode } from './coupons.js';
import { loadCatalog } from './menu.js';
import { calculateOrder, LIMITS } from './pricing.js';
import { getSettings, PAYMENT_LABELS } from './settings.js';

export const STATUS_LABELS = {
  recebido: 'Recebido',
  em_preparo: 'Em preparo',
  pronto: 'Pronto para retirada',
  saiu_para_entrega: 'Saiu para entrega',
  concluido: 'Concluído',
  cancelado: 'Cancelado',
};

const TRANSITIONS = {
  recebido: ['em_preparo', 'cancelado'],
  em_preparo: ['pronto', 'saiu_para_entrega', 'cancelado'],
  pronto: ['concluido', 'cancelado'],
  saiu_para_entrega: ['concluido', 'cancelado'],
  concluido: [],
  cancelado: [],
};

/** Próximos status permitidos para um pedido (depende de entrega/retirada). */
export function nextStatuses(status, fulfillment) {
  return (TRANSITIONS[status] || []).filter((s) => {
    if (s === 'pronto') return fulfillment === 'retirada';
    if (s === 'saiu_para_entrega') return fulfillment === 'entrega';
    return true;
  });
}

export const orderCode = (id) => `#${String(id).padStart(4, '0')}`;

// ---------- entrada ----------

function parseItems(items) {
  if (!Array.isArray(items) || items.length === 0) throw badRequest('Seu carrinho está vazio.');
  if (items.length > LIMITS.maxLines) throw badRequest(`O pedido pode ter no máximo ${LIMITS.maxLines} itens diferentes.`);
  const parsed = items.map((it, i) => {
    onlyKeys(it, ['productId', 'quantity', 'addonIds', 'notes'], `item ${i + 1}`);
    return {
      productId: integer(it.productId, { field: 'o produto', min: 1, max: 2 ** 31 }),
      quantity: integer(it.quantity, { field: 'a quantidade', min: 1, max: LIMITS.maxQuantityPerLine }),
      addonIds: idList(it.addonIds, { field: 'os adicionais', max: 20 }).sort((a, b) => a - b),
      notes: text(it.notes, { field: 'a observação do item', max: LIMITS.maxItemNotes }),
    };
  });
  const units = parsed.reduce((s, it) => s + it.quantity, 0);
  if (units > LIMITS.maxTotalUnits) {
    throw badRequest(`Para pedidos com mais de ${LIMITS.maxTotalUnits} unidades, fale diretamente com a loja.`);
  }
  return parsed;
}

function computeQuote(db, { items, couponCode, fulfillment }) {
  const settings = getSettings(db);
  const catalog = loadCatalog(db);
  const coupon = findCoupon(db, couponCode);
  const result = calculateOrder(items, catalog, { fulfillment, settings, coupon, couponCode });
  return { result, settings, coupon };
}

function quoteResponse(result) {
  return {
    lines: result.lines.map((l) => ({
      index: l.index,
      productId: l.productId,
      name: l.name,
      addons: l.addons,
      unitPriceCents: l.unitPriceCents,
      quantity: l.quantity,
      lineTotalCents: l.lineTotalCents,
      notes: l.notes,
    })),
    subtotalCents: result.subtotalCents,
    discountCents: result.discountCents,
    deliveryFeeCents: result.deliveryFeeCents,
    totalCents: result.totalCents,
    coupon: result.coupon,
    couponError: result.couponError,
    issues: result.issues,
  };
}

/** Orçamento: o navegador mostra estes valores (calculados aqui) na revisão. */
export function quote(db, body) {
  onlyKeys(body, ['items', 'couponCode', 'fulfillment'], 'orçamento');
  const input = {
    items: parseItems(body.items),
    couponCode: normalizeCouponCode(body.couponCode),
    fulfillment: oneOf(body.fulfillment ?? 'retirada', ['entrega', 'retirada'], { field: 'o tipo de pedido' }),
  };
  return quoteResponse(computeQuote(db, input).result);
}

function parseAddress(address) {
  if (!address || typeof address !== 'object') throw badRequest('Informe o endereço de entrega.');
  onlyKeys(address, ['street', 'number', 'district', 'complement', 'reference'], 'endereço');
  return {
    street: text(address.street, { field: 'a rua', min: 3, max: 120 }),
    number: text(address.number, { field: 'o número', min: 1, max: 20 }),
    district: text(address.district, { field: 'o bairro', min: 2, max: 80 }),
    complement: text(address.complement, { field: 'o complemento', max: 80 }),
    reference: text(address.reference, { field: 'o ponto de referência', max: 120 }),
  };
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Cria o pedido. O navegador envia apenas o que o cliente escolheu;
 * preços, descontos e taxa são recalculados aqui. `expectedTotalCents` serve
 * só para confirmar que o cliente viu o mesmo total — se mudou, recusamos.
 */
export function createOrder(db, body, { log = null } = {}) {
  onlyKeys(
    body,
    ['idempotencyKey', 'items', 'couponCode', 'fulfillment', 'customer', 'address', 'paymentMethod', 'changeForCents', 'notes', 'expectedTotalCents'],
    'pedido'
  );
  if (typeof body.idempotencyKey !== 'string' || !UUID.test(body.idempotencyKey)) {
    throw badRequest('Identificador do pedido inválido. Recarregue a página e tente de novo.');
  }
  const idempotencyKey = body.idempotencyKey.toLowerCase();
  const fulfillment = oneOf(body.fulfillment, ['entrega', 'retirada'], { field: 'o tipo de pedido (entrega ou retirada)' });
  const items = parseItems(body.items);
  const couponCode = normalizeCouponCode(body.couponCode);
  onlyKeys(body.customer ?? {}, ['name', 'phone'], 'cliente');
  const customer = {
    name: text(body.customer?.name, { field: 'o seu nome', min: 2, max: 80 }),
    phone: phoneBR(body.customer?.phone),
  };
  const address = fulfillment === 'entrega' ? parseAddress(body.address) : null;
  const paymentMethod = oneOf(body.paymentMethod, Object.keys(PAYMENT_LABELS), { field: 'a forma de pagamento' });
  const notes = text(body.notes, { field: 'as observações do pedido', max: 280, multiline: true });
  const changeForCents =
    paymentMethod === 'dinheiro' ? integer(body.changeForCents, { field: 'o troco', min: 0, max: 10000000, required: false }) : null;
  const expectedTotalCents = integer(body.expectedTotalCents, { field: 'o total esperado', min: 0, max: 10 ** 9 });

  const fingerprint = crypto
    .createHash('sha256')
    .update(JSON.stringify({ items, couponCode, fulfillment, customer, address, paymentMethod, notes, changeForCents }))
    .digest('hex');

  // Pedido repetido (ex.: duplo clique ou conexão que caiu): devolve o mesmo pedido.
  const existing = db.prepare('SELECT * FROM orders WHERE idempotency_key = ?').get(idempotencyKey);
  if (existing) {
    if (existing.request_fingerprint !== fingerprint) {
      throw conflict('Este pedido já foi enviado com outros dados. Recarregue a página para começar um novo.');
    }
    return { replayed: true, order: publicCreated(existing) };
  }

  const { result, settings, coupon } = computeQuote(db, { items, couponCode, fulfillment });
  if (!settings.payment_methods[paymentMethod]) {
    throw badRequest('Esta forma de pagamento não está disponível no momento.');
  }
  if (result.issues.length > 0) {
    throw new HttpError(409, result.issues[0].message, { code: 'pedido_invalido', issues: result.issues, quote: quoteResponse(result) });
  }
  if (couponCode && result.couponError) {
    throw new HttpError(409, result.couponError, { code: 'cupom_invalido', quote: quoteResponse(result) });
  }
  if (result.totalCents !== expectedTotalCents) {
    throw new HttpError(409, 'Os valores do pedido mudaram. Confira o novo total antes de confirmar.', {
      code: 'total_alterado',
      quote: quoteResponse(result),
    });
  }
  if (changeForCents !== null && changeForCents > 0 && changeForCents < result.totalCents) {
    throw badRequest('O valor para troco precisa ser maior ou igual ao total do pedido.');
  }

  const trackingToken = crypto.randomBytes(24).toString('base64url');
  const order = transaction(db, () => {
    if (coupon && result.coupon) {
      const used = db
        .prepare('UPDATE coupons SET uses = uses + 1 WHERE id = ? AND active = 1 AND (max_uses IS NULL OR uses < max_uses)')
        .run(coupon.id);
      if (used.changes !== 1) throw conflict('Este cupom atingiu o limite de usos.');
    }
    const now = nowIso();
    const ins = db
      .prepare(
        `INSERT INTO orders (tracking_token, idempotency_key, request_fingerprint, status, fulfillment,
           customer_name, customer_phone, address_json, notes, payment_method, change_for_cents,
           subtotal_cents, discount_cents, delivery_fee_cents, total_cents, coupon_code, created_at, updated_at)
         VALUES (?, ?, ?, 'recebido', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .run(
        trackingToken,
        idempotencyKey,
        fingerprint,
        fulfillment,
        customer.name,
        customer.phone,
        address ? JSON.stringify(address) : null,
        notes,
        paymentMethod,
        changeForCents || null,
        result.subtotalCents,
        result.discountCents,
        result.deliveryFeeCents,
        result.totalCents,
        result.coupon ? result.coupon.code : null,
        now,
        now
      );
    const orderId = Number(ins.lastInsertRowid);
    const insItem = db.prepare(
      `INSERT INTO order_items (order_id, product_id, product_name, base_price_cents, unit_price_cents, quantity, line_total_cents, notes)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    );
    const insAddon = db.prepare('INSERT INTO order_item_addons (order_item_id, addon_id, addon_name, price_cents) VALUES (?, ?, ?, ?)');
    for (const l of result.lines) {
      const it = insItem.run(orderId, l.productId, l.name, l.basePriceCents, l.unitPriceCents, l.quantity, l.lineTotalCents, l.notes);
      for (const a of l.addons) insAddon.run(Number(it.lastInsertRowid), a.id, a.name, a.priceCents);
    }
    db.prepare('INSERT INTO order_status_history (order_id, from_status, to_status, created_at) VALUES (?, NULL, ?, ?)').run(
      orderId,
      'recebido',
      now
    );
    return db.prepare('SELECT * FROM orders WHERE id = ?').get(orderId);
  });
  log?.info('order_created', { orderId: order.id, totalCents: order.total_cents, fulfillment, items: result.lines.length });
  return { replayed: false, order: publicCreated(order) };
}

function publicCreated(o) {
  return { code: orderCode(o.id), trackingToken: o.tracking_token, status: o.status, totalCents: o.total_cents };
}

function loadItems(db, orderId) {
  const items = db.prepare('SELECT * FROM order_items WHERE order_id = ? ORDER BY id').all(orderId);
  const addons = db.prepare('SELECT addon_name, price_cents FROM order_item_addons WHERE order_item_id = ?');
  return items.map((it) => ({
    name: it.product_name,
    quantity: it.quantity,
    unitPriceCents: it.unit_price_cents,
    lineTotalCents: it.line_total_cents,
    notes: it.notes,
    addons: addons.all(it.id).map((a) => ({ name: a.addon_name, priceCents: a.price_cents })),
  }));
}

function history(db, orderId) {
  return db
    .prepare('SELECT to_status, created_at FROM order_status_history WHERE order_id = ? ORDER BY id')
    .all(orderId)
    .map((h) => ({ status: h.to_status, label: STATUS_LABELS[h.to_status], at: h.created_at }));
}

/** Acompanhamento pelo cliente: só com o código secreto do pedido; mostra o mínimo de dados pessoais. */
export function trackOrder(db, body) {
  onlyKeys(body, ['token'], 'consulta');
  const token = body.token;
  if (typeof token !== 'string' || !/^[A-Za-z0-9_-]{32}$/.test(token)) throw notFound('Pedido não encontrado.');
  const o = db.prepare('SELECT * FROM orders WHERE tracking_token = ?').get(token);
  if (!o) throw notFound('Pedido não encontrado.');
  const settings = getSettings(db);
  return {
    code: orderCode(o.id),
    status: o.status,
    statusLabel: STATUS_LABELS[o.status],
    fulfillment: o.fulfillment,
    customerFirstName: o.customer_name ? o.customer_name.split(' ')[0] : null,
    paymentMethod: PAYMENT_LABELS[o.payment_method],
    changeForCents: o.change_for_cents,
    items: loadItems(db, o.id),
    subtotalCents: o.subtotal_cents,
    discountCents: o.discount_cents,
    deliveryFeeCents: o.delivery_fee_cents,
    totalCents: o.total_cents,
    couponCode: o.coupon_code,
    createdAt: o.created_at,
    updatedAt: o.updated_at,
    history: history(db, o.id),
    pickupAddress: o.fulfillment === 'retirada' ? settings.pickup_address : '',
    contactPhone: settings.contact_phone,
  };
}

// ---------- administração ----------

function adminOrder(db, o) {
  return {
    id: o.id,
    code: orderCode(o.id),
    status: o.status,
    statusLabel: STATUS_LABELS[o.status],
    nextStatuses: nextStatuses(o.status, o.fulfillment).map((s) => ({ status: s, label: STATUS_LABELS[s] })),
    fulfillment: o.fulfillment,
    customer: { name: o.customer_name, phone: o.customer_phone },
    address: o.address_json ? JSON.parse(o.address_json) : null,
    notes: o.notes,
    paymentMethod: o.payment_method,
    paymentLabel: PAYMENT_LABELS[o.payment_method],
    changeForCents: o.change_for_cents,
    subtotalCents: o.subtotal_cents,
    discountCents: o.discount_cents,
    deliveryFeeCents: o.delivery_fee_cents,
    totalCents: o.total_cents,
    couponCode: o.coupon_code,
    createdAt: o.created_at,
    updatedAt: o.updated_at,
    personalDataPurged: Boolean(o.personal_data_purged_at),
    items: loadItems(db, o.id),
    history: history(db, o.id),
  };
}

export function listOrders(db, { scope = 'abertos', limit = 100 } = {}) {
  let rows;
  if (scope === 'abertos') {
    rows = db.prepare(`SELECT * FROM orders WHERE status NOT IN ('concluido','cancelado') ORDER BY id ASC LIMIT ?`).all(limit);
  } else if (scope === 'todos') {
    rows = db.prepare('SELECT * FROM orders ORDER BY id DESC LIMIT ?').all(limit);
  } else if (STATUS_LABELS[scope]) {
    rows = db.prepare('SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?').all(scope, limit);
  } else {
    throw badRequest('Filtro inválido.');
  }
  return rows.map((o) => adminOrder(db, o));
}

export function getOrderForAdmin(db, id) {
  const o = db.prepare('SELECT * FROM orders WHERE id = ?').get(id);
  if (!o) throw notFound('Pedido não encontrado.');
  return adminOrder(db, o);
}

export function updateOrderStatus(db, id, body, adminUserId) {
  onlyKeys(body, ['status', 'fromStatus'], 'status');
  const to = oneOf(body.status, Object.keys(STATUS_LABELS), { field: 'o novo status' });
  const from = oneOf(body.fromStatus, Object.keys(STATUS_LABELS), { field: 'o status atual' });
  return transaction(db, () => {
    const o = db.prepare('SELECT * FROM orders WHERE id = ?').get(id);
    if (!o) throw notFound('Pedido não encontrado.');
    if (o.status !== from) {
      throw conflict('Este pedido já foi atualizado por outra pessoa. A lista foi recarregada.');
    }
    if (!nextStatuses(o.status, o.fulfillment).includes(to)) {
      throw conflict(`Não é possível mudar de "${STATUS_LABELS[o.status]}" para "${STATUS_LABELS[to]}".`);
    }
    const now = nowIso();
    const r = db.prepare('UPDATE orders SET status = ?, updated_at = ? WHERE id = ? AND status = ?').run(to, now, id, from);
    if (r.changes !== 1) throw conflict('Este pedido já foi atualizado por outra pessoa.');
    db.prepare('INSERT INTO order_status_history (order_id, from_status, to_status, admin_user_id, created_at) VALUES (?, ?, ?, ?, ?)').run(
      id,
      from,
      to,
      adminUserId,
      now
    );
    // Pedido cancelado devolve o uso do cupom.
    if (to === 'cancelado' && o.coupon_code) {
      db.prepare('UPDATE coupons SET uses = uses - 1 WHERE code = ? AND uses > 0').run(o.coupon_code);
    }
    return adminOrder(db, db.prepare('SELECT * FROM orders WHERE id = ?').get(id));
  });
}

/**
 * Remove nome, telefone, endereço e observações de pedidos finalizados há mais
 * de `days` dias (os valores e itens continuam para relatórios).
 */
export function purgePersonalData(db, days) {
  const cutoff = new Date(Date.now() - days * 86400 * 1000).toISOString();
  return db
    .prepare(
      `UPDATE orders SET customer_name = NULL, customer_phone = NULL, address_json = NULL, notes = '',
              personal_data_purged_at = ?
        WHERE status IN ('concluido','cancelado') AND updated_at < ? AND personal_data_purged_at IS NULL`
    )
    .run(nowIso(), cutoff).changes;
}
