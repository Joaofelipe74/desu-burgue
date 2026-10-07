// Opções de personalização, preço promocional, selos, "mais pedidos" e cardápio ampliado.
import assert from 'node:assert/strict';
import { after, before, describe, it } from 'node:test';
import { createRateLimiter } from '../server/http/security.js';
import { applySampleMenuV2 } from '../server/sample-menu-v2.js';
import { orderBody, startServer } from './helpers.js';

describe('opções de personalização (validadas no servidor)', () => {
  let srv;
  let admin;
  let ids;
  before(async () => {
    srv = await startServer({ overrides: { limiters: { order: createRateLimiter({ windowMs: 60_000, max: 1000 }) } } });
    admin = srv.client();
    await admin.login();
    const ponto = await admin.admin('POST', '/api/admin/option-groups', {
      name: 'Ponto da carne', kind: 'single', required: true,
      choices: [{ name: 'Ao ponto', priceCents: 0 }, { name: 'Bem passado', priceCents: 0 }],
    });
    const pao = await admin.admin('POST', '/api/admin/option-groups', {
      name: 'Tipo de pão', kind: 'single', required: true,
      choices: [{ name: 'Tradicional', priceCents: 0 }, { name: 'Brioche', priceCents: 200 }],
    });
    const tirar = await admin.admin('POST', '/api/admin/option-groups', {
      name: 'Retirar ingredientes', kind: 'multi', required: false, maxChoices: 2,
      choices: [{ name: 'Sem cebola' }, { name: 'Sem tomate' }, { name: 'Sem picles' }],
    });
    const outro = await admin.admin('POST', '/api/admin/option-groups', {
      name: 'Sabor', kind: 'single', required: true, choices: [{ name: 'Cola' }],
    });
    for (const r of [ponto, pao, tirar, outro]) assert.equal(r.status, 201, JSON.stringify(r.data));
    await admin.admin('PUT', '/api/admin/products/1', { optionGroupIds: [ponto.data.id, pao.data.id, tirar.data.id] });
    const groups = (await admin.get('/api/admin/option-groups')).data.groups;
    const choice = (g, n) => groups.find((x) => x.name === g).choices.find((c) => c.name === n).id;
    ids = {
      aoPonto: choice('Ponto da carne', 'Ao ponto'),
      bemPassado: choice('Ponto da carne', 'Bem passado'),
      brioche: choice('Tipo de pão', 'Brioche'),
      tradicional: choice('Tipo de pão', 'Tradicional'),
      semCebola: choice('Retirar ingredientes', 'Sem cebola'),
      semTomate: choice('Retirar ingredientes', 'Sem tomate'),
      semPicles: choice('Retirar ingredientes', 'Sem picles'),
      cola: choice('Sabor', 'Cola'),
      groupTirar: tirar.data.id,
    };
  });
  after(() => srv.close());

  const quote = (optionIds) =>
    srv.client().post('/api/orders/quote', { items: [{ productId: 1, quantity: 2, optionIds }], fulfillment: 'retirada' });

  it('cardápio público mostra os grupos e escolhas do produto', async () => {
    const p = (await srv.client().get('/api/menu')).data.categories[0].products[0];
    assert.deepEqual(p.optionGroups.map((g) => g.name), ['Ponto da carne', 'Tipo de pão', 'Retirar ingredientes']);
    assert.equal(p.optionGroups[0].required, true);
    assert.equal(p.optionGroups[2].maxChoices, 2);
  });

  it('soma o preço da escolha (pão brioche +R$ 2,00) no servidor', async () => {
    const r = await quote([ids.aoPonto, ids.brioche, ids.semCebola]);
    assert.deepEqual(r.data.issues, []);
    assert.equal(r.data.lines[0].unitPriceCents, 2490 + 200);
    assert.equal(r.data.totalCents, (2490 + 200) * 2);
    assert.deepEqual(r.data.lines[0].options.map((o) => o.name), ['Ao ponto', 'Brioche', 'Sem cebola']);
  });

  it('exige grupos obrigatórios e respeita escolha única e máximo', async () => {
    const faltando = await quote([ids.brioche]);
    assert.ok(faltando.data.issues.some((i) => i.code === 'opcao_obrigatoria' && /Ponto da carne/.test(i.message)));
    const duasNoUnico = await quote([ids.aoPonto, ids.bemPassado, ids.tradicional]);
    assert.ok(duasNoUnico.data.issues.some((i) => i.code === 'opcao_excesso'));
    const acimaDoMax = await quote([ids.aoPonto, ids.tradicional, ids.semCebola, ids.semTomate, ids.semPicles]);
    assert.ok(acimaDoMax.data.issues.some((i) => i.code === 'opcao_excesso'));
    const deOutroGrupo = await quote([ids.aoPonto, ids.tradicional, ids.cola]);
    assert.ok(deOutroGrupo.data.issues.some((i) => i.code === 'opcao_invalida'), 'escolha de grupo não vinculado');
    // pedido com opção inválida é recusado
    const r = await srv.client().post('/api/orders', orderBody({ items: [{ productId: 1, quantity: 2, optionIds: [ids.brioche] }], expectedTotalCents: 5380 }));
    assert.equal(r.status, 409);
  });

  it('grava as opções escolhidas no pedido e mostra no acompanhamento e no painel', async () => {
    const items = [{ productId: 1, quantity: 1, optionIds: [ids.bemPassado, ids.brioche, ids.semTomate], notes: '' }];
    const r = await srv.client().post('/api/orders', orderBody({ items, expectedTotalCents: 2690 }));
    assert.equal(r.status, 201, JSON.stringify(r.data));
    const t = await srv.client().post('/api/orders/track', { token: r.data.trackingToken });
    assert.deepEqual(t.data.items[0].options.map((o) => o.name), ['Bem passado', 'Brioche', 'Sem tomate']);
    const list = await admin.get('/api/admin/orders');
    const o = list.data.orders.find((x) => x.code === r.data.code);
    assert.equal(o.items[0].options[1].groupName, 'Tipo de pão');
  });

  it('escolha indisponível bloqueia; arquivar o grupo remove a exigência', async () => {
    await admin.admin('PUT', `/api/admin/option-choices/${ids.brioche}`, { available: false });
    const r = await quote([ids.aoPonto, ids.brioche]);
    assert.ok(r.data.issues.some((i) => i.code === 'opcao_indisponivel'));
    await admin.admin('PUT', `/api/admin/option-choices/${ids.brioche}`, { available: true });
    await admin.admin('PUT', `/api/admin/option-groups/${ids.groupTirar}`, { archived: true });
    const menu = (await srv.client().get('/api/menu')).data.categories[0].products[0];
    assert.equal(menu.optionGroups.some((g) => g.name === 'Retirar ingredientes'), false);
    await admin.admin('PUT', `/api/admin/option-groups/${ids.groupTirar}`, { archived: false });
  });

  it('valida o cadastro de grupos e escolhas no painel', async () => {
    assert.equal((await admin.admin('POST', '/api/admin/option-groups', { name: 'X', kind: 'qualquer' })).status, 400);
    assert.equal((await admin.admin('POST', '/api/admin/option-groups', { name: 'Ponto da carne', kind: 'single' })).status, 409);
    assert.equal((await admin.admin('POST', `/api/admin/option-groups/${ids.groupTirar}/choices`, { name: 'Sem queijo', priceCents: -5 })).status, 400);
    assert.equal((await admin.admin('POST', `/api/admin/option-groups/${ids.groupTirar}/choices`, { name: 'Sem queijo' })).status, 201);
    assert.equal((await admin.admin('PUT', '/api/admin/products/1', { optionGroupIds: [99999] })).status, 400);
    assert.equal((await srv.client().post('/api/admin/option-groups', { name: 'Hack', kind: 'single' })).status, 401);
  });
});

