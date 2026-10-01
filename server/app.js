// Monta a aplicação: segurança comum a todas as respostas, API e arquivos estáticos.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { PasswordBusyError } from './auth/passwords.js';
import { HttpError } from './http/errors.js';
import { createRouter } from './http/router.js';
import { assertSameOrigin, clientIp, createRateLimiter, securityHeaders } from './http/security.js';
import { serveStatic } from './http/static.js';
import { registerAdminRoutes } from './routes/admin.js';
import { registerPublicRoutes } from './routes/public.js';

function sendJson(ctx, status, data) {
  const body = JSON.stringify(data);
  ctx.res.statusCode = status;
  ctx.res.setHeader('Content-Type', 'application/json; charset=utf-8');
  ctx.res.setHeader('Content-Length', Buffer.byteLength(body));
  ctx.res.end(ctx.req.method === 'HEAD' ? undefined : body);
}

export function createApp({ config, db, log }) {
  const limiters = {
    api: createRateLimiter({ windowMs: 60_000, max: 300 }),
    quote: createRateLimiter({ windowMs: 60_000, max: 60 }),
    order: createRateLimiter({ windowMs: 10 * 60_000, max: config.orderRateLimit }),
    track: createRateLimiter({ windowMs: 60_000, max: 60 }),
    login: createRateLimiter({ windowMs: 15 * 60_000, max: 10 }),
    loginEmail: createRateLimiter({ windowMs: 15 * 60_000, max: 5 }),
    ...(config.limiters || {}),
  };
  const router = createRouter();
  registerPublicRoutes(router, { limiters, sendJson });
  registerAdminRoutes(router, { limiters, sendJson });

  const headers = securityHeaders(config);
  const uploadsRoot = path.join(config.dataDir, 'uploads', 'products');
  const notFoundPage = path.join(config.publicDir, '404.html');

  return async function handler(req, res) {
    const started = process.hrtime.bigint();
    const reqId = crypto.randomBytes(6).toString('hex');
    for (const [k, v] of Object.entries(headers)) res.setHeader(k, v);
    res.setHeader('X-Request-Id', reqId);

    let url;
    try {
      url = new URL(req.url, 'http://localhost');
    } catch {
      res.statusCode = 400;
      res.end();
      return;
    }
    const ctx = {
      req,
      res,
      url,
      pathname: url.pathname,
      reqId,
      ip: clientIp(req, config.trustProxyHops),
      config,
      db,
      log,
      params: {},
      session: null,
    };

    res.on('finish', () => {
      const ms = Number(process.hrtime.bigint() - started) / 1e6;
      if (ctx.pathname.startsWith('/api/') || res.statusCode >= 400) {
        log.info('http', { reqId, method: req.method, path: ctx.pathname, status: res.statusCode, ms: Math.round(ms) });
      }
    });

    try {
      if (ctx.pathname.startsWith('/api/')) {
        const general = limiters.api.hit(`api:${ctx.ip}`);
        if (!general.allowed) {
          res.setHeader('Retry-After', String(general.retryAfterSec));
          throw new HttpError(429, 'Muitas requisições. Aguarde um pouco.');
        }
        assertSameOrigin(req, config);
        const handled = await router.handle(ctx);
        if (!handled) throw new HttpError(404, 'Endereço da API não encontrado.');
        return;
      }

      if (req.method !== 'GET' && req.method !== 'HEAD') throw new HttpError(405, 'Método não permitido.');

      if (ctx.pathname.startsWith('/uploads/products/')) {
        const rel = ctx.pathname.slice('/uploads/products/'.length);
        if (serveStatic(req, res, uploadsRoot, `/${rel}`, { immutable: true })) return;
      } else if (serveStatic(req, res, config.publicDir, ctx.pathname, { isProduction: config.isProduction })) {
        return;
      }

      res.statusCode = 404;
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader('Cache-Control', 'no-cache');
      if (req.method === 'HEAD') {
        res.end();
        return;
      }
      fs.createReadStream(notFoundPage)
        .on('error', () => res.end('Página não encontrada.'))
        .pipe(res);
    } catch (err) {
      if (res.headersSent) {
        res.destroy();
        return;
      }
      let status = 500;
      let payload;
      if (err instanceof HttpError) {
        status = err.status;
        payload = { error: err.publicMessage, ...err.extra };
        if (status === 403 && err.extra?.reason) {
          log.warn('origin_rejected', { reqId, reason: err.extra.reason, path: ctx.pathname });
          delete payload.reason;
        }
      } else if (err instanceof PasswordBusyError) {
        status = 503;
        payload = { error: 'Servidor ocupado. Tente novamente em instantes.' };
      } else {
        log.error('unhandled_error', { reqId, path: ctx.pathname, error: err });
        payload = { error: 'Ocorreu um erro inesperado. Tente novamente.', requestId: reqId };
      }
      if (ctx.pathname.startsWith('/api/')) {
        sendJson(ctx, status, payload);
      } else {
        res.statusCode = status;
        res.setHeader('Content-Type', 'text/plain; charset=utf-8');
        res.end(payload.error);
      }
    }
  };
}
