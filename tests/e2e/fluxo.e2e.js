// Teste de ponta a ponta no navegador (Chromium via Playwright), em celular e computador.
/* global document, window -- usados dentro de page.evaluate (rodam no navegador) */
// Uso: npm run test:e2e
// Requer Playwright:  npm install --no-save playwright  &&  npx playwright install chromium
import assert from 'node:assert/strict';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import zlib from 'node:zlib';
import { createRequire } from 'node:module';
import { ADMIN, startServer } from '../helpers.js';

let chromium;
try {
  ({ chromium } = createRequire(import.meta.url)('playwright'));
} catch {
  console.error('Playwright não encontrado. Instale com: npm install --no-save playwright && npx playwright install chromium');
  process.exit(1);
}

const OUT = path.resolve('test-results/e2e');
fs.mkdirSync(OUT, { recursive: true });

const freePort = () =>
  new Promise((resolve) => {
    const s = net.createServer().listen(0, '127.0.0.1', () => {
      const { port } = s.address();
      s.close(() => resolve(port));
    });
  });

/** Imagem de teste (gradiente) gerada na hora — NÃO é foto do produto. */
function testPng(w = 800, h = 600) {
  const t = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc = (b) => {
    let c = 0xffffffff;
    for (const x of b) c = t[(c ^ x) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type, data) => {
    const l = Buffer.alloc(4);
    l.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const c = Buffer.alloc(4);
    c.writeUInt32BE(crc(td));
    return Buffer.concat([l, td, c]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8;
  ihdr[9] = 2;
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const i = y * (w * 3 + 1) + 1 + x * 3;
      raw[i] = 255;
      raw[i + 1] = Math.round(120 + (100 * x) / w);
      raw[i + 2] = Math.round((60 * y) / h);
    }
  return Buffer.concat([Buffer.from([0x89, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]);
}

const port = await freePort();
const base = `http://127.0.0.1:${port}`;
const srv = await startServer({ port, env: { PORT: String(port), PUBLIC_ORIGIN: base } });
const browser = await chromium.launch();
const problems = [];
const results = [];

function watch(page, label) {
  page.on('console', (m) => {
    // 401 é a resposta esperada quando o painel verifica se já existe sessão ou a senha está errada.
    if (m.type() === 'error' && !/status of 401/.test(m.text())) problems.push(`[${label}] console: ${m.text()}`);
  });
  page.on('pageerror', (e) => problems.push(`[${label}] erro JS: ${e.message}`));
}

async function step(name, fn) {
  try {
    await fn();
    results.push(`ok   ${name}`);
  } catch (err) {
    results.push(`FALHA ${name}: ${err.message.split('\n')[0]}`);
    throw err;
  }
}

async function checkLayout(page, label) {
  const info = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    imgsWithoutAlt: [...document.images].filter((i) => !i.hasAttribute('alt')).length,
    brokenImgs: [...document.images].filter((i) => i.complete && i.naturalWidth === 0 && i.src).map((i) => i.src),
    unlabeled: [...document.querySelectorAll('input:not([type=hidden]), select, textarea')]
      .filter((el) => el.offsetParent !== null)
      .filter((el) => !(el.labels && el.labels.length) && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby'))
      .map((el) => el.id || el.name || el.type),
  }));
  assert.equal(info.overflow, false, `${label}: rolagem horizontal na página`);
  assert.equal(info.imgsWithoutAlt, 0, `${label}: imagem sem alt`);
  assert.deepEqual(info.brokenImgs, [], `${label}: imagem quebrada`);
  assert.deepEqual(info.unlabeled, [], `${label}: campo sem rótulo`);
}

try {
  // ---------- preparação pelo painel (via API) ----------
  const admin = srv.client();
  await admin.login();
  const addon = await admin.admin('POST', '/api/admin/addons', { name: 'Bacon extra', priceCents: 400, available: true }, { headers: { origin: base } });
  const ponto = await admin.admin(
    'POST',
    '/api/admin/option-groups',
    { name: 'Ponto da carne', kind: 'single', required: true, choices: [{ name: 'Ao ponto' }, { name: 'Bem passado' }] },
    { headers: { origin: base } }
  );
  await admin.admin('PUT', '/api/admin/products/1', { addonIds: [addon.data.id], optionGroupIds: [ponto.data.id] }, { headers: { origin: base } });
  await admin.admin('PUT', '/api/admin/settings', { delivery_enabled: true, delivery_fee_cents: 600, pickup_address: 'Rua Exemplo, 100 — Centro', contact_phone: '(11) 4000-0000' }, { headers: { origin: base } });

  for (const device of [
    { label: 'computador', viewport: { width: 1280, height: 800 }, isMobile: false, fulfillment: 'entrega', payment: 'pix' },
    { label: 'celular', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, fulfillment: 'retirada', payment: 'dinheiro' },
  ]) {
    const ctx = await browser.newContext({ viewport: device.viewport, isMobile: device.isMobile, hasTouch: device.hasTouch, locale: 'pt-BR' });
    const page = await ctx.newPage();
    watch(page, device.label);
    const L = device.label;

    await step(`${L}: cardápio carrega com placeholder de imagem`, async () => {
      await page.goto(base + '/');
      await page.getByRole('heading', { name: 'X-Bacon' }).waitFor();
      assert.equal(await page.locator('.image-placeholder').count(), 1);
      assert.match(await page.locator('#store-status').textContent(), /Aberto/);
      await checkLayout(page, `${L}/cardápio`);
      await page.screenshot({ path: `${OUT}/${L}-1-cardapio.png`, fullPage: true });
    });

    await step(`${L}: busca e filtros do cardápio`, async () => {
      await page.fill('#menu-search', 'bacon');
      await page.waitForFunction(() => /1 item encontrado/.test(document.querySelector('#filter-status').textContent));
      await page.fill('#menu-search', 'nada-disso');
      await page.getByRole('button', { name: 'Limpar filtros' }).waitFor();
      await page.getByRole('button', { name: 'Limpar filtros' }).click();
      await page.getByRole('heading', { name: 'X-Bacon' }).waitFor();
    });

    await step(`${L}: personaliza produto (opção obrigatória, adicional, quantidade, observação)`, async () => {
      await page.getByRole('button', { name: 'Adicionar X-Bacon ao carrinho' }).click();
      const dlg = page.locator('#product-dialog');
      await dlg.waitFor({ state: 'visible' });
      // opção obrigatória: sem escolher, o diálogo avisa
      await page.locator('#pd-submit').click();
      assert.match(await page.locator('#pd-error').textContent(), /Ponto da carne/);
      await dlg.getByLabel('Ao ponto').check();
      await dlg.getByLabel('Bacon extra').check();
      await dlg.getByRole('button', { name: 'Aumentar quantidade' }).click();
      await dlg.getByLabel(/Observação/).fill('sem cebola');
      assert.match(await page.locator('#pd-submit').textContent(), /R\$\s?57,80/);
      await checkLayout(page, `${L}/personalização`);
      await page.screenshot({ path: `${OUT}/${L}-2-personalizar.png` });
      await page.locator('#pd-submit').click();
      await dlg.waitFor({ state: 'hidden' });
      assert.equal(await page.locator('#cart-count').textContent(), '2');
    });

    await step(`${L}: carrinho edita quantidades e recalcula`, async () => {
      await page.locator('#open-cart').click();
      const cartDlg = page.locator('#cart-dialog');
      await cartDlg.waitFor({ state: 'visible' });
      await cartDlg.getByRole('button', { name: 'Aumentar' }).click();
      assert.equal(await cartDlg.locator('.qty').textContent(), '3');
      assert.match(await page.locator('#cart-subtotal').textContent(), /86,70/);
      await cartDlg.getByRole('button', { name: 'Diminuir' }).click();
      assert.match(await page.locator('#cart-subtotal').textContent(), /57,80/);
      await page.screenshot({ path: `${OUT}/${L}-3-carrinho.png` });
      await cartDlg.getByRole('link', { name: 'Finalizar pedido' }).click();
    });

    await step(`${L}: checkout valida campos e mostra total do servidor`, async () => {
      await page.waitForURL('**/checkout.html');
      await page.locator('#checkout-form').waitFor({ state: 'visible' });
      await page.locator('#submit-order').click();
      assert.match(await page.locator('#form-alert').textContent(), /Confira/);
      assert.equal(await page.locator('#name').getAttribute('aria-invalid'), 'true');
      await page.getByLabel('Nome').fill(`Cliente ${L}`);
      await page.getByLabel(/Telefone/).fill('(11) 98765-4321');
      if (device.fulfillment === 'entrega') {
        await page.locator('input[name=fulfillment][value=entrega]').check();
        await page.getByLabel('Rua').fill('Rua das Palmeiras');
        await page.getByLabel('Número').fill('45');
        await page.getByLabel('Bairro').fill('Jardim');
        await page.waitForFunction(() => /63,80/.test(document.querySelector('#sum-total').textContent));
      } else {
        await page.waitForFunction(() => /57,80/.test(document.querySelector('#sum-total').textContent));
        assert.match(await page.locator('#pickup-address').textContent(), /Rua Exemplo/);
      }
      await page.locator(`input[name=payment][value=${device.payment}]`).check();
      if (device.payment === 'dinheiro') await page.getByLabel(/Troco/).fill('100,00');
      await checkLayout(page, `${L}/checkout`);
      await page.screenshot({ path: `${OUT}/${L}-4-checkout.png`, fullPage: true });
    });

    await step(`${L}: confirma pedido e abre acompanhamento`, async () => {
      await page.locator('#submit-order').click();
      await page.waitForURL('**/pedido.html#*');
      await page.locator('#status-pill').waitFor();
      assert.equal(await page.locator('#status-pill').textContent(), 'Recebido');
      assert.match(await page.locator('#sum-total').textContent(), device.fulfillment === 'entrega' ? /63,80/ : /57,80/);
      assert.match(await page.locator('#items').textContent(), /sem cebola/);
      assert.match(await page.locator('#items').textContent(), /Ao ponto/);
      await checkLayout(page, `${L}/pedido`);
      await page.screenshot({ path: `${OUT}/${L}-5-pedido.png`, fullPage: true });
      // carrinho esvaziado
      await page.goto(base + '/');
      assert.equal(await page.locator('#cart-count').textContent(), '0');
    });
    await ctx.close();
  }

  // ---------- painel administrativo ----------
  const actx = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'pt-BR' });
  const ap = await actx.newPage();
  watch(ap, 'painel');

  await step('painel: exige login e recusa senha errada', async () => {
    await ap.goto(base + '/admin/');
    await ap.locator('#login-view').waitFor({ state: 'visible' });
    await ap.getByLabel('E-mail').fill(ADMIN.email);
    await ap.getByLabel('Senha').fill('senha errada mas comprida');
    await ap.getByRole('button', { name: 'Entrar' }).click();
    await ap.waitForFunction(() => /incorretos/.test(document.querySelector('#login-alert').textContent));
    await ap.screenshot({ path: `${OUT}/painel-1-login.png` });
  });

  await step('painel: login e lista de pedidos', async () => {
    await ap.getByLabel('Senha').fill(ADMIN.password);
    await ap.getByRole('button', { name: 'Entrar' }).click();
    await ap.locator('#app-view').waitFor({ state: 'visible' });
    await ap.locator('.order-card').first().waitFor();
    assert.equal(await ap.locator('.order-card').count(), 2);
    await ap.screenshot({ path: `${OUT}/painel-2-pedidos.png`, fullPage: true });
  });

  await step('painel: muda status e cliente vê a mudança', async () => {
    const card = ap.locator('.order-card').first();
    await card.getByRole('button', { name: 'Marcar: Em preparo' }).click();
    await ap.waitForFunction(() => [...document.querySelectorAll('.order-card .status-pill')].some((p) => p.textContent === 'Em preparo'));
    const token = srv.db.prepare('SELECT tracking_token FROM orders WHERE status = ?').get('em_preparo').tracking_token;
    const cp = await actx.newPage();
    watch(cp, 'cliente');
    await cp.goto(`${base}/pedido.html#${token}`);
    await cp.locator('#status-pill').waitFor();
    assert.equal(await cp.locator('#status-pill').textContent(), 'Em preparo');
    await cp.close();
  });

  await step('painel: envia imagem do produto e cardápio exibe com selo "Imagem ilustrativa"', async () => {
    await ap.getByRole('tab', { name: 'Cardápio' }).click();
    await ap.getByRole('button', { name: 'Editar' }).last().click();
    const dlg = ap.locator('#product-editor');
    await dlg.waitFor({ state: 'visible' });
    const file = path.join(OUT, 'imagem-de-teste.png');
    fs.writeFileSync(file, testPng());
    await dlg.locator('input[type=file]').setInputFiles(file);
    await dlg.getByLabel(/Texto alternativo/).fill('Imagem de teste do X-Bacon');
    await ap.screenshot({ path: `${OUT}/painel-3-editor.png` });
    await ap.getByRole('button', { name: 'Salvar produto' }).click();
    await dlg.waitFor({ state: 'hidden' });
    const pg = await actx.newPage();
    watch(pg, 'cardápio-com-imagem');
    await pg.goto(base + '/');
    const img = pg.locator('.product-card img').first();
    await img.waitFor();
    assert.equal(await img.getAttribute('alt'), 'Imagem de teste do X-Bacon');
    assert.equal(await pg.locator('.product-card .illustrative-tag').first().textContent(), 'Imagem ilustrativa');
    await pg.waitForFunction(() => document.querySelector('.product-card img').naturalWidth > 0);
    await checkLayout(pg, 'cardápio-com-imagem');
    await pg.screenshot({ path: `${OUT}/cardapio-com-imagem.png` });
    await pg.close();
  });

  await step('painel: marca produto como indisponível e o cardápio bloqueia', async () => {
    await ap.locator('.data-item').filter({ hasText: 'X-Bacon' }).getByLabel('Disponível').uncheck();
    await ap.waitForTimeout(300);
    const pg = await actx.newPage();
    await pg.goto(base + '/');
    await pg.locator('.tag-unavailable').waitFor();
    assert.equal(await pg.getByRole('button', { name: /Adicionar X-Bacon/ }).count(), 0);
    await pg.close();
    await ap.screenshot({ path: `${OUT}/painel-4-cardapio.png`, fullPage: true });
  });

  await step('painel: abas de adicionais, cupons, configurações e conta carregam', async () => {
    for (const [tab, check] of [
      ['Adicionais', 'Bacon extra'],
      ['Cupons', 'Nenhum cupom cadastrado.'],
      ['Configurações', 'Salvar configurações'],
      ['Minha conta', 'Trocar senha'],
    ]) {
      await ap.getByRole('tab', { name: tab }).click();
      await ap.getByText(check, { exact: true }).first().waitFor();
      await ap.screenshot({ path: `${OUT}/painel-aba-${tab.toLowerCase().replace(/\s+/g, '-')}.png`, fullPage: true });
    }
    // cria um cupom pela interface
    await ap.getByRole('tab', { name: 'Cupons' }).click();
    await ap.getByLabel(/Código/).fill('BEMVINDO10');
    await ap.getByLabel(/^Valor/).fill('10');
    await ap.getByRole('button', { name: 'Criar cupom' }).click();
    await ap.getByText('BEMVINDO10', { exact: true }).waitFor();
    // painel no celular
    await ap.setViewportSize({ width: 390, height: 844 });
    await ap.getByRole('tab', { name: 'Pedidos' }).click();
    await ap.locator('.order-card').first().waitFor();
    await checkLayout(ap, 'painel/celular');
    await ap.screenshot({ path: `${OUT}/painel-celular-pedidos.png`, fullPage: true });
    await ap.setViewportSize({ width: 1280, height: 900 });
  });

  await step('painel: sair encerra a sessão', async () => {
    await ap.getByRole('button', { name: 'Sair' }).click();
    await ap.locator('#login-view').waitFor({ state: 'visible' });
    const r = await ap.evaluate(() => fetch('/api/admin/orders').then((x) => x.status));
    assert.equal(r, 401);
  });

  await actx.close();
  assert.deepEqual(problems, [], 'erros no console/JS do navegador');
  results.push('ok   nenhum erro de JavaScript ou de CSP no console');
} catch (err) {
  process.exitCode = 1;
  console.error(err);
} finally {
  await browser.close();
  await srv.close();
  console.log(`\n${results.join('\n')}`);
  if (problems.length) console.log(`\nProblemas no console:\n${problems.join('\n')}`);
  console.log(`\nCapturas de tela em: ${OUT}`);
}