describe('preço promocional, selos e mais pedidos', () => {
  let srv;
  let admin;
  before(async () => {
    srv = await startServer({ overrides: { limiters: { order: createRateLimiter({ windowMs: 60_000, max: 1000 }) } } });
    admin = srv.client();
    await admin.login();
  });
  after(() => srv.close());

  it('cobra o preço promocional e mostra o preço antigo', async () => {
    assert.equal((await admin.admin('PUT', '/api/admin/products/1', { promoPriceCents: 2490 })).status, 400, 'promoção igual ao preço');
    assert.equal((await admin.admin('PUT', '/api/admin/products/1', { promoPriceCents: 1990 })).status, 200);
    const p = (await srv.client().get('/api/menu')).data.categories[0].products[0];
    assert.equal(p.priceCents, 1990);
    assert.equal(p.originalPriceCents, 2490);
    const r = await srv.client().post('/api/orders', orderBody({ expectedTotalCents: 3980 }));
    assert.equal(r.status, 201, JSON.stringify(r.data));
    assert.equal(r.data.totalCents, 3980);
    assert.equal((await admin.admin('PUT', '/api/admin/products/1', { promoPriceCents: null })).status, 200);
    assert.equal((await srv.client().get('/api/menu')).data.categories[0].products[0].originalPriceCents, null);
  });

  it('aceita só selos da lista', async () => {
    assert.equal((await admin.admin('PUT', '/api/admin/products/1', { tags: ['<script>'] })).status, 400);
    assert.equal((await admin.admin('PUT', '/api/admin/products/1', { tags: ['novo', 'picante', 'novo'] })).status, 200);
    const p = (await srv.client().get('/api/menu')).data.categories[0].products[0];
    assert.deepEqual(p.tags, ['novo', 'picante']);
  });

  it('lista "mais pedidos" a partir dos pedidos reais (sem expor quantidades)', async () => {
    const menu = (await srv.client().get('/api/menu')).data;
    assert.deepEqual(menu.popularProductIds, [1]);
    assert.equal(JSON.stringify(menu).includes('"q"'), false);
  });
});

