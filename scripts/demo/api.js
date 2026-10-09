// API de DEMONSTRAÇÃO: atende no próprio navegador as chamadas que o servidor atende,
// tanto as da loja (/api/menu, /api/orders...) quanto as do painel (/api/admin/...).
//
// Só é usada na versão estática publicada no GitHub Pages, que não tem servidor nem banco.
// - O cálculo do pedido é o MESMO módulo do servidor (pricing.js e option-rules.js,
//   copiados pelo scripts/build-demo.js). Os dados do painel vêm dos mesmos serviços do servidor,
//   gerados no build a partir do cardápio de exemplo.
// - Nada é enviado a lugar nenhum e nada é cobrado: pedidos, cupons e ajustes ficam guardados
//   apenas neste navegador (localStorage).
// - O painel de demonstração abre sem senha. Isto NÃO é o controle de acesso do sistema:
//   no sistema real, quem confere login, sessão, CSRF e permissões é o servidor.
import { calculateOrder, LIMITS } from './pricing.js';

const CHAVE = 'desu.demo.v2';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TOKEN = /^[A-Za-z0-9_-]{32}$/;
const VISITANTE = { name: 'Visitante (demonstração)', email: 'demo@desuburguer.exemplo' };

const TRANSICOES = {
  recebido: ['em_preparo', 'cancelado'],
  em_preparo: ['pronto', 'saiu_para_entrega', 'cancelado'],
  pronto: ['concluido', 'cancelado'],
  saiu_para_entrega: ['concluido', 'cancelado'],
  concluido: [],
  cancelado: [],
};

// Pedidos de exemplo para o painel não começar vazio (clientes fictícios).
const EXEMPLOS = [
  {
    nome: 'Mariana (exemplo)', fone: '11987650001', tipo: 'entrega', pagamento: 'pix', minutos: 4,
    endereco: { street: 'Rua das Flores', number: '120', district: 'Centro', complement: 'Apto 12', reference: '' },
    status: ['recebido'],
    itens: [['X-Bacon', 2, ['Ao ponto', 'Brioche'], ['Bacon extra']], ['Batata frita grande', 1], ['Refrigerante lata', 2, ['Guaraná']]],
  },
  {
    nome: 'Rafael (exemplo)', fone: '11987650002', tipo: 'retirada', pagamento: 'cartao', minutos: 14,
    status: ['recebido', 'em_preparo'],
    itens: [['Desu Smash Duplo', 1], ['Onion rings', 1], ['Milk-shake', 1]],
    observacoes: 'Sem cebola no lanche, por favor.',
  },
  {
    nome: 'Beatriz (exemplo)', fone: '11987650003', tipo: 'entrega', pagamento: 'dinheiro', troco: 15000, minutos: 38,
    endereco: { street: 'Avenida Brasil', number: '845', district: 'Jardim América', complement: '', reference: 'Portão azul' },
    status: ['recebido', 'em_preparo', 'saiu_para_entrega'],
    itens: [['Combo Família', 1, ['Cola']], ['Pudim', 2]],
  },
  {
    nome: 'Carlos (exemplo)', fone: '11987650004', tipo: 'retirada', pagamento: 'pix', minutos: 150,
    status: ['recebido', 'em_preparo', 'pronto', 'concluido'],
    itens: [['Açaí 500 ml', 1, ['Banana', 'Granola', 'Leite condensado']]],
  },
];

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

// ---------- estado guardado no navegador ----------

const estadoVazio = () => ({
  versao: 2,
  seqPedido: 0,
  seqCupom: 0,
  pedidos: [],
  cupons: [],
  ajustes: { produtos: {}, adicionais: {}, escolhas: {}, settings: null },
  exemplos: false,
});

function lerEstado() {
  if (memoria) return memoria;
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE) || 'null');
    return salvo && salvo.versao === 2 ? salvo : estadoVazio();
  } catch {
    memoria = estadoVazio();
    return memoria;
  }
}

