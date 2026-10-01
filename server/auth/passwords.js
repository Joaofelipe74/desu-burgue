// Armazenamento de senhas com scrypt (módulo crypto do Node/OpenSSL).
// Parâmetros do OWASP Password Storage Cheat Sheet: N=2^17, r=8, p=1.
// Formato salvo: scrypt$N$r$p$salt(base64)$hash(base64) — permite mudar os
// parâmetros (ou migrar para Argon2id) no futuro sem perder as senhas atuais.
import crypto from 'node:crypto';
import { promisify } from 'node:util';

const rawScrypt = promisify(crypto.scrypt);

// Cada cálculo usa ~128 MB de memória. Limitamos a 2 cálculos simultâneos
// (e uma fila curta) para que muitas tentativas de login não derrubem o servidor.
const MAX_CONCURRENT = 2;
const MAX_QUEUE = 20;
let running = 0;
const queue = [];

export class PasswordBusyError extends Error {}

async function scrypt(...args) {
  if (running >= MAX_CONCURRENT) {
    if (queue.length >= MAX_QUEUE) throw new PasswordBusyError('Servidor ocupado.');
    await new Promise((resolve) => queue.push(resolve)); // a vaga é repassada por quem terminar
  } else {
    running++;
  }
  try {
    return await rawScrypt(...args);
  } finally {
    const next = queue.shift();
    if (next) next();
    else running--;
  }
}
const PARAMS = { N: 2 ** 17, r: 8, p: 1 };
const KEY_LEN = 32;
const SALT_LEN = 16;

export const PASSWORD_MIN = 15;
export const PASSWORD_MAX = 128;

// Lista curta de senhas muito comuns (a verificação principal é o tamanho mínimo).
const COMMON = [
  '123456789012345',
  'senhasenhasenha',
  'passwordpassword',
  'desuburguer123456',
  'administrador123',
  'qwertyuiopasdfg',
  'aaaaaaaaaaaaaaa',
];

function maxmemFor({ N, r }) {
  return 128 * N * r * 2; // folga sobre o mínimo exigido pelo scrypt
}

export async function hashPassword(password) {
  const salt = crypto.randomBytes(SALT_LEN);
  const key = await scrypt(password.normalize('NFKC'), salt, KEY_LEN, {
    ...PARAMS,
    maxmem: maxmemFor(PARAMS),
  });
  return ['scrypt', PARAMS.N, PARAMS.r, PARAMS.p, salt.toString('base64'), key.toString('base64')].join('$');
}

export async function verifyPassword(password, stored) {
  const parts = String(stored).split('$');
  if (parts.length !== 6 || parts[0] !== 'scrypt') return false;
  const [, N, r, p, saltB64, keyB64] = parts;
  const params = { N: Number(N), r: Number(r), p: Number(p) };
  const expected = Buffer.from(keyB64, 'base64');
  const key = await scrypt(String(password).normalize('NFKC'), Buffer.from(saltB64, 'base64'), expected.length, {
    ...params,
    maxmem: maxmemFor(params),
  });
  return key.length === expected.length && crypto.timingSafeEqual(key, expected);
}

/** Indica se um hash foi gerado com parâmetros antigos e deve ser refeito no próximo login. */
export function needsRehash(stored) {
  const [alg, N, r, p] = String(stored).split('$');
  return alg !== 'scrypt' || Number(N) !== PARAMS.N || Number(r) !== PARAMS.r || Number(p) !== PARAMS.p;
}

/** Valida a força da senha. Devolve uma mensagem de erro ou null. */
export function passwordProblem(password, email = '') {
  if (typeof password !== 'string') return 'Informe a senha.';
  const len = [...password].length;
  if (len < PASSWORD_MIN) return `A senha precisa ter pelo menos ${PASSWORD_MIN} caracteres (dica: use uma frase).`;
  if (len > PASSWORD_MAX) return `A senha pode ter no máximo ${PASSWORD_MAX} caracteres.`;
  const lower = password.toLowerCase();
  if (COMMON.includes(lower) || /^(.)\1+$/.test(password)) return 'Essa senha é fácil demais de adivinhar.';
  const user = String(email).split('@')[0].toLowerCase();
  if (user.length >= 4 && lower.includes(user)) return 'A senha não pode conter o seu e-mail.';
  return null;
}

// Hash fixo usado quando o e-mail não existe, para que o tempo de resposta
// não revele quais e-mails estão cadastrados.
let dummyHashPromise;
export function dummyHash() {
  dummyHashPromise ??= hashPassword(crypto.randomBytes(24).toString('base64'));
  return dummyHashPromise;
}
