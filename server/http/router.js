// Roteador mínimo: associa método + caminho (com parâmetros ":id") a uma função.
import { HttpError } from './errors.js';

export function createRouter() {
  const routes = [];

  function add(method, pattern, ...handlers) {
    const parts = pattern.split('/').filter(Boolean);
    routes.push({ method, parts, handlers });
  }

  function match(method, pathname) {
    const segs = pathname.split('/').filter(Boolean);
    let pathMatched = false;
    for (const r of routes) {
      if (r.parts.length !== segs.length) continue;
      const params = {};
      let ok = true;
      for (let i = 0; i < r.parts.length; i++) {
        const p = r.parts[i];
        if (p.startsWith(':')) params[p.slice(1)] = segs[i];
        else if (p !== segs[i]) {
          ok = false;
          break;
        }
      }
      if (!ok) continue;
      pathMatched = true;
      if (r.method === method || (method === 'HEAD' && r.method === 'GET')) {
        return { handlers: r.handlers, params };
      }
    }
    return pathMatched ? { methodNotAllowed: true } : null;
  }

  return {
    get: (p, ...h) => add('GET', p, ...h),
    post: (p, ...h) => add('POST', p, ...h),
    put: (p, ...h) => add('PUT', p, ...h),
    patch: (p, ...h) => add('PATCH', p, ...h),
    delete: (p, ...h) => add('DELETE', p, ...h),
    /** Executa a rota; devolve false se nenhuma rota corresponde ao caminho. */
    async handle(ctx) {
      const found = match(ctx.req.method, ctx.pathname);
      if (!found) return false;
      if (found.methodNotAllowed) throw new HttpError(405, 'Método não permitido.');
      ctx.params = found.params;
      for (const h of found.handlers) {
        const done = await h(ctx);
        if (done === true || ctx.res.writableEnded) break;
      }
      return true;
    },
  };
}

/** Converte um parâmetro de rota em ID inteiro positivo, ou responde 404. */
export function parseId(value) {
  if (!/^[1-9][0-9]{0,9}$/.test(String(value))) throw new HttpError(404, 'Não encontrado.');
  return Number(value);
}
