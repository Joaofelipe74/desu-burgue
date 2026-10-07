// Página do cardápio: lista produtos, personalização e carrinho.
import { cart } from './cart.js';
import { api, h, icon, money, optionsText, productImage, storage, toast } from './lib.js';

const $ = (sel) => document.querySelector(sel);
let menu = null; // resposta de /api/menu
let productsById = new Map();

// Ícones dos botões estáticos
document.querySelectorAll('[data-close].icon-btn').forEach((b) => b.append(icon('close')));
$('#pd-minus').append(icon('minus'));
$('#pd-plus').append(icon('plus'));

// ---------- Cardápio ----------

async function loadMenu() {
  const status = $('#menu-status');
  try {
    menu = await api('/api/menu');
  } catch (err) {
    status.textContent = '';
    status.append(
      h('p', { text: `Não foi possível carregar o cardápio. ${err.message}` }),
      h('button', { class: 'btn btn-secondary', type: 'button', text: 'Tentar novamente', onclick: () => location.reload() })
    );
    return;
  }
  productsById = new Map(menu.categories.flatMap((c) => c.products).map((p) => [p.id, p]));
  renderStore();
  renderFeatured();
  renderChips();
  renderMenu();
  renderCart();
  if (location.hash === '#carrinho') {
    history.replaceState(null, '', location.pathname);
    cartDlg.showModal();
  }
}

function renderStore() {
  const s = menu.store;
  document.querySelectorAll('[data-store-name]').forEach((el) => (el.textContent = s.storeName));
  document.title = `${s.storeName} — Cardápio`;
  const st = $('#store-status');
  st.hidden = false;
  st.className = `store-status ${s.acceptingOrders ? 'is-open' : 'is-closed'}`;
  st.textContent = s.acceptingOrders ? 'Aberto para pedidos' : s.closedMessage || 'Fechado no momento';

  const hours = $('#hero-hours');
  hours.hidden = !s.openingHours;
  hours.textContent = s.openingHours ? `Horário: ${s.openingHours}` : '';

  // Só aceita link do WhatsApp no formato gerado pelo servidor
  const wa = $('#hero-whatsapp');
  const waOk = /^https:\/\/wa\.me\/\d{12,13}$/.test(s.whatsappUrl || '');
  wa.hidden = !waOk;
  if (waOk) wa.href = s.whatsappUrl;

  if (s.aboutText) $('#about-text').textContent = s.aboutText;

  const PAY = { dinheiro: 'dinheiro', cartao: 'cartão', pix: 'Pix' };
  const names = s.paymentMethods.map((m) => PAY[m.id] || m.label);
  let payments = names.length > 1 ? `${names.slice(0, -1).join(', ')} ou ${names.at(-1)}` : names[0] || '';
  payments = payments.charAt(0).toUpperCase() + payments.slice(1);
  const cards = [
    s.openingHours && ['Horário', s.openingHours],
    s.deliveryEnabled && [
      'Entrega',
      `${s.deliveryFeeCents ? `Taxa de ${money(s.deliveryFeeCents)}` : 'Sem taxa de entrega'}${s.minOrderCents ? ` · pedido mínimo ${money(s.minOrderCents)}` : ''}`,
    ],
    s.pickupEnabled && ['Retirada no balcão', s.pickupAddress || 'Sem taxa. Retire no balcão da loja.'],
    payments && ['Pagamento', `${payments}, na entrega ou na retirada.`],
  ].filter(Boolean);
  const grid = $('#info-grid');
  grid.textContent = '';
  for (const [title, text] of cards) grid.append(h('div', { class: 'info-card' }, h('h3', { text: title }), h('p', { text })));

  const fc = $('#footer-contact');
  fc.textContent = '';
  if (s.openingHours) fc.append(h('li', { text: s.openingHours }));
  if (s.pickupAddress) fc.append(h('li', { text: s.pickupAddress }));
  if (s.contactPhone) fc.append(h('li', { text: `Telefone: ${s.contactPhone}` }));
  if (waOk) fc.append(h('li', {}, h('a', { href: s.whatsappUrl, target: '_blank', rel: 'noopener noreferrer', text: 'WhatsApp' })));
  if (!fc.children.length) fc.append(h('li', { text: 'Pedidos pelo site, com acompanhamento em tempo real.' }));
}

