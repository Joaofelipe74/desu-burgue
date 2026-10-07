// Rotas do painel administrativo. Todas (exceto o login) exigem sessão de
// administrador; as que alteram dados exigem também o token anti-CSRF.
import path from 'node:path';
import { dummyHash, hashPassword, needsRehash, passwordProblem, verifyPassword, PASSWORD_MAX } from '../auth/passwords.js';
import {
  clearSessionCookie,
  createSession,
  destroySession,
  destroyUserSessions,
  loadSession,
  safeEqual,
  sessionCookie,
} from '../auth/sessions.js';
import { nowIso } from '../db.js';
import { readBinary, readJson } from '../http/body.js';
import { HttpError, unauthorized, forbidden } from '../http/errors.js';
import { parseId } from '../http/router.js';
import { rateLimit } from '../http/security.js';
import { maskEmail } from '../log.js';
import { createCoupon, listCoupons, updateCoupon } from '../services/coupons.js';
import { illustrationList } from '../services/illustrations.js';
import * as options from '../services/options.js';
import { tagList } from '../services/tags.js';
import { getSharp, removeImageFiles, storeProductImage } from '../services/images.js';
import * as menu from '../services/menu.js';
import { getOrderForAdmin, listOrders, updateOrderStatus } from '../services/orders.js';
import { getSettings, updateSettings } from '../services/settings.js';
import { onlyKeys, text } from '../validation.js';

const LOCK_AFTER_FAILURES = 5;
const LOCK_MINUTES = 15;

