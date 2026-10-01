// Acesso administrativo: autenticação, autorização, CSRF, sessão e limites.
import assert from 'node:assert/strict';
import { after, before, describe, it } from 'node:test';
import { createRateLimiter } from '../server/http/security.js';
import { ADMIN, ORIGIN, startServer } from './helpers.js';

const ADMIN_ROUTES = [
  ['GET', '/api/admin/session'],
  ['GET', '/api/admin/orders'],
  ['GET', '/api/admin/orders/1'],
  ['PATCH', '/api/admin/orders/1/status'],
  ['GET', '/api/admin/categories'],
  ['POST', '/api/admin/categories'],
  ['PUT', '/api/admin/categories/1'],
  ['DELETE', '/api/admin/categories/1'],
  ['GET', '/api/admin/products'],
  ['POST', '/api/admin/products'],
  ['PUT', '/api/admin/products/1'],
  ['PUT', '/api/admin/products/1/image'],
  ['DELETE', '/api/admin/products/1/image'],
  ['GET', '/api/admin/addons'],
  ['POST', '/api/admin/addons'],
  ['GET', '/api/admin/coupons'],
  ['POST', '/api/admin/coupons'],
  ['GET', '/api/admin/settings'],
  ['PUT', '/api/admin/settings'],
  ['POST', '/api/admin/logout'],
  ['POST', '/api/admin/password'],
];