function renderFeatured() {
  const featured = menu.categories.flatMap((c) => c.products).filter((p) => p.featured && p.available).slice(0, 4);
  const box = $('#featured');
  box.textContent = '';
  $('#destaques').hidden = featured.length === 0;
  for (const p of featured) box.append(productCard(p, 'd'));
}

// ---------- Busca, filtros, ordenação e favoritos ----------

const FAV_KEY = 'desu.favoritos.v1';
let favorites = new Set((storage.get(FAV_KEY, []) || []).filter(Number.isInteger));
const filters = { q: '', chip: 'todos', sort: '' };
const TAG_LABELS = { novo: 'Novo', vegetariano: 'Vegetariano', picante: 'Picante', compartilhar: 'Para compartilhar' };
const CHIPS = [
  ['todos', 'Todos'],
  ['ofertas', 'Ofertas'],
  ['populares', 'Mais pedidos'],
  ['favoritos', 'Favoritos'],
  ['novo', 'Novidades'],
  ['vegetariano', 'Vegetarianos'],
  ['picante', 'Picantes'],
  ['compartilhar', 'Para compartilhar'],
];

const normalize = (t) =>
  String(t || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

const allProducts = () => menu.categories.flatMap((c) => c.products.map((p) => ({ ...p, categoryName: c.name })));
const popularRank = () => new Map((menu.popularProductIds || []).map((id, i) => [id, i]));

function chipMatches(p, chip) {
  if (chip === 'todos') return true;
  if (chip === 'ofertas') return Boolean(p.originalPriceCents);
  if (chip === 'favoritos') return favorites.has(p.id);
  if (chip === 'populares') return popularRank().has(p.id);
  return (p.tags || []).includes(chip);
}

function searchMatches(p, q) {
  if (!q) return true;
  const hay = normalize(`${p.name} ${p.description} ${p.categoryName || ''} ${(p.tags || []).map((t) => TAG_LABELS[t]).join(' ')}`);
  return normalize(q)
    .split(/\s+/)
    .filter(Boolean)
    .every((w) => hay.includes(w));
}

function sortProducts(list) {
  const out = [...list];
  if (filters.sort === 'asc') out.sort((a, b) => a.priceCents - b.priceCents);
  else if (filters.sort === 'desc') out.sort((a, b) => b.priceCents - a.priceCents);
  else if (filters.sort === 'name') out.sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
  else if (filters.chip === 'populares') {
    const rank = popularRank();
    out.sort((a, b) => rank.get(a.id) - rank.get(b.id));
  }
  return out;
}

function renderChips() {
  const box = $('#filter-chips');
  box.textContent = '';
  const all = allProducts();
  for (const [key, label] of CHIPS) {
    const count = key === 'todos' ? all.length : all.filter((p) => chipMatches(p, key)).length;
    if (key !== 'todos' && key !== 'favoritos' && count === 0) continue; // não mostra filtro vazio
    box.append(
      h(
        'button',
        {
          type: 'button',
          class: `chip${filters.chip === key ? ' is-active' : ''}`,
          'aria-pressed': String(filters.chip === key),
          onclick: () => {
            filters.chip = filters.chip === key ? 'todos' : key;
            renderChips();
            renderMenu();
          },
        },
        label,
        key !== 'todos' ? h('span', { class: 'chip-count', text: String(count) }) : null
      )
    );
  }
}

function renderMenu() {
  const root = $('#menu');
  const status = $('#menu-status');
  const nav = $('#category-nav');
  const fstatus = $('#filter-status');
  root.textContent = '';
  nav.textContent = '';
  if (menu.categories.length === 0) {
    status.textContent = 'O cardápio está sendo atualizado. Volte em breve!';
    return;
  }
  status.textContent = '';
  const filtering = Boolean(filters.q) || filters.chip !== 'todos' || Boolean(filters.sort);

  if (filtering) {
    nav.hidden = true;
    const list = sortProducts(allProducts().filter((p) => chipMatches(p, filters.chip) && searchMatches(p, filters.q)));
    fstatus.textContent = list.length
      ? `${list.length} ${list.length === 1 ? 'item encontrado' : 'itens encontrados'}.`
      : '';
    if (!list.length) {
      root.append(
        h(
          'div',
          { class: 'state' },
          h('p', {
            text:
              filters.chip === 'favoritos' && favorites.size === 0
                ? 'Você ainda não favoritou nada. Toque no coração de um produto para guardar aqui.'
                : 'Nenhum item encontrado com esses filtros.',
          }),
          h('button', { class: 'btn btn-secondary', type: 'button', text: 'Limpar filtros', onclick: clearFilters })
        )
      );
      return;
    }
    root.append(h('section', { class: 'menu-section', 'aria-label': 'Resultados' }, h('div', { class: 'product-grid' }, list.map((p) => productCard(p)))));
    return;
  }

  fstatus.textContent = '';
  nav.hidden = menu.categories.length < 2;
  for (const cat of menu.categories) {
    const id = `categoria-${cat.id}`;
    nav.append(h('a', { href: `#${id}`, text: cat.name }));
    root.append(
      h(
        'section',
        { class: 'menu-section', id, 'aria-labelledby': `${id}-t` },
        h('h3', { id: `${id}-t`, class: menu.categories.length > 1 ? 'category-title' : 'visually-hidden', text: cat.name }),
        h('div', { class: 'product-grid' }, cat.products.map((p) => productCard(p)))
      )
    );
  }
}

function clearFilters() {
  filters.q = '';
  filters.chip = 'todos';
  filters.sort = '';
  $('#menu-search').value = '';
  $('#menu-sort').value = '';
  renderChips();
  renderMenu();
}

let searchTimer;
$('#menu-search').addEventListener('input', (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    filters.q = e.target.value.trim().slice(0, 40);
    renderMenu();
  }, 150);
});
$('#menu-sort').addEventListener('change', (e) => {
  filters.sort = e.target.value;
  renderMenu();
});

