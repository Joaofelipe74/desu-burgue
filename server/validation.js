// Validação de entrada: todo dado vindo do navegador é tratado como não confiável.
import { badRequest } from './http/errors.js';

// Remove caracteres de controle (exceto quebra de linha quando permitida).
const CONTROL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F​-‏‪-‮⁦-⁩]/g;

/** Rejeita campos desconhecidos — por exemplo um "price" enviado pelo navegador. */
export function onlyKeys(obj, allowed, where = 'dados') {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    throw badRequest(`Formato inválido em ${where}.`);
  }
  for (const key of Object.keys(obj)) {
    if (!allowed.includes(key)) throw badRequest(`Campo não permitido em ${where}: "${key.slice(0, 40)}".`);
  }
  return obj;
}

export function text(value, { field, min = 0, max, required = false, multiline = false, pattern, patternMsg }) {
  if (value === undefined || value === null || value === '') {
    if (required || min > 0) throw badRequest(`Informe ${field}.`);
    return '';
  }
  if (typeof value !== 'string') throw badRequest(`${cap(field)} deve ser um texto.`);
  let v = value.normalize('NFC').replace(CONTROL, '');
  v = multiline ? v.replace(/\r\n?/g, '\n').replace(/\n{3,}/g, '\n\n').trim() : v.replace(/\s+/g, ' ').trim();
  const len = [...v].length;
  if (len < min) throw badRequest(min <= 1 ? `Informe ${field}.` : `${cap(field)} precisa ter pelo menos ${min} caracteres.`);
  if (max && len > max) throw badRequest(`${cap(field)} pode ter no máximo ${max} caracteres.`);
  if (pattern && v && !pattern.test(v)) throw badRequest(patternMsg || `${cap(field)} inválido.`);
  return v;
}

export function integer(value, { field, min = 0, max = Number.MAX_SAFE_INTEGER, required = true }) {
  if (value === undefined || value === null || value === '') {
    if (required) throw badRequest(`Informe ${field}.`);
    return null;
  }
  if (typeof value !== 'number' || !Number.isInteger(value)) throw badRequest(`${cap(field)} deve ser um número inteiro.`);
  if (value < min || value > max) throw badRequest(`${cap(field)} deve estar entre ${min} e ${max}.`);
  return value;
}

export function boolean(value, { field, required = true }) {
  if (value === undefined) {
    if (required) throw badRequest(`Informe ${field}.`);
    return undefined;
  }
  if (typeof value !== 'boolean') throw badRequest(`${cap(field)} deve ser verdadeiro ou falso.`);
  return value;
}

export function oneOf(value, options, { field }) {
  if (!options.includes(value)) throw badRequest(`${cap(field)} inválido.`);
  return value;
}

export function idList(value, { field, max = 50 }) {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value)) throw badRequest(`${cap(field)} deve ser uma lista.`);
  if (value.length > max) throw badRequest(`${cap(field)}: no máximo ${max} itens.`);
  const ids = value.map((v) => integer(v, { field, min: 1, max: 2 ** 31 }));
  if (new Set(ids).size !== ids.length) throw badRequest(`${cap(field)}: itens repetidos.`);
  return ids;
}

/** Telefone brasileiro: aceita formatação, guarda só dígitos (DDD + número). */
export function phoneBR(value) {
  const raw = text(value, { field: 'o telefone', min: 1, max: 25 });
  const digits = raw.replace(/\D/g, '').replace(/^55(?=\d{10,11}$)/, '');
  if (!/^[1-9]{2}9?\d{8}$/.test(digits)) {
    throw badRequest('Telefone inválido. Use DDD + número, por exemplo (11) 91234-5678.');
  }
  return digits;
}

export function cap(s) {
  const t = String(s).replace(/^(o|a|os|as) /, '');
  return t.charAt(0).toUpperCase() + t.slice(1);
}
