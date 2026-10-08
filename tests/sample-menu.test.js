// Cardápio de exemplo: aplicado uma vez, sem duplicar, preservando o X-Bacon original.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { after, before, describe, it } from 'node:test';
import { ROOT_DIR } from '../server/config.js';
import { applySampleMenu } from '../server/sample-menu.js';
import { SAMPLE_FLAG_V3, applySampleMenuV3 } from '../server/sample-menu-v2.js';
import { ILLUSTRATIONS } from '../server/services/illustrations.js';
import { orderBody, startServer } from './helpers.js';

describe('cardápio de exemplo', () => {
  let srv;
  before(async () => {
    srv = await startServer({ sampleMenu: true });
  });
  after(() => srv.close());

  it('cria categorias, produtos e adicionais com ilustração e selo ilustrativo', async () => {
    const r = await srv.client().get('/api/menu');
    const cats = r.data.categories.map((c) => c.name);
    // v1 (5 categorias) + ampliação v2 (7 categorias novas)
    for (const c of ['Hambúrgueres', 'Combos', 'Porções', 'Bebidas', 'Sobremesas']) assert.ok(cats.includes(c), c);
    assert.equal(cats.length, 12);
    const all = r.data.categories.flatMap((c) => c.products);
    assert.equal(all.length, 63);
    for (const p of all) {
      assert.ok(p.image, `${p.name} tem ilustração`);
      assert.equal(p.image.kind, 'illustration');
      assert.equal(p.image.illustrative, true, 'desenho nunca aparece como foto real');
      const file = path.join(ROOT_DIR, 'public', p.image.src);
      assert.ok(fs.existsSync(file), `arquivo ${p.image.src} existe`);
    }
    const xbacon = all.find((p) => p.name === 'X-Bacon');
    assert.equal(xbacon.priceCents, 2490, 'preço original preservado');
    assert.equal(xbacon.featured, true);
    assert.ok(xbacon.addons.some((a) => a.name === 'Bacon extra'));
    assert.equal(all.filter((p) => p.featured).length, 4);
    assert.equal(r.data.store.deliveryEnabled, true);
    assert.equal(r.data.store.deliveryFeeCents, 600);
    assert.ok(r.data.store.openingHours.length > 0);
  });

  it('não duplica ao abrir o banco de novo', () => {
    const before = srv.db.prepare('SELECT COUNT(*) n FROM products').get().n;
    assert.equal(applySampleMenu(srv.db), false);
    assert.equal(srv.db.prepare('SELECT COUNT(*) n FROM products').get().n, before);
  });

  it('Combo Casal usa o desenho de 2 lanches; banco antigo é ajustado só se o dono não mudou', () => {
    const get = () => srv.db.prepare("SELECT illustration FROM products WHERE name = 'Combo Casal'").get().illustration;
    assert.equal(get(), 'combo-casal');
    // simula um banco criado antes do ajuste
    const reset = (ill) => {
      srv.db.prepare("UPDATE products SET illustration = ? WHERE name = 'Combo Casal'").run(ill);
      srv.db.prepare('DELETE FROM settings WHERE key = ?').run(SAMPLE_FLAG_V3);
    };
    reset('combo-familia');
    assert.equal(applySampleMenuV3(srv.db), true);
    assert.equal(get(), 'combo-casal');
    assert.equal(applySampleMenuV3(srv.db), false, 'aplicado uma vez só');
    reset('combo');
    applySampleMenuV3(srv.db);
    assert.equal(get(), 'combo', 'escolha do dono é mantida');
    srv.db.prepare("UPDATE products SET illustration = 'combo-casal' WHERE name = 'Combo Casal'").run();
  });

  it('todas as ilustrações cadastradas têm arquivo', () => {
    for (const key of Object.keys(ILLUSTRATIONS)) {
      assert.ok(fs.existsSync(path.join(ROOT_DIR, 'public', 'img', 'ilustracoes', `${key}.svg`)), key);
    }
  });

  it('pedido com produtos do exemplo é calculado no servidor', async () => {
    const menu = (await srv.client().get('/api/menu')).data;
    const byName = new Map(menu.categories.flatMap((c) => c.products).map((p) => [p.name, p]));
    const smash = byName.get('Desu Smash Duplo');
    const bacon = smash.addons.find((a) => a.name === 'Bacon extra');
    const refri = byName.get('Refrigerante lata');
    const guarana = refri.optionGroups.find((g) => g.name === 'Sabor do refrigerante').choices.find((c) => c.name === 'Guaraná');
    const items = [
      { productId: smash.id, quantity: 1, addonIds: [bacon.id], notes: '' },
      { productId: refri.id, quantity: 2, addonIds: [], optionIds: [guarana.id], notes: '' },
    ];
    const expected = 2990 + 400 + 650 * 2 + 600;
    const r = await srv.client().post('/api/orders', orderBody({
      items,
      fulfillment: 'entrega',
      address: { street: 'Rua A', number: '1', district: 'Centro' },
      expectedTotalCents: expected,
    }));
    assert.equal(r.status, 201, JSON.stringify(r.data));
    assert.equal(r.data.totalCents, expected);
  });

  it('painel escolhe ilustração só da lista e marca destaque', async () => {
    const c = srv.client();
    await c.login();
    const list = await c.get('/api/admin/products');
    assert.ok(list.data.illustrations.length >= 20);
    const id = list.data.products.find((p) => p.name === 'X-Burguer').id;
    assert.equal((await c.admin('PUT', `/api/admin/products/${id}`, { illustration: '../../server/app' })).status, 400);
    assert.equal((await c.admin('PUT', `/api/admin/products/${id}`, { illustration: 'veggie', featured: true })).status, 200);
    const menu = (await srv.client().get('/api/menu')).data;
    const p = menu.categories.flatMap((x) => x.products).find((x) => x.id === id);
    assert.equal(p.image.src, '/img/ilustracoes/veggie.svg');
    assert.equal(p.featured, true);
    // WhatsApp: só número válido; vira link wa.me
    assert.equal((await c.admin('PUT', '/api/admin/settings', { whatsapp: 'abc' })).status, 400);
    assert.equal((await c.admin('PUT', '/api/admin/settings', { whatsapp: '(11) 98765-4321' })).status, 200);
    const store = (await srv.client().get('/api/menu')).data.store;
    assert.equal(store.whatsappUrl, 'https://wa.me/5511987654321');
  });
});