function toggleFavorite(p, btn) {
  if (favorites.has(p.id)) favorites.delete(p.id);
  else favorites.add(p.id);
  storage.set(FAV_KEY, [...favorites]);
  const on = favorites.has(p.id);
  document.querySelectorAll(`.fav-btn[data-product="${p.id}"]`).forEach((b) => {
    b.setAttribute('aria-pressed', String(on));
    b.setAttribute('aria-label', on ? `Remover ${p.name} dos favoritos` : `Favoritar ${p.name}`);
  });
  toast(on ? `${p.name} nos favoritos.` : `${p.name} saiu dos favoritos.`);
  renderChips();
  if (filters.chip === 'favoritos') renderMenu();
  btn?.focus();
}

function productCard(p, prefix = 'p') {
  const canOrder = p.available && menu.store.acceptingOrders;
  const media = productImage(p);
  const fav = favorites.has(p.id);
  media.append(
    h(
      'button',
      {
        type: 'button',
        class: 'fav-btn',
        dataset: { product: String(p.id) },
        'aria-pressed': String(fav),
        'aria-label': fav ? `Remover ${p.name} dos favoritos` : `Favoritar ${p.name}`,
        onclick: (e) => toggleFavorite(p, e.currentTarget),
      },
      icon('heart')
    )
  );
  const badges = [
    p.originalPriceCents ? h('span', { class: 'badge-tag badge-offer', text: 'Oferta' }) : null,
    popularRank().has(p.id) ? h('span', { class: 'badge-tag badge-popular', text: 'Mais pedido' }) : null,
    ...(p.tags || []).map((t) => h('span', { class: `badge-tag badge-${t}`, text: TAG_LABELS[t] })),
  ].filter(Boolean);
  return h(
    'article',
    { class: `product-card${p.available ? '' : ' is-unavailable'}`, 'aria-labelledby': `${prefix}-${p.id}` },
    media,
    h(
      'div',
      { class: 'product-body' },
      badges.length ? h('div', { class: 'badges' }, badges) : null,
      h(prefix === 'd' ? 'h3' : 'h4', { id: `${prefix}-${p.id}`, class: 'product-name', text: p.name }),
      p.description ? h('p', { class: 'product-desc', text: p.description }) : h('p', { class: 'product-desc' }),
      h(
        'div',
        { class: 'product-footer' },
        h(
          'span',
          { class: 'price-box' },
          p.originalPriceCents
            ? h('span', { class: 'price-old' }, h('span', { class: 'visually-hidden', text: 'De ' }), money(p.originalPriceCents))
            : null,
          h('span', { class: 'price' }, p.originalPriceCents ? h('span', { class: 'visually-hidden', text: 'por ' }) : null, money(p.priceCents))
        ),
        p.available
          ? h('button', {
              class: 'btn btn-primary',
              type: 'button',
              text: 'Adicionar',
              disabled: !canOrder,
              'aria-label': `Adicionar ${p.name} ao carrinho`,
              onclick: () => openProduct(p),
            })
          : h('span', { class: 'tag-unavailable', text: 'Indisponível' })
      )
    )
  );
}

