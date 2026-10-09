// API de DEMONSTRAÇÃO: atende no próprio navegador as mesmas chamadas que o servidor
// atende (/api/menu, /api/orders/quote, /api/orders e /api/orders/track).
//
// Só é usada na versão estática publicada no GitHub Pages, que não tem servidor nem banco.
// - O cálculo do pedido é o MESMO módulo do servidor (pricing.js e option-rules.js,
//   copiados pelo scripts/build-demo.js).
// - Nada é enviado a lugar nenhum e nada é cobrado: os pedidos ficam guardados apenas
//   neste navegador (localStorage) e o andamento avança sozinho, para mostrar o acompanhamento.
// - Esta camada NÃO é segurança: no sistema real, quem confere tudo é o servidor.
import { calculateOrder, LIMITS } from './pricing.js';

const STORAGE_KEY = 'desu.demo.pedidos.v1';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TOKEN = /^[A-Za-z0-9_-]{32}$/;

// Etapas simuladas (segundos depois do pedido).
const ETAPAS = {
  entrega: [
    ['recebido', 0],
    ['em_preparo', 20],
    ['saiu_para_entrega', 60],
    ['concluido', 150],
  ],
  retirada: [
    ['recebido', 0],
    ['em_preparo', 20],
    ['pronto', 60],
    ['concluido', 150],
  ],
};

let dadosPromise = null;
let memoria = null; // usado se o navegador bloquear o localStorage

function carregarDados() {
  dadosPromise ||= fetch(new URL('./dados.json', import.meta.url))
    .then((r) => {
      if (!r.ok) throw new Error('dados');
      return r.json();
    })
    .then((d) => ({
      ...d,
      catalog: {
        products: new Map(d.catalog.products.map((p) => [p.id, p])),
        addons: new Map(d.catalog.addons.map((a) => [a.id, a])),
        links: new Map(d.catalog.links.map(([pid, ids]) => [pid, new Set(ids)])),
        options: {
          groups: new Map(d.catalog.options.groups.map((g) => [g.id, g])),
          choices: new Map(d.catalog.options.choices.map((c) => [c.id, c])),
          productGroups: new Map(d.catalog.options.productGroups),
        },
      },
    }))
    .catch((err) => {
      dadosPromise = null;
      throw err;
    });
  return dadosPromise;
}

function lerPedidos() {
  if (memoria) return memoria;
  try {
    const salvo = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(salvo) ? salvo : [];
  } catch {
    memoria = [];
    return memoria;
  }
}

function salvarPedidos(lista) {
  const ultimos = lista.slice(-30);
  if (memoria) {
    memoria = ultimos;
    return;
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ultimos));
  } catch {
    memoria = ultimos;
  }
}