function gravarEstado(e) {
  e.pedidos = e.pedidos.slice(-50);
  if (memoria) {
    memoria = e;
    return;
  }
  try {
    localStorage.setItem(CHAVE, JSON.stringify(e));
  } catch {
    memoria = e;
  }
}

function tokenAleatorio() {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

const agora = () => new Date().toISOString();
const disp = (mapa, id, atual) => (Object.hasOwn(mapa, id) ? mapa[id] : atual);

/** Configurações, catálogo e cardápio com os ajustes feitos no painel de demonstração. */
function comAjustes(d, e) {
  const aj = e.ajustes;
  const settings = { ...d.settings, ...(aj.settings || {}) };
  const products = new Map([...d.catalog.products].map(([id, p]) => [id, { ...p, available: disp(aj.produtos, id, p.available) }]));
  const addons = new Map([...d.catalog.addons].map(([id, a]) => [id, { ...a, available: disp(aj.adicionais, id, a.available) }]));
  const choices = new Map(
    [...d.catalog.options.choices].map(([id, c]) => [id, { ...c, available: disp(aj.escolhas, id, c.available) }])
  );
  const catalog = { products, addons, links: d.catalog.links, options: { ...d.catalog.options, choices } };
  return { settings, catalog };
}

function configPublica(s, labels) {
  return {
    storeName: s.store_name,
    acceptingOrders: s.accepting_orders,
    closedMessage: s.closed_message,
    pickupEnabled: s.pickup_enabled,
    pickupAddress: s.pickup_address,
    deliveryEnabled: s.delivery_enabled,
    deliveryFeeCents: s.delivery_fee_cents,
    minOrderCents: s.min_order_cents,
    paymentMethods: Object.entries(s.payment_methods)
      .filter(([, on]) => on)
      .map(([id]) => ({ id, label: labels[id] })),
    contactPhone: s.contact_phone,
    openingHours: s.opening_hours,
    aboutText: s.about_text,
    whatsappUrl: s.whatsapp ? `https://wa.me/55${s.whatsapp}` : '',
  };
}

function cardapio(d, e) {
  const { settings } = comAjustes(d, e);
  const aj = e.ajustes;
  const m = structuredClone(d.menu);
  m.store = configPublica(settings, d.paymentLabels);
  for (const p of m.categories.flatMap((c) => c.products)) {
    p.available = disp(aj.produtos, p.id, p.available);
    for (const a of p.addons) a.available = disp(aj.adicionais, a.id, a.available);
    for (const g of p.optionGroups) for (const c of g.choices) c.available = disp(aj.escolhas, c.id, c.available);
  }
  return m;
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
const SO_NO_SISTEMA = 'Na demonstração, esta alteração não está disponível. Rodando o projeto, o painel permite cadastrar e editar tudo.';

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

/** Igual ao normalizeCouponCode do servidor. */
function codigoCupom(v) {
  if (v === undefined || v === null || v === '') return '';
  if (typeof v !== 'string') throw recusa('Cupom inválido.');
  const code = v.trim().toUpperCase();
  if (!/^[A-Z0-9]{3,20}$/.test(code)) throw recusa('Cupom inválido. Use de 3 a 20 letras ou números.');
  return code;
}

const acharCupom = (e, code) => (code ? e.cupons.find((c) => c.code === code) || null : null);

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

// ---------- pedidos ----------

const codigo = (id) => `#${String(id).padStart(4, '0')}`;
const statusAtual = (p) => p.historico[p.historico.length - 1].status;
const proximos = (status, tipo) =>
  (TRANSICOES[status] || []).filter((s) => (s === 'pronto' ? tipo === 'retirada' : s === 'saiu_para_entrega' ? tipo === 'entrega' : true));

function novoPedido(e, { result, fulfillment, cliente, endereco, observacoes, pagamento, troco, cupom, chave, criadoEm, historico }) {
  e.seqPedido += 1;
  const pedido = {
    id: e.seqPedido,
    token: tokenAleatorio(),
    chave,
    criadoEm,
    fulfillment,
    cliente,
    endereco,
    observacoes,
    pagamento,
    troco,
    cupom,
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
    historico,
  };
  e.pedidos.push(pedido);
  return pedido;
}

function criarExemplos(d, e) {
  if (e.exemplos) return;
  const { settings, catalog } = comAjustes(d, e);
  const produtos = new Map(d.menu.categories.flatMap((c) => c.products).map((p) => [p.name, p]));
  const minutosAntes = (min) => Date.now() - min * 60000;
  for (const ex of EXEMPLOS) {
    const items = ex.itens.map(([nome, qtd, escolhas = [], adicionais = []]) => {
      const p = produtos.get(nome);
      if (!p) return null;
      const optionIds = [];
      for (const g of p.optionGroups) {
        const marcadas = g.choices.filter((c) => escolhas.includes(c.name)).slice(0, g.maxChoices || 99);
        if (!marcadas.length && g.required) marcadas.push(g.choices[0]);
        optionIds.push(...marcadas.map((c) => c.id));
      }
      const addonIds = p.addons.filter((a) => adicionais.includes(a.name)).map((a) => a.id);
      return { productId: p.id, quantity: qtd, addonIds, optionIds: optionIds.sort((a, b) => a - b), notes: '' };
    }).filter(Boolean);
    const result = calculateOrder(items, catalog, { fulfillment: ex.tipo, settings });
    if (!items.length || result.issues.length) continue;
    const inicio = minutosAntes(ex.minutos);
    novoPedido(e, {
      result,
      fulfillment: ex.tipo,
      cliente: { name: ex.nome, phone: ex.fone },
      endereco: ex.endereco || null,
      observacoes: ex.observacoes || '',
      pagamento: ex.pagamento,
      troco: ex.troco || null,
      cupom: null,
      chave: null,
      criadoEm: new Date(inicio).toISOString(),
      historico: ex.status.map((status, i) => ({ status, at: new Date(inicio + i * 6 * 60000).toISOString() })),
    });
  }
  e.exemplos = true;
}

function pedidoParaPainel(d, p) {
  const status = statusAtual(p);
  return {
    id: p.id,
    code: codigo(p.id),
    status,
    statusLabel: d.statusLabels[status],
    nextStatuses: proximos(status, p.fulfillment).map((s) => ({ status: s, label: d.statusLabels[s] })),
    fulfillment: p.fulfillment,
    customer: { name: p.cliente.name, phone: p.cliente.phone },
    address: p.endereco,
    notes: p.observacoes,
    paymentMethod: p.pagamento,
    paymentLabel: d.paymentLabels[p.pagamento],
    changeForCents: p.troco,
    subtotalCents: p.subtotalCents,
    discountCents: p.discountCents,
    deliveryFeeCents: p.deliveryFeeCents,
    totalCents: p.totalCents,
    couponCode: p.cupom,
    createdAt: p.criadoEm,
    updatedAt: p.historico[p.historico.length - 1].at,
    personalDataPurged: false,
    items: p.items,
    history: p.historico.map((h) => ({ status: h.status, label: d.statusLabels[h.status], at: h.at })),
  };
}

// ---------- rotas da loja ----------

function orcamento(d, e, body = {}) {
  const items = itensDoPedido(body.items);
  const fulfillment = tipoDePedido(body.fulfillment, 'retirada');
  const couponCode = codigoCupom(body.couponCode);
  const { settings, catalog } = comAjustes(d, e);
  return resposta(calculateOrder(items, catalog, { fulfillment, settings, coupon: acharCupom(e, couponCode), couponCode }));
}

function criarPedido(d, e, body = {}) {
  if (typeof body.idempotencyKey !== 'string' || !UUID.test(body.idempotencyKey)) {
    throw recusa('Identificador do pedido inválido. Recarregue a página e tente de novo.');
  }
  const chave = body.idempotencyKey.toLowerCase();
  const repetido = e.pedidos.find((p) => p.chave === chave);
  if (repetido) {
    return { code: codigo(repetido.id), trackingToken: repetido.token, status: statusAtual(repetido), totalCents: repetido.totalCents, replayed: true };
  }

  const fulfillment = tipoDePedido(body.fulfillment);
  const items = itensDoPedido(body.items);
  const couponCode = codigoCupom(body.couponCode);
  const nome = texto(body.customer?.name, { campo: 'o seu nome', min: 2, max: 80 });
  const fone = telefone(body.customer?.phone);
  let endereco = null;
  if (fulfillment === 'entrega') {
    const a = body.address || {};
    endereco = {
      street: texto(a.street, { campo: 'a rua', min: 3, max: 120 }),
      number: texto(a.number, { campo: 'o número', min: 1, max: 20 }),
      district: texto(a.district, { campo: 'o bairro', min: 2, max: 80 }),
      complement: texto(a.complement, { campo: 'o complemento', max: 80 }),
      reference: texto(a.reference, { campo: 'o ponto de referência', max: 120 }),
    };
  }
  const { settings, catalog } = comAjustes(d, e);
  const pagamento = body.paymentMethod;
  if (!Object.hasOwn(d.paymentLabels, pagamento)) throw recusa('Escolha a forma de pagamento.');
  if (!settings.payment_methods[pagamento]) throw recusa('Esta forma de pagamento não está disponível no momento.');
  const observacoes = texto(body.notes, { campo: 'as observações do pedido', max: 280 });
  const troco = pagamento === 'dinheiro' && inteiro(body.changeForCents, 0, 10000000) ? body.changeForCents : null;
  if (!inteiro(body.expectedTotalCents, 0, 10 ** 9)) throw recusa('Informe o total esperado.');

  const cupom = acharCupom(e, couponCode);
  const result = calculateOrder(items, catalog, { fulfillment, settings, coupon: cupom, couponCode });
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
  if (cupom && result.coupon) cupom.uses += 1;
  const criadoEm = agora();
  const pedido = novoPedido(e, {
    result,
    fulfillment,
    cliente: { name: nome, phone: fone },
    endereco,
    observacoes,
    pagamento,
    troco,
    cupom: result.coupon ? result.coupon.code : null,
    chave,
    criadoEm,
    historico: [{ status: 'recebido', at: criadoEm }],
  });
  return { code: codigo(pedido.id), trackingToken: pedido.token, status: 'recebido', totalCents: pedido.totalCents, replayed: false };
}

function acompanhar(d, e, body = {}) {
  const token = body.token;
  const p = typeof token === 'string' && TOKEN.test(token) ? e.pedidos.find((x) => x.token === token) : null;
  if (!p) throw recusa('Pedido não encontrado. Na demonstração, o pedido só existe no navegador em que foi feito.', 404);
  const { settings } = comAjustes(d, e);
  const status = statusAtual(p);
  return {
    code: codigo(p.id),
    status,
    statusLabel: d.statusLabels[status],
    fulfillment: p.fulfillment,
    customerFirstName: p.cliente.name.split(' ')[0],
    paymentMethod: d.paymentLabels[p.pagamento],
    changeForCents: p.troco,
    items: p.items,
    subtotalCents: p.subtotalCents,
    discountCents: p.discountCents,
    deliveryFeeCents: p.deliveryFeeCents,
    totalCents: p.totalCents,
    couponCode: p.cupom,
    createdAt: p.criadoEm,
    updatedAt: p.historico[p.historico.length - 1].at,
    history: p.historico.map((h) => ({ status: h.status, label: d.statusLabels[h.status], at: h.at })),
    pickupAddress: p.fulfillment === 'retirada' ? settings.pickup_address : '',
    contactPhone: settings.contact_phone,
  };
}

// ---------- rotas do painel ----------

function listarPedidos(d, e, scope) {
  let lista;
  if (scope === 'abertos') lista = e.pedidos.filter((p) => !['concluido', 'cancelado'].includes(statusAtual(p))).sort((a, b) => a.id - b.id);
  else if (scope === 'todos') lista = [...e.pedidos].sort((a, b) => b.id - a.id);
  else if (d.statusLabels[scope]) lista = e.pedidos.filter((p) => statusAtual(p) === scope).sort((a, b) => b.id - a.id);
  else throw recusa('Filtro inválido.');
  return { orders: lista.map((p) => pedidoParaPainel(d, p)), serverTime: agora() };
}

function mudarStatus(d, e, id, body = {}) {
  const p = e.pedidos.find((x) => x.id === id);
  if (!p) throw recusa('Pedido não encontrado.', 404);
  const para = body.status;
  const de = body.fromStatus;
  if (!d.statusLabels[para] || !d.statusLabels[de]) throw recusa('Status inválido.');
  const atual = statusAtual(p);
  if (atual !== de) throw recusa('Este pedido já foi atualizado por outra pessoa. A lista foi recarregada.', 409);
  if (!proximos(atual, p.fulfillment).includes(para)) {
    throw recusa(`Não é possível mudar de "${d.statusLabels[atual]}" para "${d.statusLabels[para]}".`, 409);
  }
  p.historico.push({ status: para, at: agora() });
  if (para === 'cancelado' && p.cupom) {
    const c = acharCupom(e, p.cupom);
    if (c && c.uses > 0) c.uses -= 1;
  }
  return pedidoParaPainel(d, p);
}

/** Só a disponibilidade pode ser ligada/desligada na demonstração. */
function alternarDisponivel(mapa, id, body, existe) {
  if (!existe) throw recusa('Não encontrado.', 404);
  const chaves = Object.keys(body || {});
  if (chaves.length !== 1 || chaves[0] !== 'available' || typeof body.available !== 'boolean') {
    throw recusa('Na demonstração, aqui só dá para ligar e desligar a disponibilidade. Rodando o projeto, dá para editar tudo.');
  }
  mapa[id] = body.available;
  return { ok: true };
}

function salvarConfiguracoes(d, e, body = {}) {
  const atual = comAjustes(d, e).settings;
  const prox = { ...atual, payment_methods: { ...atual.payment_methods } };
  const bool = (k) => {
    if (typeof body[k] !== 'boolean') throw recusa('Valor inválido nas configurações.');
    return body[k];
  };
  if ('store_name' in body) prox.store_name = texto(body.store_name, { campo: 'o nome da loja', min: 2, max: 60 });
  if ('accepting_orders' in body) prox.accepting_orders = bool('accepting_orders');
  if ('closed_message' in body) prox.closed_message = texto(body.closed_message, { campo: 'a mensagem de loja fechada', max: 200 });
  if ('pickup_enabled' in body) prox.pickup_enabled = bool('pickup_enabled');
  if ('pickup_address' in body) prox.pickup_address = texto(body.pickup_address, { campo: 'o endereço de retirada', max: 200 });
  if ('delivery_enabled' in body) prox.delivery_enabled = bool('delivery_enabled');
  if ('delivery_fee_cents' in body) {
    if (!inteiro(body.delivery_fee_cents, 0, 100000)) throw recusa('Confira a taxa de entrega.');
    prox.delivery_fee_cents = body.delivery_fee_cents;
  }
  if ('min_order_cents' in body) {
    if (!inteiro(body.min_order_cents, 0, 1000000)) throw recusa('Confira o pedido mínimo.');
    prox.min_order_cents = body.min_order_cents;
  }
  if ('contact_phone' in body) prox.contact_phone = texto(body.contact_phone, { campo: 'o telefone de contato', max: 30 });
  if ('opening_hours' in body) prox.opening_hours = texto(body.opening_hours, { campo: 'o horário de funcionamento', max: 120 });
  if ('about_text' in body) prox.about_text = typeof body.about_text === 'string' ? body.about_text.trim().slice(0, 400) : prox.about_text;
  if ('whatsapp' in body) prox.whatsapp = body.whatsapp ? telefone(body.whatsapp) : '';
  if ('payment_methods' in body && body.payment_methods && typeof body.payment_methods === 'object') {
    for (const k of Object.keys(d.paymentLabels)) if (typeof body.payment_methods[k] === 'boolean') prox.payment_methods[k] = body.payment_methods[k];
  }
  if (!prox.pickup_enabled && !prox.delivery_enabled) throw recusa('Ative pelo menos uma opção: entrega ou retirada.');
  if (!Object.values(prox.payment_methods).some(Boolean)) throw recusa('Ative pelo menos uma forma de pagamento.');
  e.ajustes.settings = prox;
  return { settings: prox };
}

const cupomParaPainel = (c) => ({
  id: c.id,
  code: c.code,
  kind: c.kind,
  value: c.value,
  minOrderCents: c.min_order_cents,
  maxUses: c.max_uses,
  uses: c.uses,
  validUntil: c.valid_until,
  active: Boolean(c.active),
  createdAt: c.created_at,
});

function dadosDoCupom(body, parcial) {
  const out = {};
  if (!parcial) {
    out.code = codigoCupom(body.code);
    if (!out.code) throw recusa('Informe o código do cupom.');
  } else if ('code' in body) {
    throw recusa('O código do cupom não pode ser alterado. Crie um novo cupom.');
  }
  if (!parcial || 'kind' in body) {
    if (!['percent', 'fixed'].includes(body.kind)) throw recusa('Escolha o tipo do cupom.');
    out.kind = body.kind;
  }
  if (!parcial || 'value' in body) {
    if (!inteiro(body.value, 1, 10000000)) throw recusa('Confira o valor do cupom.');
    out.value = body.value;
  }
  if (!parcial || 'minOrderCents' in body) {
    const v = body.minOrderCents ?? 0;
    if (!inteiro(v, 0, 10000000)) throw recusa('Confira o pedido mínimo do cupom.');
    out.min_order_cents = v;
  }
  if (!parcial || 'maxUses' in body) {
    if (body.maxUses !== null && body.maxUses !== undefined && !inteiro(body.maxUses, 1, 1000000)) throw recusa('Confira o limite de usos.');
    out.max_uses = body.maxUses ?? null;
  }
  if (!parcial || 'validUntil' in body) {
    if (body.validUntil && !/^\d{4}-\d{2}-\d{2}$/.test(body.validUntil)) throw recusa('Validade inválida (use AAAA-MM-DD).');
    out.valid_until = body.validUntil || null;
  }
  if (!parcial || 'active' in body) out.active = body.active ?? true;
  return out;
}

function painel(d, e, metodo, rota, query, body) {
  const aj = e.ajustes;
  const seg = rota.split('/').filter(Boolean); // ['api', 'admin', ...]
  const [, , recurso, idTxt, sub] = seg;
  const id = idTxt !== undefined ? Number(idTxt) : null;

  if (recurso === 'session' && metodo === 'GET') return { user: VISITANTE, csrfToken: 'demo', imageOptimization: false };
  if (recurso === 'login' && metodo === 'POST') return { user: VISITANTE, csrfToken: 'demo' };
  if (recurso === 'logout' && metodo === 'POST') return { ok: true };
  if (recurso === 'password') throw recusa('Na demonstração não existe senha para trocar. No sistema real, a senha precisa ter pelo menos 15 caracteres.');

  if (recurso === 'orders') {
    if (metodo === 'GET' && id === null) return listarPedidos(d, e, query.get('scope') || 'abertos');
    if (metodo === 'GET') {
      const p = e.pedidos.find((x) => x.id === id);
      if (!p) throw recusa('Pedido não encontrado.', 404);
      return pedidoParaPainel(d, p);
    }
    if (metodo === 'PATCH' && sub === 'status') return mudarStatus(d, e, id, body);
  }

  if (recurso === 'categories' && metodo === 'GET') return { categories: d.admin.categories };
  if (recurso === 'products' && metodo === 'GET') {
    const r = structuredClone(d.admin.products);
    for (const p of r.products) p.available = disp(aj.produtos, p.id, p.available);
    return r;
  }
  if (recurso === 'products' && metodo === 'PUT' && sub === undefined) {
    return alternarDisponivel(aj.produtos, id, body, d.catalog.products.has(id));
  }
  if (recurso === 'addons' && metodo === 'GET') {
    return { addons: d.admin.addons.map((a) => ({ ...a, available: disp(aj.adicionais, a.id, a.available) })) };
  }
  if (recurso === 'addons' && metodo === 'PUT') return alternarDisponivel(aj.adicionais, id, body, d.catalog.addons.has(id));
  if (recurso === 'option-groups' && metodo === 'GET') {
    const groups = structuredClone(d.admin.optionGroups);
    for (const g of groups) for (const c of g.choices) c.available = disp(aj.escolhas, c.id, c.available);
    return { groups };
  }
  if (recurso === 'option-choices' && metodo === 'PUT') {
    return alternarDisponivel(aj.escolhas, id, body, d.catalog.options.choices.has(id));
  }
  if (recurso === 'coupons' && metodo === 'GET') {
    return { coupons: [...e.cupons].sort((a, b) => Number(b.active) - Number(a.active) || b.id - a.id).map(cupomParaPainel) };
  }
  if (recurso === 'coupons' && metodo === 'POST') {
    const c = dadosDoCupom(body || {}, false);
    if (c.kind === 'percent' && c.value > 100) throw recusa('Cupom percentual deve ser de 1 a 100%.');
    if (e.cupons.some((x) => x.code === c.code)) throw recusa('Já existe um cupom com esse código.', 409);
    e.seqCupom += 1;
    e.cupons.push({ id: e.seqCupom, uses: 0, created_at: agora(), ...c });
    return { id: e.seqCupom };
  }
  if (recurso === 'coupons' && metodo === 'PUT') {
    const atual = e.cupons.find((x) => x.id === id);
    if (!atual) throw recusa('Cupom não encontrado.', 404);
    const c = dadosDoCupom(body || {}, true);
    if ((c.kind ?? atual.kind) === 'percent' && (c.value ?? atual.value) > 100) throw recusa('Cupom percentual deve ser de 1 a 100%.');
    Object.assign(atual, c);
    return { ok: true };
  }
  if (recurso === 'settings' && metodo === 'GET') return { settings: comAjustes(d, e).settings };
  if (recurso === 'settings' && metodo === 'PUT') return salvarConfiguracoes(d, e, body);

  throw recusa(SO_NO_SISTEMA);
}

/**
 * Mesmo contrato do `api()` de lib.js: devolve os dados ou lança `ApiError(status, data)`.
 */
export async function demoApi(path, opts, ApiError) {
  const url = new URL(String(path).replace(/^.*?(\/api\/)/, '$1'), 'https://demo.local');
  const rota = url.pathname;
  const metodo = (opts.method || (opts.body !== undefined || opts.raw !== undefined ? 'POST' : 'GET')).toUpperCase();
  let d;
  try {
    d = await carregarDados();
  } catch {
    throw new ApiError(0, { error: 'Não foi possível carregar os dados da demonstração. Recarregue a página.' });
  }
  const e = lerEstado();
  try {
    criarExemplos(d, e);
    let r;
    if (metodo === 'GET' && rota === '/api/menu') r = cardapio(d, e);
    else if (metodo === 'POST' && rota === '/api/orders/quote') r = orcamento(d, e, opts.body);
    else if (metodo === 'POST' && rota === '/api/orders') r = criarPedido(d, e, opts.body);
    else if (metodo === 'POST' && rota === '/api/orders/track') r = acompanhar(d, e, opts.body);
    else if (rota.startsWith('/api/admin/')) r = painel(d, e, metodo, rota, url.searchParams, opts.raw !== undefined ? {} : opts.body);
    else throw recusa('Esta função não está disponível na demonstração.', 404);
    gravarEstado(e);
    return r;
  } catch (err) {
    gravarEstado(e);
    if (err instanceof Recusa) throw new ApiError(err.status, err.data);
    throw new ApiError(500, { error: 'A demonstração teve um problema. Recarregue a página e tente de novo.' });
  }
}