export function registerAdminRoutes(router, { limiters, sendJson }) {
  const audit = (ctx, action, entity, entityId = null, details = {}) => {
    ctx.db
      .prepare('INSERT INTO audit_log (admin_user_id, action, entity, entity_id, details) VALUES (?, ?, ?, ?, ?)')
      .run(ctx.session.user.id, action, entity, entityId, JSON.stringify(details));
    ctx.log.info('admin_action', { reqId: ctx.reqId, userId: ctx.session.user.id, action, entity, entityId });
  };

  /** Exige sessão válida de administrador (e token CSRF em operações de escrita). */
  const requireAdmin = (ctx) => {
    ctx.res.setHeader('Cache-Control', 'no-store');
    const session = loadSession(ctx.db, ctx.req, ctx.config);
    if (!session) throw unauthorized('Sua sessão expirou. Faça login novamente.');
    if (session.user.role !== 'admin') throw forbidden();
    if (!['GET', 'HEAD'].includes(ctx.req.method)) {
      const sent = ctx.req.headers['x-csrf-token'];
      if (!sent || !safeEqual(sent, session.csrfToken)) {
        ctx.log.warn('csrf_rejected', { reqId: ctx.reqId, userId: session.user.id, path: ctx.pathname });
        throw forbidden('Sessão inválida para esta ação. Recarregue a página.');
      }
    }
    ctx.session = session;
  };

  // ---------- login / sessão ----------

  router.post('/api/admin/login', rateLimit(limiters.login, 'login'), async (ctx) => {
    ctx.res.setHeader('Cache-Control', 'no-store');
    const body = await readJson(ctx.req, 4096);
    onlyKeys(body, ['email', 'password'], 'login');
    const email = text(body.email, { field: 'o e-mail', min: 3, max: 254 }).toLowerCase();
    const password = typeof body.password === 'string' ? body.password : '';
    const generic = new HttpError(401, 'E-mail ou senha incorretos.');

    // Limite por e-mail (vale também para e-mails que não existem, para não revelar quais existem).
    const perEmail = limiters.loginEmail.hit(`email:${email}`);
    if (!perEmail.allowed) {
      ctx.res.setHeader('Retry-After', String(perEmail.retryAfterSec));
      ctx.log.warn('login_throttled', { reqId: ctx.reqId, email: maskEmail(email), ip: ctx.ip });
      throw new HttpError(429, 'Muitas tentativas. Aguarde alguns minutos e tente novamente.');
    }

    const user = ctx.db.prepare('SELECT * FROM admin_users WHERE email = ?').get(email);
    if (user && user.locked_until && Date.parse(user.locked_until) > Date.now()) {
      await verifyPassword(password, await dummyHash()); // mesmo tempo de resposta
      ctx.log.warn('login_locked', { reqId: ctx.reqId, userId: user.id, ip: ctx.ip });
      throw new HttpError(429, 'Muitas tentativas. Aguarde alguns minutos e tente novamente.');
    }

    const ok =
      password.length > 0 && password.length <= PASSWORD_MAX * 4
        ? await verifyPassword(password, user ? user.password_hash : await dummyHash())
        : false;

    if (!user || !ok || user.active !== 1) {
      if (user) {
        const failures = user.failed_attempts + 1;
        if (failures >= LOCK_AFTER_FAILURES) {
          const until = new Date(Date.now() + LOCK_MINUTES * 60 * 1000).toISOString();
          ctx.db.prepare('UPDATE admin_users SET failed_attempts = 0, locked_until = ? WHERE id = ?').run(until, user.id);
          ctx.log.warn('account_locked', { reqId: ctx.reqId, userId: user.id, ip: ctx.ip });
        } else {
          ctx.db.prepare('UPDATE admin_users SET failed_attempts = ? WHERE id = ?').run(failures, user.id);
        }
      }
      ctx.log.warn('login_failed', { reqId: ctx.reqId, email: maskEmail(email), ip: ctx.ip });
      throw generic;
    }

    if (needsRehash(user.password_hash)) {
      ctx.db.prepare('UPDATE admin_users SET password_hash = ? WHERE id = ?').run(await hashPassword(password), user.id);
    }
    ctx.db
      .prepare('UPDATE admin_users SET failed_attempts = 0, locked_until = NULL, last_login_at = ? WHERE id = ?')
      .run(nowIso(), user.id);
    limiters.loginEmail.reset(`email:${email}`);

    const s = createSession(ctx.db, user.id, ctx.config);
    ctx.res.setHeader('Set-Cookie', sessionCookie(ctx.config, s.token, s.maxAgeSec));
    ctx.log.info('login_success', { reqId: ctx.reqId, userId: user.id, ip: ctx.ip });
    sendJson(ctx, 200, { user: { name: user.name, email: user.email }, csrfToken: s.csrfToken });
  });

  router.get('/api/admin/session', requireAdmin, (ctx) => {
    sendJson(ctx, 200, {
      user: { name: ctx.session.user.name, email: ctx.session.user.email },
      csrfToken: ctx.session.csrfToken,
      imageOptimization: Boolean(getSharp()),
    });
  });

  router.post('/api/admin/logout', requireAdmin, (ctx) => {
    destroySession(ctx.db, ctx.session.idHash);
    ctx.res.setHeader('Set-Cookie', clearSessionCookie(ctx.config));
    ctx.log.info('logout', { reqId: ctx.reqId, userId: ctx.session.user.id });
    sendJson(ctx, 200, { ok: true });
  });

  router.post('/api/admin/password', rateLimit(limiters.login, 'password'), requireAdmin, async (ctx) => {
    const body = await readJson(ctx.req, 4096);
    onlyKeys(body, ['currentPassword', 'newPassword'], 'senha');
    const user = ctx.db.prepare('SELECT * FROM admin_users WHERE id = ?').get(ctx.session.user.id);
    const current = typeof body.currentPassword === 'string' ? body.currentPassword : '';
    if (!(await verifyPassword(current, user.password_hash))) throw new HttpError(400, 'Senha atual incorreta.');
    const problem = passwordProblem(body.newPassword, user.email);
    if (problem) throw new HttpError(400, problem);
    ctx.db.prepare('UPDATE admin_users SET password_hash = ? WHERE id = ?').run(await hashPassword(body.newPassword), user.id);
    // encerra todas as sessões (inclusive esta) e abre uma nova
    destroyUserSessions(ctx.db, user.id);
    const s = createSession(ctx.db, user.id, ctx.config);
    ctx.res.setHeader('Set-Cookie', sessionCookie(ctx.config, s.token, s.maxAgeSec));
    audit(ctx, 'password_changed', 'admin_user', user.id);
    sendJson(ctx, 200, { ok: true, csrfToken: s.csrfToken });
  });

  // ---------- pedidos ----------

  router.get('/api/admin/orders', requireAdmin, (ctx) => {
    const scope = ctx.url.searchParams.get('scope') || 'abertos';
    sendJson(ctx, 200, { orders: listOrders(ctx.db, { scope }), serverTime: nowIso() });
  });

  router.get('/api/admin/orders/:id', requireAdmin, (ctx) => {
    sendJson(ctx, 200, getOrderForAdmin(ctx.db, parseId(ctx.params.id)));
  });

  router.patch('/api/admin/orders/:id/status', requireAdmin, async (ctx) => {
    const id = parseId(ctx.params.id);
    const body = await readJson(ctx.req, 1024);
    const order = updateOrderStatus(ctx.db, id, body, ctx.session.user.id);
    audit(ctx, 'order_status', 'order', id, { from: body.fromStatus, to: body.status });
    sendJson(ctx, 200, order);
  });

  // ---------- categorias ----------

  router.get('/api/admin/categories', requireAdmin, (ctx) => sendJson(ctx, 200, { categories: menu.listCategories(ctx.db) }));

  router.post('/api/admin/categories', requireAdmin, async (ctx) => {
    const id = menu.createCategory(ctx.db, await readJson(ctx.req));
    audit(ctx, 'create', 'category', id);
    sendJson(ctx, 201, { id });
  });

  router.put('/api/admin/categories/:id', requireAdmin, async (ctx) => {
    const id = parseId(ctx.params.id);
    menu.updateCategory(ctx.db, id, await readJson(ctx.req));
    audit(ctx, 'update', 'category', id);
    sendJson(ctx, 200, { ok: true });
  });

  router.delete('/api/admin/categories/:id', requireAdmin, (ctx) => {
    const id = parseId(ctx.params.id);
    menu.deleteCategory(ctx.db, id);
    audit(ctx, 'delete', 'category', id);
    sendJson(ctx, 200, { ok: true });
  });

  // ---------- produtos ----------

  router.get('/api/admin/products', requireAdmin, (ctx) =>
    sendJson(ctx, 200, {
      products: menu.listProducts(ctx.db),
      illustrations: illustrationList(),
      tags: tagList(),
      optionGroups: options.listOptionGroups(ctx.db).map((g) => ({ id: g.id, name: g.name, archived: g.archived })),
    })
  );

  router.post('/api/admin/products', requireAdmin, async (ctx) => {
    const id = menu.createProduct(ctx.db, await readJson(ctx.req));
    audit(ctx, 'create', 'product', id);
    sendJson(ctx, 201, { id });
  });

  router.put('/api/admin/products/:id', requireAdmin, async (ctx) => {
    const id = parseId(ctx.params.id);
    const body = await readJson(ctx.req);
    menu.updateProduct(ctx.db, id, body);
    audit(ctx, 'update', 'product', id, { fields: Object.keys(body) });
    sendJson(ctx, 200, { ok: true });
  });

  const uploadsDir = (ctx) => path.join(ctx.config.dataDir, 'uploads', 'products');

  router.put('/api/admin/products/:id/image', requireAdmin, async (ctx) => {
    const id = parseId(ctx.params.id);
    const product = menu.getProduct(ctx.db, id);
    const buf = await readBinary(ctx.req, ctx.config.maxImageBytes);
    const image = await storeProductImage(buf, uploadsDir(ctx));
    menu.setProductImage(ctx.db, id, image);
    removeImageFiles(uploadsDir(ctx), product.image_file, product.image_thumb_file);
    audit(ctx, 'image_upload', 'product', id, { optimized: image.optimized, width: image.width, height: image.height });
    sendJson(ctx, 200, { ok: true, optimized: image.optimized });
  });

  router.delete('/api/admin/products/:id/image', requireAdmin, (ctx) => {
    const id = parseId(ctx.params.id);
    const product = menu.getProduct(ctx.db, id);
    menu.setProductImage(ctx.db, id, null);
    removeImageFiles(uploadsDir(ctx), product.image_file, product.image_thumb_file);
    audit(ctx, 'image_remove', 'product', id);
    sendJson(ctx, 200, { ok: true });
  });

  // ---------- adicionais ----------

  router.get('/api/admin/addons', requireAdmin, (ctx) => sendJson(ctx, 200, { addons: menu.listAddons(ctx.db) }));

  router.post('/api/admin/addons', requireAdmin, async (ctx) => {
    const id = menu.createAddon(ctx.db, await readJson(ctx.req));
    audit(ctx, 'create', 'addon', id);
    sendJson(ctx, 201, { id });
  });

  router.put('/api/admin/addons/:id', requireAdmin, async (ctx) => {
    const id = parseId(ctx.params.id);
    menu.updateAddon(ctx.db, id, await readJson(ctx.req));
    audit(ctx, 'update', 'addon', id);
    sendJson(ctx, 200, { ok: true });
  });

  // ---------- grupos de opções (ponto da carne, pão, retirar ingredientes...) ----------

  router.get('/api/admin/option-groups', requireAdmin, (ctx) => sendJson(ctx, 200, { groups: options.listOptionGroups(ctx.db) }));

  router.post('/api/admin/option-groups', requireAdmin, async (ctx) => {
    const id = options.createOptionGroup(ctx.db, await readJson(ctx.req));
    audit(ctx, 'create', 'option_group', id);
    sendJson(ctx, 201, { id });
  });

  router.put('/api/admin/option-groups/:id', requireAdmin, async (ctx) => {
    const id = parseId(ctx.params.id);
    options.updateOptionGroup(ctx.db, id, await readJson(ctx.req));
    audit(ctx, 'update', 'option_group', id);
    sendJson(ctx, 200, { ok: true });
  });

  router.post('/api/admin/option-groups/:id/choices', requireAdmin, async (ctx) => {
    const groupId = parseId(ctx.params.id);
    const id = options.createOptionChoice(ctx.db, groupId, await readJson(ctx.req));
    audit(ctx, 'create', 'option_choice', id, { groupId });
    sendJson(ctx, 201, { id });
  });

  router.put('/api/admin/option-choices/:id', requireAdmin, async (ctx) => {
    const id = parseId(ctx.params.id);
    options.updateOptionChoice(ctx.db, id, await readJson(ctx.req));
    audit(ctx, 'update', 'option_choice', id);
    sendJson(ctx, 200, { ok: true });
  });

  // ---------- cupons ----------

  router.get('/api/admin/coupons', requireAdmin, (ctx) => sendJson(ctx, 200, { coupons: listCoupons(ctx.db) }));

  router.post('/api/admin/coupons', requireAdmin, async (ctx) => {
    const id = createCoupon(ctx.db, await readJson(ctx.req));
    audit(ctx, 'create', 'coupon', id);
    sendJson(ctx, 201, { id });
  });

  router.put('/api/admin/coupons/:id', requireAdmin, async (ctx) => {
    const id = parseId(ctx.params.id);
    updateCoupon(ctx.db, id, await readJson(ctx.req));
    audit(ctx, 'update', 'coupon', id);
    sendJson(ctx, 200, { ok: true });
  });

  // ---------- configurações ----------

  router.get('/api/admin/settings', requireAdmin, (ctx) => sendJson(ctx, 200, { settings: getSettings(ctx.db) }));

  router.put('/api/admin/settings', requireAdmin, async (ctx) => {
    const body = await readJson(ctx.req);
    const settings = updateSettings(ctx.db, body);
    audit(ctx, 'update', 'settings', null, { fields: Object.keys(body) });
    sendJson(ctx, 200, { settings });
  });
}
