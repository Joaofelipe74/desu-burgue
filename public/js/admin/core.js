// Base do painel: chamadas autenticadas, estado da sessão e componentes de formulário.
import { api, ApiError, h } from '../lib.js';

export const state = {
  csrfToken: null,
  user: null,
  imageOptimization: false,
  onUnauthorized: () => {},
};

/** Chamada à API do painel: envia o token anti-CSRF e trata sessão expirada. */
export async function adminApi(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (state.csrfToken) headers['X-CSRF-Token'] = state.csrfToken;
  try {
    return await api(path, { ...opts, headers });
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) state.onUnauthorized(err.message);
    throw err;
  }
}

let idSeq = 0;
const nextId = (p) => `${p}-${++idSeq}`;

/** Campo com rótulo associado. */
export function field(labelText, input, hint) {
  if (!input.id) input.id = nextId('f');
  return h(
    'div',
    { class: 'field' },
    h('label', { for: input.id }, labelText, hint ? h('span', { class: 'hint', text: ` (${hint})` }) : null),
    input
  );
}

export function checkbox(labelText, checked, props = {}) {
  const input = h('input', { type: 'checkbox', checked: Boolean(checked), ...props });
  return { input, el: h('label', { class: 'switch' }, input, h('span', { text: labelText })) };
}

/** Mostra uma mensagem temporária num elemento de alerta. */
export function flash(el, message, kind = 'error') {
  el.className = `alert alert-${kind}`;
  el.textContent = message;
  if (kind === 'success') setTimeout(() => el.textContent === message && (el.textContent = ''), 4000);
}

/** Executa uma ação de botão com estado de carregamento e tratamento de erro. */
export async function withBusy(button, fn, alertEl) {
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  try {
    return await fn();
  } catch (err) {
    if (alertEl) flash(alertEl, err.message);
    else throw err;
  } finally {
    button.disabled = false;
    button.removeAttribute('aria-busy');
  }
}

export function sectionTitle(text, ...extra) {
  return h('div', { class: 'toolbar' }, h('h2', { text }), h('span', { class: 'spacer' }), ...extra);
}
