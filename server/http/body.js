// Leitura do corpo das requisições com limite de tamanho e tipo de conteúdo.
import { HttpError } from './errors.js';

function readRaw(req, limitBytes) {
  return new Promise((resolve, reject) => {
    const declared = Number(req.headers['content-length']);
    if (Number.isFinite(declared) && declared > limitBytes) {
      reject(new HttpError(413, 'Conteúdo grande demais.'));
      req.resume();
      return;
    }
    const chunks = [];
    let size = 0;
    let failed = false;
    req.on('data', (chunk) => {
      if (failed) return;
      size += chunk.length;
      if (size > limitBytes) {
        failed = true;
        reject(new HttpError(413, 'Conteúdo grande demais.'));
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (!failed) resolve(Buffer.concat(chunks));
    });
    req.on('error', (err) => {
      if (!failed) {
        failed = true;
        reject(err);
      }
    });
  });
}

function mediaType(req) {
  return String(req.headers['content-type'] || '')
    .split(';')[0]
    .trim()
    .toLowerCase();
}

/** Lê JSON (exige Content-Type: application/json, máximo 32 KB por padrão). */
export async function readJson(req, limitBytes = 32 * 1024) {
  if (mediaType(req) !== 'application/json') {
    throw new HttpError(415, 'Envie os dados em formato JSON.');
  }
  const raw = await readRaw(req, limitBytes);
  if (raw.length === 0) return {};
  try {
    const value = JSON.parse(raw.toString('utf8'));
    if (value === null || typeof value !== 'object' || Array.isArray(value)) {
      throw new Error('not an object');
    }
    return value;
  } catch {
    throw new HttpError(400, 'Dados inválidos (JSON malformado).');
  }
}

/** Lê um arquivo binário enviado diretamente no corpo (usado no upload de imagens). */
export async function readBinary(req, limitBytes) {
  const type = mediaType(req);
  if (!type.startsWith('image/')) {
    throw new HttpError(415, 'Envie uma imagem JPG, PNG ou WebP.');
  }
  return readRaw(req, limitBytes);
}
