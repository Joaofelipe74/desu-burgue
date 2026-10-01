// Registro de eventos em JSON (uma linha por evento).
// Regra: nunca registrar senhas, tokens, cookies, telefones ou endereços.
const LEVELS = { debug: 10, info: 20, warn: 30, error: 40, silent: 100 };
const FORBIDDEN_KEYS = /pass|senha|token|cookie|secret|phone|telefone|address|endereco|authorization/i;

function scrub(value, depth = 0) {
  if (value === null || typeof value !== 'object' || depth > 3) return value;
  if (value instanceof Error) {
    return { name: value.name, message: value.message, stack: value.stack };
  }
  const out = Array.isArray(value) ? [] : {};
  for (const [k, v] of Object.entries(value)) {
    out[k] = FORBIDDEN_KEYS.test(k) ? '[omitido]' : scrub(v, depth + 1);
  }
  return out;
}

/** Mascara um e-mail para log: "joao@exemplo.com" -> "jo***@exemplo.com". */
export function maskEmail(email) {
  if (typeof email !== 'string' || !email.includes('@')) return '[inválido]';
  const [user, domain] = email.split('@');
  return `${user.slice(0, 2)}***@${domain.slice(0, 60)}`;
}

export function createLogger(level = 'info', sink = (line) => process.stdout.write(line + '\n')) {
  const min = LEVELS[level] ?? LEVELS.info;
  const write = (lvl, event, data) => {
    if (LEVELS[lvl] < min) return;
    const entry = { t: new Date().toISOString(), level: lvl, event, ...scrub(data || {}) };
    try {
      sink(JSON.stringify(entry));
    } catch {
      /* o log nunca deve derrubar a aplicação */
    }
  };
  return {
    debug: (e, d) => write('debug', e, d),
    info: (e, d) => write('info', e, d),
    warn: (e, d) => write('warn', e, d),
    error: (e, d) => write('error', e, d),
  };
}