describe('cardápio ampliado (exemplo v2)', () => {
  it('adiciona categorias, produtos e opções sem apagar nada e sem duplicar', async () => {
    const srv = await startServer({ sampleMenu: true });
    try {
      const menu = (await srv.client().get('/api/menu')).data;
      const names = menu.categories.map((c) => c.name);
      assert.deepEqual(names, [
        'Hambúrgueres', 'Smash Burgers', 'Artesanais Premium', 'Combos', 'Hot Dogs', 'Sanduíches',
        'Porções', 'Kids', 'Bebidas', 'Açaí', 'Sobremesas', 'Molhos',
      ]);
      const all = menu.categories.flatMap((c) => c.products);
      assert.equal(all.length, 63);
      assert.equal(new Set(all.map((p) => p.name)).size, 63, 'sem nomes repetidos');
      const xbacon = all.find((p) => p.name === 'X-Bacon');
      assert.equal(xbacon.priceCents, 2490, 'preço original intacto');
      assert.ok(xbacon.optionGroups.some((g) => g.name === 'Ponto da carne'));
      assert.ok(all.some((p) => p.originalPriceCents), 'há itens em promoção');
      assert.ok(all.some((p) => p.tags.includes('vegetariano')));
      assert.equal(applySampleMenuV2(srv.db), false, 'não aplica duas vezes');
      // pedido com opções obrigatórias de um item do exemplo
      const refri = all.find((p) => p.name === 'Refrigerante lata');
      const guarana = refri.optionGroups[0].choices.find((c) => c.name === 'Guaraná');
      const r = await srv.client().post('/api/orders', orderBody({
        items: [{ productId: refri.id, quantity: 1, optionIds: [guarana.id] }],
        expectedTotalCents: refri.priceCents,
      }));
      assert.equal(r.status, 201, JSON.stringify(r.data));
    } finally {
      await srv.close();
    }
  });
});
