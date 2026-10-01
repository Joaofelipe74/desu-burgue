// Cabeçalhos de segurança, verificação de origem e limitação de tentativas.
import { HttpError } from './errors.js';

/**
 * Política de segurança de conteúdo (CSP): só permite scripts, estilos e imagens
 * do próprio site. Nada de scripts inline — reduz muito o impacto de XSS.
 */
export function securityHeaders(config) {
  const csp = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "manifest-src 'self'",
  ];
  if (config.secureCookies) csp.push('upgrade-insecure-requests');
  const headers = {
    'Content-Security-Policy': csp.join('; '),
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'same-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Resource-Policy': 'same-origin',
  };
  if (config.secureCookies) {
    headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains';
  }
  return headers;
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

/**
 * Bloqueia requisições que alteram dados vindas de outro site
 * (Fetch Metadata + verificação do cabeçalho Origin).
 */
export function assertSameOrigin(req, config) {
  if (SAFE_METHODS.has(req.method)) return;
  const site = req.headers['sec-fetch-site'];
  if (site && site !== 'same-origin') {
    throw new HttpError(403, 'Requisição bloqueada: origem não permitida.', { reason: 'fetch-site' });
  }
  const origin = req.headers.origin;
  if (origin && !config.allowedOrigins.has(origin)) {
    throw new HttpError(403, 'Requisição bloqueada: origem não permitida.', { reason: 'origin' });
  }
}

/** Descobre o IP do cliente, confiando em X-Forwarded-For só se configurado. */
export function clientIp(req, trustProxyHops) {
  const direct = req.socket?.remoteAddress || 'desconhecido';
  if (!trustProxyHops) return direct;
  const chain = String(req.headers['x-forwarded-for'] || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  if (chain.length < trustProxyHops) return direct;
  return chain[chain.length - trustProxyHops] || direct;
}

/** Limitador simples por janela de tempo (memória do processo). */
export function createRateLimiter({ windowMs, max }) {
  const hits = new Map();
  let lastSweep = Date.now();
  return {
    hit(key) {
      const now = Date.now();
      if (now - lastSweep > windowMs) {
        for (const [k, v] of hits) if (v.resetAt <= now) hits.delete(k);
        lastSweep = now;
      }
      let entry = hits.get(key);
      if (!entry || entry.resetAt <= now) {
        entry = { count: 0, resetAt: now + windowMs };
        hits.set(key, entry);
      }
      entry.count += 1;
      return {
        allowed: entry.count <= max,
        retryAfterSec: Math.max(1, Math.ceil((entry.resetAt - now) / 1000)),
      };
    },
    reset(key) {
      hits.delete(key);
    },
  };
}

/** Middleware de rota que aplica um limitador por IP. */
export function rateLimit(limiter, name) {
  return (ctx) => {
    const result = limiter.hit(`${name}:${ctx.ip}`);
    if (!result.allowed) {
      ctx.res.setHeader('Retry-After', String(result.retryAfterSec));
      ctx.log.warn('rate_limited', { reqId: ctx.reqId, limiter: name, ip: ctx.ip, path: ctx.pathname });
      throw new HttpError(429, 'Muitas tentativas. Aguarde um pouco e tente novamente.');
    }
  };
}