// ---------- Personalização ----------

const dlg = $('#product-dialog');
let current = null;
let editIndex = null;
let qty = 1;

function selectedAddons() {
  return [...dlg.querySelectorAll('input[name="addon"]:checked')].map((i) => Number(i.value));
}

function selectedOptions() {
  return [...dlg.querySelectorAll('#pd-options input:checked')].map((i) => Number(i.value));
}

function optionPrice(p, ids) {
  const all = (p.optionGroups || []).flatMap((g) => g.choices);
  return ids.reduce((s, id) => s + (all.find((c) => c.id === id)?.priceCents || 0), 0);
}

function missingRequired(p, ids) {
  return (p.optionGroups || []).filter((g) => g.required && !g.choices.some((c) => ids.includes(c.id)));
}

function updateProductTotal() {
  if (!current) return;
  const addons = selectedAddons().map((id) => current.addons.find((a) => a.id === id));
  const unit = current.priceCents + optionPrice(current, selectedOptions()) + addons.reduce((s, a) => s + (a?.priceCents || 0), 0);
  $('#pd-qty').textContent = String(qty);
  $('#pd-minus').disabled = qty <= 1;
  $('#pd-plus').disabled = qty >= cart.MAX_QTY;
  $('#pd-submit').textContent = `${editIndex === null ? 'Adicionar ao carrinho' : 'Salvar alterações'} · ${money(unit * qty)}`;
}

/** Em grupos de escolha múltipla com limite, bloqueia as demais ao atingir o máximo. */
function enforceMax(fieldset) {
  const max = Number(fieldset.dataset.max) || 0;
  if (fieldset.dataset.kind !== 'multi' || !max) return;
  const boxes = [...fieldset.querySelectorAll('input[type="checkbox"]')];
  const checked = boxes.filter((b) => b.checked).length;
  for (const b of boxes) if (!b.checked) b.disabled = checked >= max || b.dataset.unavailable === '1';
}

function renderOptionGroups(p, selected) {
  const box = $('#pd-options');
  box.textContent = '';
  for (const g of p.optionGroups || []) {
    const hint = g.required
      ? h('span', { class: 'req-badge', text: g.kind === 'multi' && g.maxChoices ? `Obrigatório · até ${g.maxChoices}` : 'Obrigatório' })
      : h('span', { class: 'hint', text: g.kind === 'multi' && g.maxChoices ? ` (opcional, até ${g.maxChoices})` : ' (opcional)' });
    const fs = h(
      'fieldset',
      { class: 'option-group', dataset: { kind: g.kind, max: String(g.maxChoices || ''), group: String(g.id) } },
      h('legend', {}, g.name, ' ', hint)
    );
    // Nada vem marcado: o cliente escolhe (como nos apps de delivery); obrigatórios são cobrados ao adicionar.
    for (const c of g.choices) {
      const checked = selected ? selected.includes(c.id) : false;
      fs.append(
        h(
          'label',
          { class: 'choice' },
          h('input', {
            type: g.kind === 'single' ? 'radio' : 'checkbox',
            name: `opt-${g.id}`,
            value: String(c.id),
            checked,
            disabled: !c.available,
            dataset: { unavailable: c.available ? '0' : '1' },
            onchange: () => {
              enforceMax(fs);
              fs.classList.remove('has-error');
              $('#pd-error').textContent = '';
              updateProductTotal();
            },
          }),
          h('span', { text: c.name }),
          h('span', { class: 'choice-extra', text: !c.available ? 'Indisponível' : c.priceCents ? `+ ${money(c.priceCents)}` : '' })
        )
      );
    }
    box.append(fs);
    enforceMax(fs);
  }
}

