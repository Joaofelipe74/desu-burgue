// Funções compartilhadas pelas páginas.
// Regra de segurança: textos vindos do servidor SEMPRE entram na página via
// textContent (nunca innerHTML), evitando XSS.

const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
export const money = (cents) => brl.format((Number(cents) || 0) / 100);

const dateTime = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Sao_Paulo',
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
});
const timeOnly = new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit' });
export const formatDateTime = (iso) => (iso ? dateTime.format(new Date(iso)) : '');
export const formatTime = (iso) => (iso ? timeOnly.format(new Date(iso)) : '');

/** Cria elementos de forma segura: h('p', { class: 'x' }, 'texto', filho) */
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key === 'text') el.textContent = value;
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key in el && typeof value !== 'string') el[key] = value;
    else el.setAttribute(key, value === true ? '' : String(value));
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

const ICONS = {
  cart: 'M3 4h2l2.4 10.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 1.9-1.5L21 8H6.2M10 20a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm9 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z',
  plus: 'M12 5v14M5 12h14',
  minus: 'M5 12h14',
  close: 'M6 6l12 12M18 6 6 18',
  trash: 'M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3',
  back: 'M15 18l-6-6 6-6',
  heart: 'M12 20.5s-7.5-4.6-9.6-9.2A5.2 5.2 0 0 1 12 6.4a5.2 5.2 0 0 1 9.6 4.9C19.5 15.9 12 20.5 12 20.5Z',
  search: 'M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14Zm9 3-4.3-4.3',
};

export function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('class', 'icon');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '2');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', ICONS[name] || '');
  svg.append(path);
  return svg;
}

/** Erro de API com mensagem pronta para mostrar ao usuário. */
export class ApiError extends Error {
  constructor(status, data) {
    super(data?.error || 'Erro inesperado.');
    this.status = status;
    this.data = data || {};
  }
}

/**
 * Chamada à API com tempo limite e mensagens claras.
 * opts: { method, body (objeto → JSON), raw (Blob/File), headers, timeoutMs }
 */
export async function api(path, opts = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs || 15000);
  const headers = { Accept: 'application/json', ...(opts.headers || {}) };
  let body;
  if (opts.raw) {
    body = opts.raw;
    headers['Content-Type'] = opts.raw.type || 'application/octet-stream';
  } else if (opts.body !== undefined) {
    body = JSON.stringify(opts.body);
    headers['Content-Type'] = 'application/json';
  }
  let res;
  try {
    res = await fetch(path, {
      method: opts.method || (body ? 'POST' : 'GET'),
      headers,
      body,
      credentials: 'same-origin',
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, { error: 'Sem conexão com o servidor. Verifique sua internet e tente novamente.' });
  } finally {
    clearTimeout(timer);
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const fallback =
      res.status === 429
        ? 'Muitas tentativas. Aguarde um pouco e tente novamente.'
        : res.status >= 500
          ? 'O servidor teve um problema. Tente novamente em instantes.'
          : 'Não foi possível concluir a ação.';
    throw new ApiError(res.status, data?.error ? data : { ...(data || {}), error: fallback });
  }
  return data;
}

/** Armazenamento local que nunca quebra a página (modo anônimo, bloqueios etc.). */
export const storage = {
  get(key, fallback = null) {
    try {
      const v = localStorage.getItem(key);
      return v === null ? fallback : JSON.parse(v);
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch {
      /* ignora */
    }
  },
};

let toastTimer;
export function toast(message) {
  let el = document.getElementById('toast');
  if (!el) {
    el = h('div', { id: 'toast', class: 'toast', role: 'status', 'aria-live': 'polite' });
    document.body.append(el);
  }
  el.textContent = message;
  el.classList.add('is-visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('is-visible'), 3200);
}

/** Imagem do produto com tratamento para arquivo ausente/quebrado. */
export function productImage(product, { sizes = '(max-width: 600px) 100vw, 360px', eager = false } = {}) {
  const wrap = h('div', { class: 'product-media' });
  const placeholder = () =>
    h(
      'div',
      { class: 'image-placeholder' },
      h('img', { src: '/img/placeholder-produto.svg', alt: '', width: 72, height: 72 }),
      h('span', { text: 'Foto em breve' })
    );
  const img = product.image;
  if (!img) {
    wrap.append(placeholder());
    return wrap;
  }
  const el = h('img', {
    src: img.thumbSrc || img.src,
    alt: img.alt || product.name,
    width: img.width || undefined,
    height: img.height || undefined,
    loading: eager ? 'eager' : 'lazy',
    decoding: 'async',
  });
  if (img.thumbSrc) {
    el.srcset = `${img.thumbSrc} 600w, ${img.src} 1200w`;
    el.sizes = sizes;
  }
  el.addEventListener('error', () => {
    el.replaceWith(placeholder());
    wrap.querySelector('.illustrative-tag')?.remove();
  });
  wrap.append(el);
  if (img.illustrative) wrap.append(h('span', { class: 'illustrative-tag', text: 'Imagem ilustrativa' }));
  return wrap;
}

/** Texto das opções escolhidas: "Ao ponto · Brioche · Sem cebola". */
export function optionsText(options = []) {
  return options.map((o) => o.name).join(' · ');
}

/** Converte "24,90" / "24.90" / "24" em centavos (2490). Devolve null se inválido. */
export function parseMoneyToCents(value) {
  const v = String(value ?? '')
    .trim()
    .replace(/^R\$\s*/i, '');
  if (!/^\d{1,7}([.,]\d{1,2})?$/.test(v)) return null;
  const [int, dec = ''] = v.split(/[.,]/);
  return Number(int) * 100 + Number((dec + '00').slice(0, 2));
}

export const centsToInput = (cents) => ((Number(cents) || 0) / 100).toFixed(2).replace('.', ',');

/** UUID v4 (funciona também fora de HTTPS, onde crypto.randomUUID não existe). */
export function uuid() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hex = [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
