// Fluxo completo: cardápio → orçamento → pedido → acompanhamento → painel → status.
import assert from 'node:assert/strict';
import { after, before, describe, it } from 'node:test';
import { createRateLimiter } from '../server/http/security.js';
import { orderBody, startServer, uuid } from './helpers.js';

describe('fluxo do pedido (API real + banco SQLite)', () => {
  let srv;
  let customer;
  let admin;

  before(async () => {
    // muitos pedidos saem do mesmo IP nestes testes; o limite real é testado em http-security
    srv = await startServer({ overrides: { limiters: { order: createRateLimiter({ windowMs: 60_000, max: 1000 }) } } });
    customer = srv.client();
    admin = srv.client();
    assert.equal((await admin.login()).status, 200);
  });
  after(() => srv.close());

  it('cardápio público traz o X-Bacon original com preço do servidor', async () => {
    const r = await customer.get('/api/menu');
    assert.equal(r.status, 200);
    const p = r.data.categories[0].products[0];
    assert.equal(p.name, 'X-Bacon');
    assert.equal(p.priceCents, 2490);
    assert.equal(p.image, null);
    assert.equal(r.data.store.storeName, 'Desu Burguer');
    assert.equal('payment_methods' in r.data.store, false, 'não expõe configurações internas');
  });

  it('do produto personalizado ao pedido registrado, persistido e acompanhado', async () => {
    // admin cadastra um adicional e vincula ao X-Bacon
    const add = await admin.admin('POST', '/api/admin/addons', { name: 'Bacon extra', priceCents: 400, available: true });
    assert.equal(add.status, 201);
    const upd = await admin.admin('PUT', '/api/admin/products/1', { addonIds: [add.data.id] });
    assert.equal(upd.status, 200);

    const items = [{ productId: 1, quantity: 2, addonIds: [add.data.id], notes: 'sem cebola' }];
    const q = await customer.post('/api/orders/quote', { items, fulfillment: 'retirada' });
    assert.equal(q.status, 200);
    assert.equal(q.data.totalCents, (2490 + 400) * 2);

    const body = orderBody({ items, expectedTotalCents: q.data.totalCents });
    const r = await customer.post('/api/orders', body);
    assert.equal(r.status, 201, JSON.stringify(r.data));
    assert.match(r.data.code, /^#\d{4}$/);
    assert.match(r.data.trackingToken, /^[A-Za-z0-9_-]{32}$/);
    assert.equal(r.data.totalCents, 5780);

    // persistência no banco
    const row = srv.db.prepare('SELECT * FROM orders WHERE tracking_token = ?').get(r.data.trackingToken);
    assert.equal(row.status, 'recebido');
    assert.equal(row.customer_phone, '11912345678', 'telefone normalizado');
    assert.equal(row.total_cents, 5780);
    const itemsRows = srv.db.prepare('SELECT * FROM order_items WHERE order_id = ?').all(row.id);
    assert.equal(itemsRows.length, 1);
    assert.equal(itemsRows[0].notes, 'sem cebola');
    assert.equal(srv.db.prepare('SELECT COUNT(*) n FROM order_item_addons').get().n, 1);

    // acompanhamento pelo cliente
    const t = await customer.post('/api/orders/track', { token: r.data.trackingToken });
    assert.equal(t.status, 200);
    assert.equal(t.data.status, 'recebido');
    assert.equal(t.data.customerFirstName, 'Maria');
    assert.equal(JSON.stringify(t.data).includes('91234'), false, 'não devolve telefone');
    assert.equal(t.headers.get('cache-control'), 'no-store');

    // painel vê o pedido e muda status seguindo as regras
    const list = await admin.get('/api/admin/orders');
    const o = list.data.orders.find((x) => x.id === row.id);
    assert.ok(o);
    assert.deepEqual(o.nextStatuses.map((s) => s.status), ['em_preparo', 'cancelado']);
    const s1 = await admin.admin('PATCH', `/api/admin/orders/${o.id}/status`, { status: 'em_preparo', fromStatus: 'recebido' });
    assert.equal(s1.status, 200);
    const s2 = await admin.admin('PATCH', `/api/admin/orders/${o.id}/status`, { status: 'saiu_para_entrega', fromStatus: 'em_preparo' });
    assert.equal(s2.status, 409, 'retirada não pode "sair para entrega"');
    const s3 = await admin.admin('PATCH', `/api/admin/orders/${o.id}/status`, { status: 'pronto', fromStatus: 'recebido' });
    assert.equal(s3.status, 409, 'status desatualizado é recusado');
    assert.equal((await admin.admin('PATCH', `/api/admin/orders/${o.id}/status`, { status: 'pronto', fromStatus: 'em_preparo' })).status, 200);
    assert.equal((await admin.admin('PATCH', `/api/admin/orders/${o.id}/status`, { status: 'concluido', fromStatus: 'pronto' })).status, 200);
    const fin = await admin.admin('PATCH', `/api/admin/orders/${o.id}/status`, { status: 'cancelado', fromStatus: 'concluido' });
    assert.equal(fin.status, 409, 'pedido concluído não volta atrás');

    const t2 = await customer.post('/api/orders/track', { token: r.data.trackingToken });
    assert.deepEqual(t2.data.history.map((h) => h.status), ['recebido', 'em_preparo', 'pronto', 'concluido']);
  });

  it('rejeita preços, totais e descontos adulterados pelo navegador', async () => {
    const tampered = [
      { ...orderBody(), totalCents: 1 },
      { ...orderBody(), items: [{ productId: 1, quantity: 1, price: 1 }] },
      { ...orderBody(), items: [{ productId: 1, quantity: 1, unitPriceCents: 1 }] },
      { ...orderBody(), discountCents: 4980 },
      { ...orderBody(), deliveryFeeCents: 0 },
    ];
    for (const body of tampered) {
      const r = await customer.post('/api/orders', body);
      assert.equal(r.status, 400, JSON.stringify(body));
      assert.match(r.data.error, /Campo não permitido/);
    }
    // total esperado diferente do calculado: recusa e devolve o valor correto
    const r = await customer.post('/api/orders', orderBody({ expectedTotalCents: 100 }));
    assert.equal(r.status, 409);
    assert.equal(r.data.code, 'total_alterado');
    assert.equal(r.data.quote.totalCents, 4980);
    // quantidades e IDs inválidos
    for (const items of [
      [{ productId: 1, quantity: 0 }],
      [{ productId: 1, quantity: -3 }],
      [{ productId: 1, quantity: 1.5 }],
      [{ productId: 1, quantity: 21 }],
      [{ productId: '1 OR 1=1', quantity: 1 }],
      [],
    ]) {
      assert.equal((await customer.post('/api/orders', orderBody({ items }))).status, 400, JSON.stringify(items));
    }
  });

  it('não cria pedido duplicado ao reenviar a mesma requisição', async () => {
    const body = orderBody();
    const before = srv.db.prepare('SELECT COUNT(*) n FROM orders').get().n;
    const [a, b] = await Promise.all([customer.post('/api/orders', body), customer.post('/api/orders', body)]);
    const c = await customer.post('/api/orders', body);
    const statuses = [a.status, b.status, c.status].sort();
    assert.deepEqual(statuses, [200, 200, 201]);
    assert.equal(a.data.trackingToken, b.data.trackingToken);
    assert.equal(a.data.trackingToken, c.data.trackingToken);
    assert.equal(srv.db.prepare('SELECT COUNT(*) n FROM orders').get().n, before + 1);
    // mesma chave com outros dados: recusa
    const d = await customer.post('/api/orders', { ...body, notes: 'outra coisa' });
    assert.equal(d.status, 409);
  });

  it('bloqueia produto indisponível, loja fechada e entrega desativada', async () => {
    await admin.admin('PUT', '/api/admin/products/1', { available: false });
    let r = await customer.post('/api/orders', orderBody());
    assert.equal(r.status, 409);
    assert.match(r.data.error, /indisponível/);
    await admin.admin('PUT', '/api/admin/products/1', { available: true });

    r = await customer.post('/api/orders', orderBody({ fulfillment: 'entrega', address: { street: 'Rua A', number: '10', district: 'Centro' } }));
    assert.equal(r.status, 409);
    assert.match(r.data.error, /entregas/);

    await admin.admin('PUT', '/api/admin/settings', { accepting_orders: false });
    r = await customer.post('/api/orders', orderBody());
    assert.equal(r.status, 409);
    await admin.admin('PUT', '/api/admin/settings', { accepting_orders: true });
  });

  it('entrega cobra a taxa configurada e exige endereço', async () => {
    await admin.admin('PUT', '/api/admin/settings', { delivery_enabled: true, delivery_fee_cents: 600 });
    const noAddr = await customer.post('/api/orders', orderBody({ fulfillment: 'entrega', expectedTotalCents: 5580 }));
    assert.equal(noAddr.status, 400);
    const r = await customer.post(
      '/api/orders',
      orderBody({
        fulfillment: 'entrega',
        expectedTotalCents: 5580,
        address: { street: 'Rua das Flores', number: '123', district: 'Centro', complement: 'ap 2', reference: '' },
        paymentMethod: 'dinheiro',
        changeForCents: 10000,
      })
    );
    assert.equal(r.status, 201, JSON.stringify(r.data));
    const row = srv.db.prepare('SELECT * FROM orders WHERE tracking_token = ?').get(r.data.trackingToken);
    assert.equal(row.delivery_fee_cents, 600);
    assert.equal(row.total_cents, 5580);
    assert.equal(JSON.parse(row.address_json).street, 'Rua das Flores');
    // troco menor que o total é recusado
    const bad = await customer.post(
      '/api/orders',
      orderBody({ idempotencyKey: uuid(), fulfillment: 'entrega', expectedTotalCents: 5580, address: { street: 'Rua X', number: '1', district: 'Centro' }, paymentMethod: 'dinheiro', changeForCents: 100 })
    );
    assert.equal(bad.status, 400);
  });

  it('cupom: desconto calculado no servidor e limite de usos respeitado', async () => {
    const c = await admin.admin('POST', '/api/admin/coupons', { code: 'DESU10', kind: 'percent', value: 10, maxUses: 1, active: true });
    assert.equal(c.status, 201, JSON.stringify(c.data));
    const q = await customer.post('/api/orders/quote', { items: [{ productId: 1, quantity: 2 }], couponCode: 'desu10', fulfillment: 'retirada' });
    assert.equal(q.data.discountCents, 498);
    assert.equal(q.data.totalCents, 4482);
    const r1 = await customer.post('/api/orders', orderBody({ couponCode: 'DESU10', expectedTotalCents: 4482 }));
    assert.equal(r1.status, 201);
    const r2 = await customer.post('/api/orders', orderBody({ couponCode: 'DESU10', expectedTotalCents: 4482 }));
    assert.equal(r2.status, 409);
    assert.match(r2.data.error, /limite/);
    assert.equal(srv.db.prepare("SELECT uses FROM coupons WHERE code = 'DESU10'").get().uses, 1);
    // cancelar o pedido devolve o uso do cupom
    const id = srv.db.prepare('SELECT id FROM orders WHERE tracking_token = ?').get(r1.data.trackingToken).id;
    await admin.admin('PATCH', `/api/admin/orders/${id}/status`, { status: 'cancelado', fromStatus: 'recebido' });
    assert.equal(srv.db.prepare("SELECT uses FROM coupons WHERE code = 'DESU10'").get().uses, 0);
    const unknown = await customer.post('/api/orders', orderBody({ couponCode: 'NAOEXISTE', expectedTotalCents: 4980 }));
    assert.equal(unknown.status, 409);
  });

  it('cliente só vê o próprio pedido (token secreto, sem IDs sequenciais)', async () => {
    for (const token of ['1', 'x'.repeat(32), "' OR 1=1 --", '../../etc/passwd']) {
      const r = await customer.post('/api/orders/track', { token });
      assert.equal(r.status, 404, token);
    }
    assert.equal((await customer.get('/api/admin/orders/1')).status, 401);
  });

  it('valida dados do cliente com mensagens claras', async () => {
    const r1 = await customer.post('/api/orders', orderBody({ customer: { name: 'M', phone: '11912345678' } }));
    assert.equal(r1.status, 400);
    assert.match(r1.data.error, /nome/);
    const r2 = await customer.post('/api/orders', orderBody({ customer: { name: 'Maria', phone: '123' } }));
    assert.equal(r2.status, 400);
    assert.match(r2.data.error, /Telefone/);
    const r3 = await customer.post('/api/orders', orderBody({ paymentMethod: 'bitcoin' }));
    assert.equal(r3.status, 400);
    const r4 = await customer.post('/api/orders', orderBody({ idempotencyKey: 'abc' }));
    assert.equal(r4.status, 400);
  });

  it('remove dados pessoais de pedidos antigos finalizados (retenção)', async () => {
    const { purgePersonalData } = await import('../server/services/orders.js');
    srv.db.prepare("UPDATE orders SET updated_at = '2000-01-01T00:00:00.000Z' WHERE status IN ('concluido','cancelado')").run();
    const n = purgePersonalData(srv.db, 30);
    assert.ok(n >= 1);
    const left = srv.db
      .prepare("SELECT COUNT(*) n FROM orders WHERE status IN ('concluido','cancelado') AND customer_phone IS NOT NULL")
      .get().n;
    assert.equal(left, 0);
    const open = srv.db.prepare("SELECT COUNT(*) n FROM orders WHERE status = 'recebido' AND customer_phone IS NOT NULL").get().n;
    assert.ok(open > 0, 'pedidos em aberto mantêm os dados');
  });
});
