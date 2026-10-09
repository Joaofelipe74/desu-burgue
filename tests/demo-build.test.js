// Versão de demonstração (GitHub Pages): o build gera só arquivos estáticos, sem painel,
// com caminhos corretos e com o MESMO cálculo de preços do servidor.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { after, before, describe, it } from 'node:test';
import { ROOT_DIR } from '../server/config.js';
import { startServer } from './helpers.js';

const BASE = '/desu-burgue/';

describe('versão de demonstração', () => {
  let tmp;
  let out;
  let srv;
  before(async () => {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'desu-demo-test-'));
    out = path.join(tmp, 'site');
    execFileSync(process.execPath, [
      '--disable-warning=ExperimentalWarning',
      path.join(ROOT_DIR, 'scripts', 'build-demo.js'),
      '--out', out, '--base', BASE, '--repo', 'https://github.com/exemplo/desu-burgue',
    ], { stdio: 'pipe' });
    srv = await startServer({ sampleMenu: true });
  });
  after(() => {
    srv?.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  it('gera só as telas do cliente, com aviso, CSP e caminhos na base', () => {
    for (const f of ['index.html', 'checkout.html', 'pedido.html', '404.html', 'demo/api.js', 'demo/pricing.js', 'demo/option-rules.js', 'demo/dados.json']) {
      assert.ok(fs.existsSync(path.join(out, f)), f);
    }
    assert.equal(fs.existsSync(path.join(out, 'admin')), false, 'sem painel');
    assert.equal(fs.existsSync(path.join(out, 'js', 'admin')), false, 'sem scripts do painel');
    for (const f of ['index.html', 'checkout.html', 'pedido.html', '404.html']) {
      const html = fs.readFileSync(path.join(out, f), 'utf8');
      assert.match(html, /<html lang="pt-BR" data-demo="1">/, f);
      assert.match(html, /Content-Security-Policy" content="default-src 'self'; script-src 'self'/, f);
      assert.match(html, /Versão de demonstração/, f);
      assert.doesNotMatch(html, /(href|src)="\/(?!desu-burgue\/)/, `${f}: caminho fora da base`);
    }
    const menu = JSON.parse(fs.readFileSync(path.join(out, 'demo', 'dados.json'), 'utf8')).menu;
    const produtos = menu.categories.flatMap((c) => c.products);
    assert.equal(produtos.length, 63);
    for (const p of produtos) assert.ok(p.image.src.startsWith(`${BASE}img/ilustracoes/`), p.name);
  });

  it('a pasta demo/ publicada no GitHub Pages está atualizada com o código', (t) => {
    const publicada = path.join(ROOT_DIR, 'demo');
    if (!fs.existsSync(publicada)) return t.skip('pasta demo/ ainda não gerada');
    const nova = path.join(tmp, 'demo-pages');
    const cmd = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'package.json'), 'utf8')).scripts['build:demo:pages'];
    const extra = cmd.split(' ').slice(cmd.split(' ').indexOf('--base'));
    execFileSync(process.execPath, ['--disable-warning=ExperimentalWarning', path.join(ROOT_DIR, 'scripts', 'build-demo.js'), '--out', nova, ...extra], { stdio: 'pipe' });
    const lista = (dir) => fs.readdirSync(dir, { recursive: true }).filter((f) => fs.statSync(path.join(dir, f)).isFile()).sort();
    const msg = 'A pasta demo/ está desatualizada. Rode: npm run build:demo:pages';
    assert.deepEqual(lista(publicada), lista(nova), msg);
    for (const f of lista(nova)) assert.ok(fs.readFileSync(path.join(publicada, f)).equals(fs.readFileSync(path.join(nova, f))), `${msg} (${f})`);
  });

  it('não apaga uma pasta que não foi criada pelo build', () => {
    const outra = path.join(tmp, 'pasta-do-usuario');
    fs.mkdirSync(outra);
    fs.writeFileSync(path.join(outra, 'importante.txt'), 'não apagar');
    assert.throws(() =>
      execFileSync(process.execPath, ['--disable-warning=ExperimentalWarning', path.join(ROOT_DIR, 'scripts', 'build-demo.js'), '--out', outra], { stdio: 'pipe' })
    );
    assert.equal(fs.readFileSync(path.join(outra, 'importante.txt'), 'utf8'), 'não apagar');
  });

  it('a API da demonstração calcula igual ao servidor e guarda o pedido só no navegador', async () => {
    // Simula o navegador: fetch de arquivo local e localStorage em memória.
    const store = new Map();
    globalThis.localStorage = {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, String(v)),
    };
    const realFetch = globalThis.fetch;
    globalThis.fetch = async (url, opts) => {
      const file = new URL(url);
      if (file.protocol !== 'file:') return realFetch(url, opts);
      return new Response(fs.readFileSync(file), { status: 200 });
    };
    try {
      class ApiError extends Error {
        constructor(status, data) {
          super(data.error);
          this.status = status;
          this.data = data;
        }
      }
      const { demoApi } = await import(pathToFileURL(path.join(out, 'demo', 'api.js')).href);
      const menu = await demoApi('/api/menu', {}, ApiError);
      const byName = new Map(menu.categories.flatMap((c) => c.products).map((p) => [p.name, p]));
      const xbacon = byName.get('X-Bacon');
      const ponto = xbacon.optionGroups.find((g) => g.name === 'Ponto da carne').choices.find((c) => c.name === 'Ao ponto');
      const pao = xbacon.optionGroups.find((g) => g.name === 'Tipo de pão').choices.find((c) => c.name === 'Australiano');
      const bacon = xbacon.addons.find((a) => a.name === 'Bacon extra');
      const acai = byName.get('Açaí 500 ml');
      const items = [
        { productId: xbacon.id, quantity: 2, addonIds: [bacon.id], optionIds: [ponto.id, pao.id], notes: 'sem cebola' },
        { productId: acai.id, quantity: 1, addonIds: [], optionIds: [], notes: '' },
      ];
      for (const fulfillment of ['entrega', 'retirada']) {
        const body = { items, fulfillment, couponCode: '' };
        const demo = await demoApi('/api/orders/quote', { body }, ApiError);
        const real = await srv.client().post('/api/orders/quote', body);
        assert.equal(real.status, 200);
        assert.deepEqual(demo, real.data, `orçamento igual ao do servidor (${fulfillment})`);
      }
      // opção obrigatória faltando: mesmo aviso do servidor
      const sem = { items: [{ productId: xbacon.id, quantity: 1, addonIds: [], optionIds: [], notes: '' }], fulfillment: 'retirada', couponCode: '' };
      assert.deepEqual((await demoApi('/api/orders/quote', { body: sem }, ApiError)).issues, (await srv.client().post('/api/orders/quote', sem)).data.issues);

      const quote = await demoApi('/api/orders/quote', { body: { items, fulfillment: 'retirada' } }, ApiError);
      const pedido = {
        idempotencyKey: crypto.randomUUID(),
        items,
        fulfillment: 'retirada',
        couponCode: '',
        customer: { name: 'Maria Teste', phone: '(11) 98765-4321' },
        paymentMethod: 'pix',
        notes: '',
        expectedTotalCents: quote.totalCents,
      };
      const criado = await demoApi('/api/orders', { body: pedido }, ApiError);
      assert.equal(criado.code, '#0001');
      assert.match(criado.trackingToken, /^[A-Za-z0-9_-]{32}$/);
      const repetido = await demoApi('/api/orders', { body: pedido }, ApiError);
      assert.equal(repetido.trackingToken, criado.trackingToken, 'sem pedido duplicado');
      const salvo = store.get('desu.demo.pedidos.v1');
      assert.doesNotMatch(salvo, /98765|Teste/, 'telefone e sobrenome não ficam guardados');

      const acomp = await demoApi('/api/orders/track', { body: { token: criado.trackingToken } }, ApiError);
      assert.equal(acomp.status, 'recebido');
      assert.equal(acomp.customerFirstName, 'Maria');
      assert.equal(acomp.totalCents, quote.totalCents);

      await assert.rejects(
        demoApi('/api/orders', { body: { ...pedido, idempotencyKey: crypto.randomUUID(), expectedTotalCents: 1 } }, ApiError),
        (e) => e.status === 409 && e.data.code === 'total_alterado'
      );
      await assert.rejects(
        demoApi('/api/orders', { body: { ...pedido, idempotencyKey: crypto.randomUUID(), customer: { name: 'Maria', phone: '123' } } }, ApiError),
        (e) => e.status === 400 && /Telefone inválido/.test(e.message)
      );
      await assert.rejects(demoApi('/api/admin/orders', {}, ApiError), (e) => e.status === 404);
    } finally {
      globalThis.fetch = realFetch;
      delete globalThis.localStorage;
    }
  });
});