function openProduct(p, edit = null) {
  current = p;
  editIndex = edit ? edit.index : null;
  qty = edit ? edit.item.quantity : 1;
  $('#pd-title').textContent = p.name;
  $('#pd-desc').textContent = p.description || '';
  $('#pd-error').textContent = '';
  const media = $('#pd-media');
  media.textContent = '';
  if (p.image) {
    // sem foto, o diálogo não repete o aviso "Foto em breve" já mostrado no cartão
    const m = productImage(p, { sizes: '560px', eager: true });
    m.className = 'dialog-media';
    media.append(m);
  }
  renderOptionGroups(p, edit ? edit.item.optionIds : null);
  const list = $('#pd-addons');
  list.textContent = '';
  $('#pd-addons-box').hidden = p.addons.length === 0;
  for (const a of p.addons) {
    list.append(
      h(
        'label',
        { class: 'choice' },
        h('input', {
          type: 'checkbox',
          name: 'addon',
          value: String(a.id),
          checked: edit ? edit.item.addonIds.includes(a.id) : false,
          disabled: !a.available,
          onchange: updateProductTotal,
        }),
        h('span', { text: a.name }),
        h('span', { class: 'choice-extra', text: a.available ? `+ ${money(a.priceCents)}` : 'Indisponível' })
      )
    );
  }
  $('#pd-notes').value = edit ? edit.item.notes : '';
  $('#pd-notes-count').textContent = `${$('#pd-notes').value.length}/140`;
  updateProductTotal();
  if (!dlg.open) dlg.showModal();
}

$('#pd-minus').addEventListener('click', () => {
  qty = Math.max(1, qty - 1);
  updateProductTotal();
});
$('#pd-plus').addEventListener('click', () => {
  qty = Math.min(cart.MAX_QTY, qty + 1);
  updateProductTotal();
});
$('#pd-notes').addEventListener('input', (e) => {
  $('#pd-notes-count').textContent = `${e.target.value.length}/140`;
});
$('#product-form').addEventListener('submit', (e) => {
  e.preventDefault();
  if (!current) return;
  const optionIds = selectedOptions();
  const missing = missingRequired(current, optionIds);
  if (missing.length) {
    $('#pd-error').textContent = `Escolha: ${missing.map((g) => g.name).join(', ')}.`;
    const fs = dlg.querySelector(`.option-group[data-group="${missing[0].id}"]`);
    fs?.classList.add('has-error');
    fs?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    fs?.querySelector('input:not(:disabled)')?.focus();
    return;
  }
  const item = { productId: current.id, optionIds, addonIds: selectedAddons(), quantity: qty, notes: $('#pd-notes').value.trim() };
  if (editIndex === null) {
    cart.add(item);
    toast(`${current.name} adicionado ao carrinho.`);
  } else {
    cart.replace(editIndex, item);
    toast('Item atualizado.');
  }
  dlg.close();
  if (editIndex !== null) cartDlg.showModal();
  editIndex = null;
});

// ---------- Carrinho ----------

const cartDlg = $('#cart-dialog');

function lineInfo(item) {
  const p = productsById.get(item.productId);
  if (!p) return { problem: 'Este item não está mais no cardápio.', name: 'Item indisponível', unit: 0, addons: [], options: [] };
  const addons = item.addonIds.map((id) => p.addons.find((a) => a.id === id));
  const allChoices = (p.optionGroups || []).flatMap((g) => g.choices);
  const options = item.optionIds.map((id) => allChoices.find((c) => c.id === id));
  let problem = null;
  let canEdit = true;
  if (!p.available) {
    problem = 'Indisponível no momento.';
    canEdit = false;
  } else if (addons.some((a) => !a || !a.available)) problem = 'Um adicional não está mais disponível. Edite o item.';
  else if (options.some((o) => !o || !o.available)) problem = 'Uma opção não está mais disponível. Edite o item.';
  else {
    const missing = missingRequired(p, item.optionIds);
    if (missing.length) problem = `Escolha: ${missing.map((g) => g.name).join(', ')}.`;
  }
  const unit =
    p.priceCents + options.reduce((s, o) => s + (o?.priceCents || 0), 0) + addons.reduce((s, a) => s + (a?.priceCents || 0), 0);
  return { product: p, problem, canEdit, name: p.name, unit, addons: addons.filter(Boolean), options: options.filter(Boolean) };
}

