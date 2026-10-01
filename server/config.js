// Configuração central. Todos os valores vêm de variáveis de ambiente
// (arquivo .env, fora do controle de versão) com padrões seguros.
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

export const ROOT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/** Carrega o arquivo .env da raiz do projeto, se existir (Node >= 20.12). */
export function loadEnvFile(file = path.join(ROOT_DIR, '.env')) {
  if (fs.existsSync(file)) process.loadEnvFile(file);
}

function intFrom(value, fallback, { min = -Infinity, max = Infinity } = {}) {
  if (value === undefined || value === '') return fallback;
  const n = Number(value);
  if (!Number.isInteger(n) || n < min || n > max) {
    throw new Error(`Valor inválido de configuração: "${value}" (esperado inteiro entre ${min} e ${max}).`);
  }
  return n;
}

/**
 * Monta a configuração a partir de um objeto de ambiente.
 * Lança erro (e o servidor não sobe) se a configuração de produção for insegura.
 */
export function buildConfig(env = process.env, overrides = {}) {
  const nodeEnv = env.NODE_ENV || 'development';
  const isProduction = nodeEnv === 'production';
  const port = intFrom(env.PORT, 3000, { min: 0, max: 65535 });
  const tlsCertFile = env.TLS_CERT_FILE || '';
  const tlsKeyFile = env.TLS_KEY_FILE || '';
  const defaultScheme = tlsCertFile ? 'https' : 'http';

  const publicOrigin = (env.PUBLIC_ORIGIN || `${defaultScheme}://localhost:${port}`).replace(/\/+$/, '');
  let originUrl;
  try {
    originUrl = new URL(publicOrigin);
  } catch {
    throw new Error('PUBLIC_ORIGIN inválida. Exemplo: https://www.seudominio.com.br');
  }

  const config = {
    env: nodeEnv,
    isProduction,
    host: env.HOST || (isProduction ? '0.0.0.0' : '127.0.0.1'),
    port,
    publicOrigin: originUrl.origin,
    // Em desenvolvimento aceitamos localhost e 127.0.0.1 na mesma porta.
    allowedOrigins: new Set([originUrl.origin]),
    dataDir: path.resolve(ROOT_DIR, env.DATA_DIR || 'data'),
    publicDir: path.join(ROOT_DIR, 'public'),
    trustProxyHops: intFrom(env.TRUST_PROXY, 0, { min: 0, max: 5 }),
    tlsCertFile,
    tlsKeyFile,
    sessionTtlHours: intFrom(env.SESSION_TTL_HOURS, 12, { min: 1, max: 72 }),
    sessionIdleMinutes: intFrom(env.SESSION_IDLE_MINUTES, 120, { min: 5, max: 1440 }),
    maxImageBytes: intFrom(env.MAX_IMAGE_MB, 5, { min: 1, max: 20 }) * 1024 * 1024,
    // pedidos por IP a cada 10 minutos (anti-abuso). Atenção a redes móveis que
    // compartilham IP (CGNAT) e a proxies: configure TRUST_PROXY corretamente.
    orderRateLimit: intFrom(env.ORDER_RATE_LIMIT, 20, { min: 1, max: 1000 }),
    logLevel: env.LOG_LEVEL || (nodeEnv === 'test' ? 'silent' : 'info'),
    ...overrides,
  };

  if (!isProduction) {
    for (const h of ['localhost', '127.0.0.1']) {
      config.allowedOrigins.add(`${originUrl.protocol}//${h}:${port}`);
    }
  }

  config.secureCookies = isProduction || originUrl.protocol === 'https:';
  config.sessionCookieName = config.secureCookies ? '__Host-desu_sid' : 'desu_sid';

  if (isProduction) {
    if (originUrl.protocol !== 'https:') {
      throw new Error(
        'Em produção, PUBLIC_ORIGIN precisa usar https:// (ex.: https://www.seudominio.com.br). ' +
          'O painel administrativo depende de cookies seguros que só funcionam com HTTPS.'
      );
    }
    if (!env.PUBLIC_ORIGIN) {
      throw new Error('Em produção, defina PUBLIC_ORIGIN no arquivo .env.');
    }
  }
  if ((tlsCertFile && !tlsKeyFile) || (!tlsCertFile && tlsKeyFile)) {
    throw new Error('Defina TLS_CERT_FILE e TLS_KEY_FILE juntos (ou nenhum dos dois).');
  }
  return config;
}
