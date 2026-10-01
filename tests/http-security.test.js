// Segurança HTTP: cabeçalhos, arquivos estáticos, corpo das requisições, uploads e erros.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { after, before, describe, it } from 'node:test';
import { buildConfig } from '../server/config.js';
import { orderBody, startServer } from './helpers.js';

/** Gera um PNG válido (w×h, RGB) sem dependências externas. */
function makePng(w, h) {
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc = (buf) => {
    let c = 0xffffffff;
    for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const c = Buffer.alloc(4);
    c.writeUInt32BE(crc(td));
    return Buffer.concat([len, td, c]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8;
  ihdr[9] = 2;
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) raw[y * (w * 3 + 1) + 1 + x * 3] = 255;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

describe('segurança HTTP', () => {
  let srv;
  before(async () => {
    srv = await startServer();
  });
  after(() => srv.close());

  it('envia cabeçalhos de segurança em páginas e na API', async () => {
    const c = srv.client();
    for (const url of ['/', '/api/menu', '/admin/', '/nao-existe']) {
      const r = await c.get(url);
      const csp = r.headers.get('content-security-policy');
      assert.match(csp, /default-src 'self'/, url);
      assert.match(csp, /script-src 'self'(;|$)/, url);
      assert.doesNotMatch(csp, /unsafe-inline|unsafe-eval/, url);
      assert.match(csp, /frame-ancestors 'none'/, url);
      assert.equal(r.headers.get('x-content-type-options'), 'nosniff', url);
      assert.equal(r.headers.get('x-frame-options'), 'DENY', url);
      assert.ok(r.headers.get('referrer-policy'), url);
      assert.equal(r.headers.get('x-powered-by'), null, url);
      assert.equal(r.headers.get('access-control-allow-origin'), null, 'sem CORS liberado');
    }
  });

  it('não serve arquivos fora da pasta pública (path traversal, ocultos, código, banco)', async () => {
    const c = srv.client();
    const attempts = [
      '/../server/app.js',
      '/%2e%2e/server/app.js',
      '/..%2fserver%2fapp.js',
      '/%2e%2e%2f%2e%2e%2fetc%2fpasswd',
      '/..%5c..%5cpackage.json',
      '/.env',
      '/.git/config',
      '/%2egit/config',
      '/package.json',
      '/server/app.js',
      '/data/desu.db',
      '/uploads/products/../../desu.db',
      '/uploads/products/%2e%2e%2f%2e%2e%2fdesu.db',
      '/uploads/products/..%2f..%2fdesu.db',
      '/index.html%00.png',
      '/%E0%A4%A',
    ];
    for (const url of attempts) {
      const r = await c.get(url);
      assert.ok([400, 404].includes(r.status), `${url} → ${r.status}`);
      assert.equal(typeof r.data === 'string' && r.data.includes('createApp'), false, url);
    }
  });

  it('redireciona pastas para o caminho normalizado (sem redirecionamento aberto)', async () => {
    const r = await srv.client().get('/admin');
    assert.equal(r.status, 301);
    assert.equal(r.headers.get('location'), '/admin/');
  });

  it('API exige JSON, limita tamanho e trata JSON malformado', async () => {
    const c = srv.client();
    const wrongType = await c.request('POST', '/api/orders/quote', { raw: '{}', contentType: 'text/plain' });
    assert.equal(wrongType.status, 415);
    const malformed = await c.request('POST', '/api/orders/quote', { raw: '{"items":', contentType: 'application/json' });
    assert.equal(malformed.status, 400);
    const big = await c.post('/api/orders/quote', { items: [], pad: 'x'.repeat(40 * 1024) });
    assert.equal(big.status, 413);
    const arr = await c.request('POST', '/api/orders/quote', { raw: '[1,2]', contentType: 'application/json' });
    assert.equal(arr.status, 400);
    assert.equal((await c.get('/api/nao-existe')).status, 404);
    assert.equal((await c.request('DELETE', '/api/menu')).status, 405);
  });

  it('upload de imagem: aceita só imagem de verdade, com nome aleatório', async () => {
    const c = srv.client();
    await c.login();
    const put = (raw, contentType) => c.request('PUT', '/api/admin/products/1/image', { raw, contentType, headers: { 'x-csrf-token': c.csrf } });

    assert.equal((await put('<html><script>alert(1)</script></html>', 'text/html')).status, 415);
    assert.equal((await put('<html><script>alert(1)</script></html>', 'image/png')).status, 415, 'conteúdo não é PNG');
    const svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>';
    assert.equal((await put(svg, 'image/svg+xml')).status, 415, 'SVG recusado');
    const fakeGif = Buffer.concat([Buffer.from('GIF89a'), Buffer.alloc(100)]);
    assert.equal((await put(fakeGif, 'image/gif')).status, 415);

    const png = makePng(40, 30);
    const ok = await put(png, 'image/png');
    assert.equal(ok.status, 200, JSON.stringify(ok.data));

    const menu = await srv.client().get('/api/menu');
    const img = menu.data.categories[0].products[0].image;
    assert.ok(img, 'produto agora tem imagem');
    assert.match(img.src, /^\/uploads\/products\/[a-f0-9]{32}\.(png|webp)$/);
    assert.equal(img.illustrative, true, 'por padrão marcada como ilustrativa');
    assert.ok(img.alt.length > 0, 'tem texto alternativo');

    const file = await fetch(srv.base + img.src);
    assert.equal(file.status, 200);
    assert.match(file.headers.get('content-type'), /^image\/(png|webp)$/);
    assert.match(file.headers.get('cache-control'), /immutable/);
    assert.equal(file.headers.get('x-content-type-options'), 'nosniff');

    // trocar a imagem apaga o arquivo antigo
    const oldName = path.basename(img.src);
    assert.equal((await put(makePng(20, 20), 'image/png')).status, 200);
    assert.equal(fs.existsSync(path.join(srv.dataDir, 'uploads', 'products', oldName)), false);

    // arquivo grande demais
    const huge = Buffer.concat([png, Buffer.alloc(6 * 1024 * 1024)]);
    assert.equal((await put(huge, 'image/png')).status, 413);

    // remover imagem volta ao placeholder
    assert.equal((await c.admin('DELETE', '/api/admin/products/1/image')).status, 200);
    const menu2 = await srv.client().get('/api/menu');
    assert.equal(menu2.data.categories[0].products[0].image, null);
  });

  it('limita a criação de pedidos por IP (anti-abuso)', async () => {
    const c = srv.client();
    const statuses = [];
    for (let i = 0; i < 11; i++) statuses.push((await c.post('/api/orders', orderBody())).status);
    assert.deepEqual(statuses.slice(0, 10), Array(10).fill(201));
    assert.equal(statuses[10], 429);
  });
});

describe('erros inesperados', () => {
  it('respondem com mensagem genérica e registram o detalhe só no log', async () => {
    const srv = await startServer();
    srv.db.exec('DROP TABLE settings'); // força uma falha interna
    const r = await srv.client().get('/api/menu');
    assert.equal(r.status, 500);
    assert.equal(r.data.error, 'Ocorreu um erro inesperado. Tente novamente.');
    assert.ok(r.data.requestId);
    assert.equal(JSON.stringify(r.data).includes('settings'), false, 'não vaza detalhes internos');
    const logged = srv.logs.find((l) => l.event === 'unhandled_error');
    assert.equal(logged.reqId, r.data.requestId);
    await srv.close();
  });
});

describe('configuração de produção', () => {
  it('recusa iniciar em produção sem HTTPS', () => {
    assert.throws(() => buildConfig({ NODE_ENV: 'production' }), /PUBLIC_ORIGIN/);
    assert.throws(() => buildConfig({ NODE_ENV: 'production', PUBLIC_ORIGIN: 'http://loja.com' }), /https/);
  });

  it('em produção usa cookie __Host- com Secure e liga HSTS', async () => {
    const cfg = buildConfig({ NODE_ENV: 'production', PUBLIC_ORIGIN: 'https://loja.exemplo.com.br' });
    assert.equal(cfg.secureCookies, true);
    assert.equal(cfg.sessionCookieName, '__Host-desu_sid');
    assert.equal(cfg.allowedOrigins.has('http://localhost:3000'), false, 'localhost não é aceito em produção');
    const { securityHeaders } = await import('../server/http/security.js');
    const h = securityHeaders(cfg);
    assert.match(h['Strict-Transport-Security'], /max-age=31536000/);
    const { sessionCookie } = await import('../server/auth/sessions.js');
    assert.match(sessionCookie(cfg, 'abc', 60), /^__Host-desu_sid=abc; Path=\/; HttpOnly; SameSite=Strict; Max-Age=60; Secure$/);
  });
});
