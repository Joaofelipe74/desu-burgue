// Sessões do painel administrativo, guardadas no banco.
// O navegador recebe só um identificador aleatório em cookie HttpOnly;
// no banco fica apenas o hash SHA-256 desse identificador.
import crypto from 'node:crypto';
import { nowIso } from '../db.js';

const sha256 = (v) => crypto.createHash('sha256').update(v).digest('hex');
const randomToken = () => crypto.randomBytes(32).toString('base64url');

export function parseCookies(header = '') {
  const out = {};
  for (const part of String(header).split(';')) {
    const i = part.indexOf('=');
    if (i < 0) continue;
    const k = part.slice(0, i).trim();
    const v = part.slice(i + 1).trim();
    if (k && !(k in out)) out[k] = v;
  }
  return out;
}

export function sessionCookie(config, token, maxAgeSec) {
  const parts = [`${config.sessionCookieName}=${token}`, 'Path=/', 'HttpOnly', 'SameSite=Strict', `Max-Age=${maxAgeSec}`];
  if (config.secureCookies) parts.push('Secure');
  return parts.join('; ');
}

export function clearSessionCookie(config) {
  return sessionCookie(config, '', 0);
}

export function createSession(db, userId, config) {
  const token = randomToken();
  const csrfToken = randomToken();
  const now = new Date();
  const expires = new Date(now.getTime() + config.sessionTtlHours * 3600 * 1000);
  db.prepare(
    `INSERT INTO sessions (id_hash, user_id, csrf_token, created_at, last_seen_at, expires_at)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).run(sha256(token), userId, csrfToken, now.toISOString(), now.toISOString(), expires.toISOString());
  // limpeza de sessões vencidas
  db.prepare('DELETE FROM sessions WHERE expires_at < ?').run(now.toISOString());
  return { token, csrfToken, maxAgeSec: config.sessionTtlHours * 3600 };
}

/** Devolve { session, user } se o cookie for válido; senão null. */
export function loadSession(db, req, config) {
  const token = parseCookies(req.headers.cookie)[config.sessionCookieName];
  if (!token || token.length > 100) return null;
  const idHash = sha256(token);
  const row = db
    .prepare(
      `SELECT s.id_hash, s.csrf_token, s.last_seen_at, s.expires_at,
              u.id AS user_id, u.email, u.name, u.role, u.active
         FROM sessions s JOIN admin_users u ON u.id = s.user_id
        WHERE s.id_hash = ?`
    )
    .get(idHash);
  if (!row) return null;
  const now = Date.now();
  const idleLimit = Date.parse(row.last_seen_at) + config.sessionIdleMinutes * 60 * 1000;
  if (Date.parse(row.expires_at) <= now || idleLimit <= now || row.active !== 1) {
    db.prepare('DELETE FROM sessions WHERE id_hash = ?').run(idHash);
    return null;
  }
  if (now - Date.parse(row.last_seen_at) > 60 * 1000) {
    db.prepare('UPDATE sessions SET last_seen_at = ? WHERE id_hash = ?').run(nowIso(), idHash);
  }
  return {
    idHash,
    csrfToken: row.csrf_token,
    user: { id: row.user_id, email: row.email, name: row.name, role: row.role },
  };
}

export function destroySession(db, idHash) {
  db.prepare('DELETE FROM sessions WHERE id_hash = ?').run(idHash);
}

export function destroyUserSessions(db, userId, exceptIdHash = null) {
  db.prepare('DELETE FROM sessions WHERE user_id = ? AND id_hash IS NOT ?').run(userId, exceptIdHash);
}

/** Comparação de tokens em tempo constante. */
export function safeEqual(a, b) {
  const ba = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  return ba.length === bb.length && crypto.timingSafeEqual(ba, bb);
}