function tokenAleatorio() {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ---------- validação (mesmas mensagens do servidor) ----------

class Recusa extends Error {
  constructor(status, data) {
    super(data.error);
    this.status = status;
    this.data = data;
  }
}
const recusa = (msg, status = 400, extra = {}) => new Recusa(status, { error: msg, ...extra });

function texto(v, { campo, min = 0, max }) {
  if (v === undefined || v === null || v === '') {
    if (min > 0) throw recusa(`Informe ${campo}.`);
    return '';
  }
  if (typeof v !== 'string') throw recusa(`Informe ${campo}.`);
  const t = v.replace(/\s+/g, ' ').trim();
  if ([...t].length < min) throw recusa(min <= 1 ? `Informe ${campo}.` : `Confira ${campo}: precisa ter pelo menos ${min} caracteres.`);
  if (max && [...t].length > max) throw recusa(`Confira ${campo}: pode ter no máximo ${max} caracteres.`);
  return t;
}

const inteiro = (v, min, max) => Number.isInteger(v) && v >= min && v <= max;
const listaIds = (v) => (Array.isArray(v) ? v.filter((x) => inteiro(x, 1, 2 ** 31)).sort((a, b) => a - b) : []);

function itensDoPedido(items) {
  if (!Array.isArray(items) || items.length === 0) throw recusa('Seu carrinho está vazio.');
  if (items.length > LIMITS.maxLines) throw recusa(`O pedido pode ter no máximo ${LIMITS.maxLines} itens diferentes.`);
  const lista = items.map((it) => {
    if (!it || !inteiro(it.productId, 1, 2 ** 31)) throw recusa('Um item do carrinho é inválido.');
    if (!inteiro(it.quantity, 1, LIMITS.maxQuantityPerLine)) throw recusa(`A quantidade deve estar entre 1 e ${LIMITS.maxQuantityPerLine}.`);
    return {
      productId: it.productId,
      quantity: it.quantity,
      addonIds: listaIds(it.addonIds),
      optionIds: listaIds(it.optionIds),
      notes: texto(it.notes, { campo: 'a observação do item', max: LIMITS.maxItemNotes }),
    };
  });
  if (lista.reduce((s, it) => s + it.quantity, 0) > LIMITS.maxTotalUnits) {
    throw recusa(`Para pedidos com mais de ${LIMITS.maxTotalUnits} unidades, fale diretamente com a loja.`);
  }
  return lista;
}

function telefone(v) {
  const digitos = texto(v, { campo: 'o telefone', min: 1, max: 25 }).replace(/\D/g, '').replace(/^55(?=\d{10,11}$)/, '');
  if (!/^[1-9]{2}9?\d{8}$/.test(digitos)) throw recusa('Telefone inválido. Use DDD + número, por exemplo (11) 91234-5678.');
  return digitos;
}

function tipoDePedido(v, padrao) {
  const f = v ?? padrao;
  if (f !== 'entrega' && f !== 'retirada') throw recusa('Escolha entrega ou retirada.');
  return f;
}

function resposta(result) {
  return {
    lines: result.lines.map((l) => ({
      index: l.index,
      productId: l.productId,
      name: l.name,
      options: l.options,
      addons: l.addons,
      unitPriceCents: l.unitPriceCents,
      quantity: l.quantity,
      lineTotalCents: l.lineTotalCents,
      notes: l.notes,
    })),
    subtotalCents: result.subtotalCents,
    discountCents: result.discountCents,
    deliveryFeeCents: result.deliveryFeeCents,
    totalCents: result.totalCents,
    coupon: result.coupon,
    couponError: result.couponError,
    issues: result.issues,
  };
}

const codigoCupom = (v) => (typeof v === 'string' ? v.trim().toUpperCase().slice(0, 40) : '');

// ---------- rotas ----------

async function orcamento(d, body = {}) {
  const items = itensDoPedido(body.items);
  const fulfillment = tipoDePedido(body.fulfillment, 'retirada');
  const couponCode = codigoCupom(body.couponCode);
  // A demonstração não tem cupons cadastrados: qualquer código é recusado, como no servidor.
  return resposta(calculateOrder(items, d.catalog, { fulfillment, settings: d.settings, coupon: null, couponCode }));
}

async function criarPedido(d, body = {}) {
  if (typeof body.idempotencyKey !== 'string' || !UUID.test(body.idempotencyKey)) {
    throw recusa('Identificador do pedido inválido. Recarregue a página e tente de novo.');
  }
  const chave = body.idempotencyKey.toLowerCase();
  const pedidos = lerPedidos();
  const repetido = pedidos.find((p) => p.chave === chave);
  if (repetido) {
    return { code: repetido.code, trackingToken: repetido.token, status: 'recebido', totalCents: repetido.totalCents, replayed: true };
  }

  const fulfillment = tipoDePedido(body.fulfillment);
  const items = itensDoPedido(body.items);
  const couponCode = codigoCupom(body.couponCode);
  const nome = texto(body.customer?.name, { campo: 'o seu nome', min: 2, max: 80 });
  telefone(body.customer?.phone); // conferido, mas não guardado: é só uma demonstração
  if (fulfillment === 'entrega') {
    const a = body.address || {};
    texto(a.street, { campo: 'a rua', min: 3, max: 120 });
    texto(a.number, { campo: 'o número', min: 1, max: 20 });
    texto(a.district, { campo: 'o bairro', min: 2, max: 80 });
  }
  const pagamento = body.paymentMethod;
  if (!d.settings.payment_methods[pagamento]) throw recusa('Escolha a forma de pagamento.');
  const troco = pagamento === 'dinheiro' && inteiro(body.changeForCents, 0, 10000000) ? body.changeForCents : null;
  if (!inteiro(body.expectedTotalCents, 0, 10 ** 9)) throw recusa('Informe o total esperado.');

  const result = calculateOrder(items, d.catalog, { fulfillment, settings: d.settings, coupon: null, couponCode });
  if (result.issues.length > 0) {
    throw recusa(result.issues[0].message, 409, { code: 'pedido_invalido', issues: result.issues, quote: resposta(result) });
  }
  if (couponCode && result.couponError) {
    throw recusa(result.couponError, 409, { code: 'cupom_invalido', quote: resposta(result) });
  }
  if (result.totalCents !== body.expectedTotalCents) {
    throw recusa('Os valores do pedido mudaram. Confira o novo total antes de confirmar.', 409, {
      code: 'total_alterado',
      quote: resposta(result),
    });
  }
  if (troco !== null && troco > 0 && troco < result.totalCents) {
    throw recusa('O valor para troco precisa ser maior ou igual ao total do pedido.');
  }

  const numero = pedidos.reduce((m, p) => Math.max(m, p.numero), 0) + 1;
  const pedido = {
    numero,
    code: `#${String(numero).padStart(4, '0')}`,
    chave,
    token: tokenAleatorio(),
    criadoEm: new Date().toISOString(),
    fulfillment,
    primeiroNome: nome.split(' ')[0],
    pagamento,
    troco,
    items: result.lines.map((l) => ({
      name: l.name,
      quantity: l.quantity,
      unitPriceCents: l.unitPriceCents,
      lineTotalCents: l.lineTotalCents,
      notes: l.notes,
      options: l.options.map((o) => ({ groupName: o.groupName, name: o.name, priceCents: o.priceCents })),
      addons: l.addons.map((a) => ({ name: a.name, priceCents: a.priceCents })),
    })),
    subtotalCents: result.subtotalCents,
    discountCents: result.discountCents,
    deliveryFeeCents: result.deliveryFeeCents,
    totalCents: result.totalCents,
  };
  pedidos.push(pedido);
  salvarPedidos(pedidos);
  return { code: pedido.code, trackingToken: pedido.token, status: 'recebido', totalCents: pedido.totalCents, replayed: false };
}

async function acompanhar(d, body = {}) {
  const token = body.token;
  const pedido = typeof token === 'string' && TOKEN.test(token) ? lerPedidos().find((p) => p.token === token) : null;
  if (!pedido) throw recusa('Pedido não encontrado. Na demonstração, o pedido só existe no navegador em que foi feito.', 404);
  const inicio = Date.parse(pedido.criadoEm);
  const passados = (Date.now() - inicio) / 1000;
  const history = ETAPAS[pedido.fulfillment]
    .filter(([, seg]) => seg <= passados)
    .map(([status, seg]) => ({ status, label: d.statusLabels[status], at: new Date(inicio + seg * 1000).toISOString() }));
  const atual = history[history.length - 1];
  return {
    code: pedido.code,
    status: atual.status,
    statusLabel: atual.label,
    fulfillment: pedido.fulfillment,
    customerFirstName: pedido.primeiroNome,
    paymentMethod: d.paymentLabels[pedido.pagamento],
    changeForCents: pedido.troco,
    items: pedido.items,
    subtotalCents: pedido.subtotalCents,
    discountCents: pedido.discountCents,
    deliveryFeeCents: pedido.deliveryFeeCents,
    totalCents: pedido.totalCents,
    couponCode: null,
    createdAt: pedido.criadoEm,
    updatedAt: atual.at,
    history,
    pickupAddress: pedido.fulfillment === 'retirada' ? d.settings.pickup_address : '',
    contactPhone: d.settings.contact_phone,
  };
}

/**
 * Mesmo contrato do `api()` de lib.js: devolve os dados ou lança `ApiError(status, data)`.
 */
export async function demoApi(path, opts, ApiError) {
  const rota = String(path).replace(/^.*(\/api\/)/, '$1').split('?')[0];
  const metodo = opts.method || (opts.body !== undefined ? 'POST' : 'GET');
  let d;
  try {
    d = await carregarDados();
  } catch {
    throw new ApiError(0, { error: 'Não foi possível carregar o cardápio da demonstração. Recarregue a página.' });
  }
  try {
    if (metodo === 'GET' && rota === '/api/menu') return structuredClone(d.menu);
    if (metodo === 'POST' && rota === '/api/orders/quote') return await orcamento(d, opts.body);
    if (metodo === 'POST' && rota === '/api/orders') return await criarPedido(d, opts.body);
    if (metodo === 'POST' && rota === '/api/orders/track') return await acompanhar(d, opts.body);
    throw recusa('Esta função não está disponível na demonstração.', 404);
  } catch (err) {
    if (err instanceof Recusa) throw new ApiError(err.status, err.data);
    throw new ApiError(500, { error: 'A demonstração teve um problema. Recarregue a página e tente de novo.' });
  }
}
