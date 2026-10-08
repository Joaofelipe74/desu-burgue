// Entrega de arquivos estáticos (HTML, CSS, JS, imagens) com proteção
// contra acesso a arquivos fora das pastas permitidas.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

/** Tipos de texto que vale a pena compactar (as ilustrações SVG ficam ~5x menores). */
const COMPRESSIBLE = new Set(['.html', '.css', '.js', '.svg', '.txt', '.webmanifest']);
const GZIP_MAX_BYTES = 1024 * 1024;
const GZIP_CACHE_MAX = 200;
/** Cache em memória das versões compactadas: caminho → { etag, data }. */
const gzipCache = new Map();

function acceptsGzip(req) {
  const ae = String(req.headers['accept-encoding'] || '').slice(0, 256);
  return ae.split(',').some((part) => {
    const [name, ...params] = part.trim().toLowerCase().split(';');
    if (name.trim() !== 'gzip') return false;
    const q = params.map((p) => p.trim()).find((p) => p.startsWith('q='));
    return !q || Number(q.slice(2)) > 0;
  });
}

function gzipped(file, etag) {
  const hit = gzipCache.get(file);
  if (hit && hit.etag === etag) return hit.data;
  const data = zlib.gzipSync(fs.readFileSync(file), { level: 9 });
  if (gzipCache.size >= GZIP_CACHE_MAX) gzipCache.delete(gzipCache.keys().next().value);
  gzipCache.set(file, { etag, data });
  return data;
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
};

/**
 * Resolve um caminho de URL dentro de `root`. Devolve null se o caminho for
 * inválido, tentar sair da pasta (..), apontar para arquivo oculto ou tiver
 * extensão não permitida.
 */
export function resolveSafePath(root, urlPath) {
  let decoded;
  try {
    decoded = decodeURIComponent(urlPath);
  } catch {
    return null;
  }
  if (decoded.includes('\0') || decoded.includes('\\')) return null;
  const segments = decoded.split('/').filter(Boolean);
  if (segments.some((s) => s.startsWith('.'))) return null; // bloqueia "..", ".env", ".git"
  const full = path.resolve(root, ...segments);
  const rootResolved = path.resolve(root);
  if (full !== rootResolved && !full.startsWith(rootResolved + path.sep)) return null;
  return full;
}

/**
 * Tenta servir `urlPath` a partir de `root`. Devolve true se respondeu.
 * `immutable`: arquivos com nome aleatório (uploads) podem ficar em cache por 1 ano.
 */
export function serveStatic(
  req,
  res,
  root,
  urlPath,
  { immutable = false, isProduction = false, mountPrefix = '' } = {}
) {
  if (req.method !== 'GET' && req.method !== 'HEAD') return false;
  let file = resolveSafePath(root, urlPath);
  if (!file) return false;

  let stat;
  try {
    stat = fs.statSync(file);
    if (stat.isDirectory()) {
      if (!urlPath.endsWith('/')) {
        // Redireciona para o caminho normalizado (evita "//host" virar outro domínio).
        const rel = path.relative(path.resolve(root), file).split(path.sep).map(encodeURIComponent);
        res.writeHead(301, { Location: `${mountPrefix}/${rel.join('/')}/`.replace(/\/{2,}/g, '/') });
        res.end();
        return true;
      }
      file = path.join(file, 'index.html');
      stat = fs.statSync(file);
    }
  } catch {
    return false;
  }
  if (!stat.isFile()) return false;

  const ext = path.extname(file).toLowerCase();
  const type = MIME[ext];
  if (!type) return false;

  const compressible = COMPRESSIBLE.has(ext) && stat.size <= GZIP_MAX_BYTES;
  const useGzip = compressible && acceptsGzip(req);
  const baseTag = `${stat.size.toString(16)}-${Math.floor(stat.mtimeMs).toString(16)}`;
  const etag = `W/"${baseTag}${useGzip ? '-gz' : ''}"`;
  let cache = 'no-cache';
  if (immutable) cache = 'public, max-age=31536000, immutable';
  else if (isProduction && ext !== '.html') cache = 'public, max-age=3600, must-revalidate';

  res.setHeader('Content-Type', type);
  res.setHeader('Cache-Control', cache);
  res.setHeader('ETag', etag);
  res.setHeader('Last-Modified', stat.mtime.toUTCString());
  if (compressible) res.setHeader('Vary', 'Accept-Encoding');

  if (req.headers['if-none-match'] === etag) {
    res.statusCode = 304;
    res.end();
    return true;
  }

  if (useGzip) {
    let data;
    try {
      data = gzipped(file, etag);
    } catch {
      return false;
    }
    res.setHeader('Content-Encoding', 'gzip');
    res.setHeader('Content-Length', data.length);
    res.statusCode = 200;
    res.end(req.method === 'HEAD' ? undefined : data);
    return true;
  }

  res.setHeader('Content-Length', stat.size);
  res.statusCode = 200;
  if (req.method === 'HEAD') {
    res.end();
    return true;
  }
  const stream = fs.createReadStream(file);
  stream.on('error', () => res.destroy());
  stream.pipe(res);
  return true;
}