describe('segurança do painel administrativo', () => {
  let srv;
  before(async () => {
    // limite por IP mais alto aqui porque todos os testes saem do mesmo IP;
    // o limite real é testado separadamente no fim do arquivo.
    srv = await startServer({ overrides: { limiters: { login: createRateLimiter({ windowMs: 60_000, max: 1000 }) } } });
  });
  after(() => srv.close());

  it('bloqueia TODAS as rotas administrativas sem login (401)', async () => {
    const c = srv.client();
    for (const [method, url] of ADMIN_ROUTES) {
      const r = await c.request(method, url, { json: {} });
      assert.equal(r.status, 401, `${method} ${url}`);
    }
  });

  it('cookie forjado ou de sessão inexistente não dá acesso', async () => {
    const c = srv.client();
    c.jar.set(srv.config.sessionCookieName, 'a'.repeat(43));
    assert.equal((await c.get('/api/admin/orders')).status, 401);
  });

  it('login errado devolve mensagem genérica (não revela se o e-mail existe)', async () => {
    const c = srv.client();
    const a = await c.login(ADMIN.email, 'senha errada mas comprida');
    const b = await c.login('ninguem@exemplo.com', 'senha errada mas comprida');
    assert.equal(a.status, 401);
    assert.equal(b.status, 401);
    assert.equal(a.data.error, b.data.error);
  });

  it('login correto cria cookie HttpOnly + SameSite=Strict e não devolve dados sensíveis', async () => {
    const c = srv.client();
    const r = await c.login();
    assert.equal(r.status, 200);
    const cookie = r.setCookie.join(';');
    assert.match(cookie, /HttpOnly/);
    assert.match(cookie, /SameSite=Strict/);
    assert.match(cookie, /Path=\//);
    assert.equal(JSON.stringify(r.data).includes('hash'), false);
    assert.ok(r.data.csrfToken);
    // no banco fica só o hash da sessão
    const token = c.jar.get(srv.config.sessionCookieName);
    const row = srv.db.prepare('SELECT * FROM sessions').all().find((s) => s.id_hash === token);
    assert.equal(row, undefined, 'token puro não é salvo no banco');
  });

  it('exige token CSRF em operações de escrita', async () => {
    const c = srv.client();
    await c.login();
    const noToken = await c.request('POST', '/api/admin/categories', { json: { name: 'Bebidas' } });
    assert.equal(noToken.status, 403);
    const wrong = await c.request('POST', '/api/admin/categories', { json: { name: 'Bebidas' }, headers: { 'x-csrf-token': 'x' } });
    assert.equal(wrong.status, 403);
    const ok = await c.admin('POST', '/api/admin/categories', { name: 'Bebidas' });
    assert.equal(ok.status, 201);
  });

  it('bloqueia requisições de outros sites (Origin / Sec-Fetch-Site)', async () => {
    const c = srv.client();
    await c.login();
    const evil = await c.admin('POST', '/api/admin/categories', { name: 'Hack' }, { headers: { origin: 'https://site-malicioso.com' } });
    assert.equal(evil.status, 403);
    const cross = await c.admin('POST', '/api/admin/categories', { name: 'Hack2' }, { headers: { 'sec-fetch-site': 'cross-site' } });
    assert.equal(cross.status, 403);
    const same = await c.admin('POST', '/api/admin/categories', { name: 'Sobremesas' }, { headers: { origin: ORIGIN, 'sec-fetch-site': 'same-origin' } });
    assert.equal(same.status, 201);
    // login vindo de outro site também é bloqueado
    const loginEvil = await srv.client().post('/api/admin/login', { email: ADMIN.email, password: ADMIN.password }, { headers: { origin: 'https://x.com' } });
    assert.equal(loginEvil.status, 403);
  });

  it('logout invalida a sessão no servidor', async () => {
    const c = srv.client();
    await c.login();
    const cookieBefore = c.jar.get(srv.config.sessionCookieName);
    assert.equal((await c.admin('POST', '/api/admin/logout', {})).status, 200);
    c.jar.set(srv.config.sessionCookieName, cookieBefore); // tenta reutilizar o cookie antigo
    assert.equal((await c.get('/api/admin/orders')).status, 401);
  });

  it('sessão expira por inatividade', async () => {
    const c = srv.client();
    await c.login();
    srv.db.prepare("UPDATE sessions SET last_seen_at = '2000-01-01T00:00:00.000Z'").run();
    assert.equal((await c.get('/api/admin/orders')).status, 401);
  });

  it('troca de senha exige a senha atual, valida a nova e encerra outras sessões', async () => {
    const a = srv.client();
    const b = srv.client();
    await a.login();
    await b.login();
    const wrong = await a.admin('POST', '/api/admin/password', { currentPassword: 'errada', newPassword: 'outra frase longa e segura 99' });
    assert.equal(wrong.status, 400);
    const weak = await a.admin('POST', '/api/admin/password', { currentPassword: ADMIN.password, newPassword: 'curta' });
    assert.equal(weak.status, 400);
    const ok = await a.admin('POST', '/api/admin/password', { currentPassword: ADMIN.password, newPassword: 'outra frase longa e segura 99' });
    assert.equal(ok.status, 200);
    assert.equal((await b.get('/api/admin/orders')).status, 401, 'a outra sessão caiu');
    assert.equal((await a.get('/api/admin/orders')).status, 200, 'a sessão atual foi renovada');
    // volta a senha original para os demais testes
    a.csrf = ok.data.csrfToken;
    const back = await a.admin('POST', '/api/admin/password', { currentPassword: 'outra frase longa e segura 99', newPassword: ADMIN.password });
    assert.equal(back.status, 200);
  });

  it('valida entradas do painel e impede campos extras', async () => {
    const c = srv.client();
    await c.login();
    const r1 = await c.admin('POST', '/api/admin/products', { name: 'X', categoryId: 1, priceCents: -1 });
    assert.equal(r1.status, 400);
    const r2 = await c.admin('POST', '/api/admin/products', { name: 'X', categoryId: 1, priceCents: 1000, role: 'admin' });
    assert.equal(r2.status, 400);
    const r3 = await c.admin('POST', '/api/admin/coupons', { code: 'X Y', kind: 'percent', value: 10 });
    assert.equal(r3.status, 400);
    const r4 = await c.admin('POST', '/api/admin/coupons', { code: 'MUITO', kind: 'percent', value: 150 });
    assert.equal(r4.status, 400);
    const r5 = await c.admin('PUT', '/api/admin/settings', { pickup_enabled: false, delivery_enabled: false });
    assert.equal(r5.status, 400);
    const r6 = await c.admin('PATCH', '/api/admin/orders/abc/status', { status: 'em_preparo', fromStatus: 'recebido' });
    assert.equal(r6.status, 404);
  });

  it('texto com HTML/script é guardado como texto (sem execução no servidor)', async () => {
    const c = srv.client();
    await c.login();
    const payload = '<img src=x onerror=alert(1)>';
    const r = await c.admin('POST', '/api/admin/products', { name: payload, categoryId: 1, priceCents: 1000 });
    assert.equal(r.status, 201);
    const menu = await srv.client().get('/api/menu');
    const names = menu.data.categories.flatMap((cat) => cat.products.map((p) => p.name));
    assert.ok(names.includes(payload), 'devolvido como dado JSON; o navegador usa textContent');
    assert.match(menu.headers.get('content-type'), /application\/json/);
    await c.admin('PUT', `/api/admin/products/${r.data.id}`, { archived: true });
  });

  it('bloqueia a conta após 5 senhas erradas e limita tentativas por IP', async () => {
    const c = srv.client();
    for (let i = 0; i < 5; i++) {
      const r = await c.login(ADMIN.email, `errada numero ${i} bem comprida`);
      assert.equal(r.status, 401);
    }
    const locked = await c.login(); // senha certa, mas conta bloqueada
    assert.equal(locked.status, 429);
    assert.ok(srv.logs.some((l) => l.event === 'account_locked'));
    // nenhum log contém a senha
    assert.equal(JSON.stringify(srv.logs).includes(ADMIN.password), false);
    // desbloqueia para o próximo teste
    srv.db.prepare('UPDATE admin_users SET locked_until = NULL, failed_attempts = 0').run();
  });
});

describe('limite de tentativas de login por IP', () => {
  it('responde 429 depois do limite', async () => {
    const srv = await startServer();
    try {
      const statuses = [];
      for (let i = 0; i < 12; i++) {
        const r = await srv.client().login(`pessoa${i}@exemplo.com`, 'qualquer senha longa demais');
        statuses.push(r.status);
      }
      assert.ok(statuses.slice(0, 10).every((s) => s === 401));
      assert.equal(statuses[10], 429);
    } finally {
      await srv.close();
    }
  });
});
