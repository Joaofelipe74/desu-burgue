// Imagens dos produtos: validação pelo conteúdo do arquivo (não pelo nome),
// nome aleatório, e otimização automática quando o pacote opcional "sharp" está instalado.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { HttpError } from '../http/errors.js';

let sharpLib;
export function getSharp() {
  if (sharpLib === undefined) {
    try {
      sharpLib = createRequire(import.meta.url)('sharp');
    } catch {
      sharpLib = null;
    }
  }
  return sharpLib;
}

export const MAX_UNOPTIMIZED_BYTES = 3 * 1024 * 1024;
const MAX_DIMENSION = 6000;

/** Identifica JPG, PNG ou WebP pelos primeiros bytes e lê largura/altura. */
export function sniffImage(buf) {
  if (buf.length < 32) return null;
  // PNG
  if (buf.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
    if (buf.toString('ascii', 12, 16) !== 'IHDR') return null;
    return { type: 'png', ext: '.png', width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  }
  // JPEG
  if (buf[0] === 0xff && buf[1] === 0xd8 && buf[2] === 0xff) {
    let i = 2;
    while (i + 9 < buf.length) {
      if (buf[i] !== 0xff) return null;
      const marker = buf[i + 1];
      if (marker === 0xff) {
        i += 1;
        continue;
      }
      const len = buf.readUInt16BE(i + 2);
      const isSof = marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker);
      if (isSof) {
        return { type: 'jpeg', ext: '.jpg', height: buf.readUInt16BE(i + 5), width: buf.readUInt16BE(i + 7) };
      }
      if (len < 2) return null;
      i += 2 + len;
    }
    return null;
  }
  // WebP
  if (buf.toString('ascii', 0, 4) === 'RIFF' && buf.toString('ascii', 8, 12) === 'WEBP') {
    const chunk = buf.toString('ascii', 12, 16);
    if (chunk === 'VP8X') {
      return { type: 'webp', ext: '.webp', width: 1 + buf.readUIntLE(24, 3), height: 1 + buf.readUIntLE(27, 3) };
    }
    if (chunk === 'VP8L' && buf[20] === 0x2f) {
      const b = buf.readUInt32LE(21);
      return { type: 'webp', ext: '.webp', width: (b & 0x3fff) + 1, height: ((b >> 14) & 0x3fff) + 1 };
    }
    if (chunk === 'VP8 ' && buf[23] === 0x9d && buf[24] === 0x01 && buf[25] === 0x2a) {
      return { type: 'webp', ext: '.webp', width: buf.readUInt16LE(26) & 0x3fff, height: buf.readUInt16LE(28) & 0x3fff };
    }
    return null;
  }
  return null;
}

const randomName = (ext) => `${crypto.randomBytes(16).toString('hex')}${ext}`;

/**
 * Valida e grava uma imagem enviada. Devolve { file, thumbFile, width, height, optimized }.
 * Recusa qualquer coisa que não seja JPG/PNG/WebP de verdade (ex.: SVG, HTML, executáveis).
 */
export async function storeProductImage(buf, uploadsDir) {
  const info = sniffImage(buf);
  if (!info) throw new HttpError(415, 'Formato não aceito. Envie uma imagem JPG, PNG ou WebP.');
  if (!info.width || !info.height || info.width > MAX_DIMENSION || info.height > MAX_DIMENSION) {
    throw new HttpError(422, `A imagem deve ter no máximo ${MAX_DIMENSION} × ${MAX_DIMENSION} pixels.`);
  }
  fs.mkdirSync(uploadsDir, { recursive: true });
  const sharp = getSharp();

  if (!sharp) {
    if (buf.length > MAX_UNOPTIMIZED_BYTES) {
      throw new HttpError(
        413,
        'Imagem acima de 3 MB. Reduza o arquivo ou instale a otimização automática (npm install) e tente de novo.'
      );
    }
    const file = randomName(info.ext);
    fs.writeFileSync(path.join(uploadsDir, file), buf, { flag: 'wx' });
    return { file, thumbFile: null, width: info.width, height: info.height, optimized: false };
  }

  // Com sharp: decodifica e recodifica (remove metadados como GPS e neutraliza
  // arquivos "disfarçados"), corrige a rotação e mantém a proporção original.
  let main;
  let thumb;
  try {
    const base = sharp(buf, { limitInputPixels: MAX_DIMENSION * MAX_DIMENSION, failOn: 'error' }).rotate();
    const meta = await base.metadata();
    if (!['jpeg', 'png', 'webp'].includes(meta.format)) throw new Error('formato');
    main = await base
      .clone()
      .resize({ width: 1200, height: 1200, fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 82 })
      .toBuffer({ resolveWithObject: true });
    thumb = await base
      .clone()
      .resize({ width: 600, height: 600, fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 78 })
      .toBuffer({ resolveWithObject: true });
  } catch {
    throw new HttpError(415, 'Não foi possível ler esta imagem. Envie um JPG, PNG ou WebP válido.');
  }
  const file = randomName('.webp');
  const thumbFile = randomName('.webp');
  fs.writeFileSync(path.join(uploadsDir, file), main.data, { flag: 'wx' });
  fs.writeFileSync(path.join(uploadsDir, thumbFile), thumb.data, { flag: 'wx' });
  return { file, thumbFile, width: main.info.width, height: main.info.height, optimized: true };
}

/** Apaga arquivos antigos de imagem (ignora se já não existirem). */
export function removeImageFiles(uploadsDir, ...files) {
  for (const f of files) {
    if (!f || !/^[a-f0-9]{32}\.(webp|png|jpg)$/.test(f)) continue;
    try {
      fs.unlinkSync(path.join(uploadsDir, f));
    } catch {
      /* já removido */
    }
  }
}