function renderCart() {
  const items = cart.items();
  $('#cart-count').textContent = String(cart.count());
  const list = $('#cart-list');
  list.textContent = '';
  $('#cart-empty').hidden = items.length > 0;
  $('#cart-footer').hidden = items.length === 0;
  if (!menu) return;
  let subtotal = 0;
  let problems = 0;
  items.forEach((item, index) => {
    const info = lineInfo(item);
    if (info.problem) problems++;
    subtotal += info.unit * item.quantity;
    const details = [
      info.options.length ? optionsText(info.options) : null,
      info.addons.length ? `Adicionais: ${info.addons.map((a) => a.name).join(', ')}` : null,
      item.notes ? `Obs.: ${item.notes}` : null,
    ].filter(Boolean);
    list.append(
      h(
        'li',
        { class: `cart-item${info.problem ? ' has-problem' : ''}` },
        h('div', { class: 'cart-item-top' }, h('span', { class: 'cart-item-name', text: info.name }), h('span', { text: money(info.unit * item.quantity) })),
        details.map((d) => h('p', { class: 'cart-item-meta', text: d })),
        info.problem ? h('p', { class: 'field-error', text: info.problem }) : null,
        h(
          'div',
          { class: 'cart-item-actions' },
          h(
            'div',
            { class: 'stepper', role: 'group', 'aria-label': `Quantidade de ${info.name}` },
            h(
              'button',
              { class: 'icon-btn', type: 'button', 'aria-label': 'Diminuir', onclick: () => cart.setQuantity(index, item.quantity - 1) },
              icon('minus')
            ),
            h('span', { class: 'qty', text: String(item.quantity) }),
            h(
              'button',
              {
                class: 'icon-btn',
                type: 'button',
                'aria-label': 'Aumentar',
                disabled: item.quantity >= cart.MAX_QTY,
                onclick: () => cart.setQuantity(index, item.quantity + 1),
              },
              icon('plus')
            )
          ),
          h(
            'div',
            { class: 'cart-item-buttons' },
            info.product && info.canEdit
              ? h('button', {
                  class: 'btn btn-secondary btn-small',
                  type: 'button',
                  text: 'Editar',
                  'aria-label': `Editar ${info.name}`,
                  onclick: () => {
                    cartDlg.close();
                    openProduct(info.product, { index, item });
                  },
                })
              : null,
            h('button', { class: 'btn btn-danger btn-small', type: 'button', onclick: () => cart.remove(index) }, icon('trash'), 'Remover')
          )
        )
      )
    );
  });
  $('#cart-subtotal').textContent = money(subtotal);
  const alert = $('#cart-alert');
  const blocked = problems > 0 || !menu.store.acceptingOrders;
  alert.textContent = problems
    ? 'Ajuste os itens destacados para continuar.'
    : !menu.store.acceptingOrders
      ? menu.store.closedMessage || 'A loja está fechada no momento.'
      : '';
  const go = $('#go-checkout');
  go.setAttribute('aria-disabled', String(blocked));
  go.tabIndex = blocked ? -1 : 0;
}

$('#go-checkout').addEventListener('click', (e) => {
  if (e.currentTarget.getAttribute('aria-disabled') === 'true') e.preventDefault();
});

$('#open-cart').addEventListener('click', () => {
  renderCart();
  cartDlg.showModal();
});

for (const d of [dlg, cartDlg]) {
  d.addEventListener('click', (e) => {
    if (e.target === d || e.target.closest('[data-close]')) d.close();
  });
}
dlg.addEventListener('close', () => {
  editIndex = null;
});

cart.subscribe(renderCart);
renderCart();
loadMenu();
