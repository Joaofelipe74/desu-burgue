// Utilitários de teste: sobe o servidor real numa porta livre, com banco temporário.
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { createApp } from '../server/app.js';
import { hashPassword } from '../server/auth/passwords.js';
import { buildConfig } from '../server/config.js';
import { openDatabase } from '../server/db.js';
import { createLogger } from '../server/log.js';

export const ORIGIN = 'http://localhost:4321';
export const ADMIN = { email: 'dono@desuburguer.test', password: 'uma frase bem longa e secreta 42' };

export async function startServer({ env = {}, overrides = {}, withAdmin = true, port = 0 } = {}) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'desu-test-'));
  const config = buildConfig({ NODE_ENV: 'test', PORT: '4321', PUBLIC_ORIGIN: ORIGIN, DATA_DIR: dataDir, ...env }, overrides);
  const logs = [];
  const log = createLogger('debug', (line) => logs.push(JSON.parse(line)));
  const db = openDatabase(path.join(dataDir, 'desu.db'));
  if (withAdmin) {
    db.prepare('INSERT INTO admin_users (email, name, password_hash) VALUES (?, ?, ?)').run(
      ADMIN.email,
      'Dono',
      await hashPassword(ADMIN.password)
    );
  }
  const server = http.createServer(createApp({ config, db, log }));
  await new Promise((r) => server.listen(port, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;
  return {
    base,
    db,
    config,
    logs,
    dataDir,
    client: () => createClient(base),
    async close() {
      await new Promise((r) => server.close(r));
      db.close();
      fs.rmSync(dataDir, { recursive: true, force: true });
    },
  };
}

/** Cliente HTTP com "pote" de cookies, imitando um navegador. */
export function createClient(base) {
  const jar = new Map();
  return {
    jar,
    csrf: null,
    async request(method, url, { json, raw, contentType, headers = {} } = {}) {
      const h = { ...headers };
      if (jar.size) h.cookie = [...jar].map(([k, v]) => `${k}=${v}`).join('; ');
      let body;
      if (json !== undefined && method !== 'GET' && method !== 'HEAD') {
        body = JSON.stringify(json);
        h['content-type'] = 'application/json';
      } else if (raw !== undefined) {
        body = raw;
        h['content-type'] = contentType || 'application/octet-stream';
      }
      const res = await fetch(base + url, { method, headers: h, body, redirect: 'manual' });
      for (const c of res.headers.getSetCookie()) {
        const [pair] = c.split(';');
        const i = pair.indexOf('=');
        const k = pair.slice(0, i);
        const v = pair.slice(i + 1);
        if (v === '' || /Max-Age=0/i.test(c)) jar.delete(k);
        else jar.set(k, v);
      }
      const text = await res.text();
      let data = null;
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
      return { status: res.status, headers: res.headers, data, setCookie: res.headers.getSetCookie() };
    },
    get(url, opts) {
      return this.request('GET', url, opts);
    },
    post(url, json, opts = {}) {
      return this.request('POST', url, { json, ...opts });
    },
    /** Login de administrador; guarda o token CSRF. */
    async login(email = ADMIN.email, password = ADMIN.password) {
      const r = await this.post('/api/admin/login', { email, password });
      if (r.status === 200) this.csrf = r.data.csrfToken;
      return r;
    },
    /** Requisição de administrador com token CSRF. */
    admin(method, url, json, opts = {}) {
      return this.request(method, url, { json, ...opts, headers: { 'x-csrf-token': this.csrf || '', ...(opts.headers || {}) } });
    },
  };
}

export const uuid = () => crypto.randomUUID();

export function orderBody(overrides = {}) {
  return {
    idempotencyKey: uuid(),
    items: [{ productId: 1, quantity: 2, addonIds: [], notes: '' }],
    couponCode: '',
    fulfillment: 'retirada',
    customer: { name: 'Maria Teste', phone: '(11) 91234-5678' },
    paymentMethod: 'pix',
    notes: '',
    expectedTotalCents: 4980,
    ...overrides,
  };
}
