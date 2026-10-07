// Rotas públicas (clientes): cardápio, orçamento, criação e acompanhamento de pedidos.
import { readJson } from '../http/body.js';
import { rateLimit } from '../http/security.js';
import { getPublicMenu, popularProductIds } from '../services/menu.js';
import { createOrder, quote, trackOrder } from '../services/orders.js';
import { getSettings, publicSettings } from '../services/settings.js';

export function registerPublicRoutes(router, { limiters, sendJson }) {
  router.get('/api/health', (ctx) => sendJson(ctx, 200, { ok: true }));

  router.get('/api/menu', (ctx) => {
    ctx.res.setHeader('Cache-Control', 'no-cache');
    sendJson(ctx, 200, {
      store: publicSettings(getSettings(ctx.db)),
      categories: getPublicMenu(ctx.db),
      popularProductIds: popularProductIds(ctx.db),
    });
  });

  router.post('/api/orders/quote', rateLimit(limiters.quote, 'quote'), async (ctx) => {
    const body = await readJson(ctx.req);
    sendJson(ctx, 200, quote(ctx.db, body));
  });

  router.post('/api/orders', rateLimit(limiters.order, 'order'), async (ctx) => {
    const body = await readJson(ctx.req);
    const { replayed, order } = createOrder(ctx.db, body, { log: ctx.log });
    ctx.res.setHeader('Cache-Control', 'no-store');
    sendJson(ctx, replayed ? 200 : 201, { ...order, replayed });
  });

  router.post('/api/orders/track', rateLimit(limiters.track, 'track'), async (ctx) => {
    const body = await readJson(ctx.req, 1024);
    ctx.res.setHeader('Cache-Control', 'no-store');
    sendJson(ctx, 200, trackOrder(ctx.db, body));
  });
}
