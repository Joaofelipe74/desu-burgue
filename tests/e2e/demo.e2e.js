// Teste de ponta a ponta da VERSÃO DE DEMONSTRAÇÃO (a que vai para o GitHub Pages).
/* global document, window, localStorage -- usados dentro de page.evaluate (rodam no navegador) */
// Gera a demonstração numa pasta temporária, serve como arquivos estáticos em /desu-burgue/
// (igual ao GitHub Pages, sem servidor de API) e faz um pedido completo no celular e no computador.
// Uso: npm run test:e2e:demo   (requer Playwright, como o test:e2e)
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { ROOT_DIR } from '../../server/config.js';

let chromium;
try {
  ({ chromium } = createRequire(import.meta.url)('playwright'));
} catch {
  console.error('Playwright não encontrado. Instale com: npm install --no-save playwright && npx playwright install chromium');
  process.exit(1);
}

const BASE = '/desu-burgue/';
const OUT = path.resolve('test-results/e2e-demo');
fs.mkdirSync(OUT, { recursive: true });
const site = fs.mkdtempSync(path.join(os.tmpdir(), 'desu-demo-'));
const dist = path.join(site, 'site');
execFileSync(
  process.execPath,
  ['--disable-warning=ExperimentalWarning', path.join(ROOT_DIR, 'scripts', 'build-demo.js'), '--out', dist, '--base', BASE, '--repo', 'https://github.com/exemplo/desu-burgue'],
  { stdio: 'inherit' }
);

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.txt': 'text/plain' };
const apiCalls = [];
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/api/')) apiCalls.push(url.pathname);
  let rel = url.pathname.startsWith(BASE) ? decodeURIComponent(url.pathname.slice(BASE.length)) : null;
  if (rel !== null && (rel === '' || rel.endsWith('/'))) rel += 'index.html';
  const file = rel !== null ? path.join(dist, rel) : null;
  if (file && file.startsWith(dist) && fs.existsSync(file) && fs.statSync(file).isFile()) {
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  } else {
    res.writeHead(404, { 'Content-Type': TYPES['.html'] });
    fs.createReadStream(path.join(dist, '404.html')).pipe(res);
  }
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const origin = `http://127.0.0.1:${server.address().port}`;

let failures = 0;
async function step(name, fn) {
  try {
    await fn();
    console.log(`ok   ${name}`);
  } catch (err) {
    failures++;
    console.log(`FALHOU ${name}\n     ${err.message.split('\n').join('\n     ')}`);
  }
}

const browser = await chromium.launch();
const errors = [];
const devices = [
  { label: 'computador', viewport: { width: 1280, height: 860 }, fulfillment: 'retirada', total: /26,90/ },
  { label: 'celular', viewport: { width: 390, height: 844 }, fulfillment: 'entrega', total: /32,90/ },
];

for (const d of devices) {
  const ctx = await browser.newContext({ viewport: d.viewport });
  const page = await ctx.newPage();
  page.on('console', (m) => m.type() === 'error' && errors.push(`${d.label}: ${m.text()}`));
  page.on('pageerror', (e) => errors.push(`${d.label}: ${e.message}`));
  const L = d.label;

  await step(`${L}: abre a demonstração com aviso, cardápio completo e imagens`, async () => {
    await page.goto(origin + BASE);
    await page.getByRole('heading', { name: 'X-Bacon' }).first().waitFor();
    assert.match(await page.locator('.demo-banner').textContent(), /Versão de demonstração/);
    assert.equal(await page.locator('.product-card').count() >= 63, true);
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 700) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 30));
      }
    });
    await page.waitForLoadState('networkidle');
    const info = await page.evaluate(() => ({
      broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src),
      overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    }));
    assert.deepEqual(info.broken, []);
    assert.equal(info.overflow, false, 'rolagem horizontal');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${OUT}/${L}-1-inicio.png` });
  });

  await step(`${L}: personaliza o X-Bacon (opções obrigatórias e preço do pão)`, async () => {
    await page.getByRole('button', { name: 'Adicionar X-Bacon ao carrinho' }).first().click();
    const dlg = page.locator('#product-dialog');
    await dlg.waitFor({ state: 'visible' });
    await page.locator('#pd-submit').click();
    assert.match(await page.locator('#pd-error').textContent(), /Ponto da carne/);
    await dlg.getByLabel('Ao ponto').check();
    await dlg.getByLabel(/Brioche/).check();
    assert.match(await page.locator('#pd-submit').textContent(), /R\$\s?26,90/);
    await page.screenshot({ path: `${OUT}/${L}-2-personalizar.png` });
    await page.locator('#pd-submit').click();
    await dlg.waitFor({ state: 'hidden' });
    assert.equal(await page.locator('#cart-count').textContent(), '1');
  });

  await step(`${L}: finaliza com o cálculo do servidor rodando no navegador`, async () => {
    await page.locator('#open-cart').click();
    await page.locator('#cart-dialog').getByRole('link', { name: 'Finalizar pedido' }).click();
    await page.waitForURL(`**${BASE}checkout.html`);
    await page.locator('#checkout-form').waitFor({ state: 'visible' });
    await page.getByLabel('Nome').fill(`Teste ${L}`);
    await page.getByLabel(/Telefone/).fill('(11) 98765-4321');
    if (d.fulfillment === 'entrega') {
      await page.locator('input[name=fulfillment][value=entrega]').check();
      await page.getByLabel('Rua').fill('Rua das Palmeiras');
      await page.getByLabel('Número').fill('45');
      await page.getByLabel('Bairro').fill('Jardim');
    }
    await page.waitForFunction((rx) => new RegExp(rx).test(document.querySelector('#sum-total').textContent), d.total.source);
    await page.locator('input[name=payment][value=pix]').check();
    await page.screenshot({ path: `${OUT}/${L}-3-checkout.png`, fullPage: true });
    await page.locator('#submit-order').click();
    await page.waitForURL(`**${BASE}pedido.html#*`);
    await page.locator('#status-pill').waitFor();
    assert.equal(await page.locator('#status-pill').textContent(), 'Recebido');
    assert.match(await page.locator('#sum-total').textContent(), d.total);
    assert.match(await page.locator('#items').textContent(), /Brioche/);
    await page.screenshot({ path: `${OUT}/${L}-4-pedido.png`, fullPage: true });
  });

  await step(`${L}: o andamento avança sozinho e o carrinho foi esvaziado`, async () => {
    // Simula que o pedido foi feito há 70 segundos.
    await page.evaluate(() => {
      const k = 'desu.demo.pedidos.v1';
      const lista = JSON.parse(localStorage.getItem(k));
      lista[lista.length - 1].criadoEm = new Date(Date.now() - 70000).toISOString();
      localStorage.setItem(k, JSON.stringify(lista));
    });
    await page.reload();
    await page.locator('#status-pill').waitFor();
    const esperado = d.fulfillment === 'entrega' ? 'Saiu para entrega' : 'Pronto para retirada';
    assert.equal(await page.locator('#status-pill').textContent(), esperado);
    await page.goto(origin + BASE);
    assert.equal(await page.locator('#cart-count').textContent(), '0');
  });

  await ctx.close();
}

await step('nenhuma chamada a /api/ e nenhum erro de JavaScript ou de CSP', async () => {
  assert.deepEqual(apiCalls, []);
  assert.deepEqual(errors, []);
});

await browser.close();
server.close();
fs.rmSync(site, { recursive: true, force: true });
console.log(`\nCapturas de tela em: ${OUT}`);
process.exit(failures ? 1 : 0);
