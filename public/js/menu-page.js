// Página do cardápio: lista produtos, personalização e carrinho.
import { cart } from './cart.js';
import { api, h, icon, money, productImage, toast } from './lib.js';

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
  if (s.contactPhone) {
    const fc = $('#footer-contact');
    fc.hidden = false;
    fc.textContent = `Contato: ${s.contactPhone}`;
  }
}

function renderMenu() {
  const root = $('#menu');
  const status = $('#menu-status');
  const nav = $('#category-nav');
  root.textContent = '';
  nav.textContent = '';
  if (menu.categories.length === 0) {
    status.textContent = 'O cardápio está sendo atualizado. Volte em breve!';
    return;
  }
  status.textContent = '';
  nav.hidden = menu.categories.length < 2;
  for (const cat of menu.categories) {
    const id = `categoria-${cat.id}`;
    nav.append(h('a', { href: `#${id}`, text: cat.name }));
    root.append(
      h(
        'section',
        { class: 'menu-section', id, 'aria-labelledby': `${id}-t` },
        h('h3', { id: `${id}-t`, class: menu.categories.length > 1 ? 'category-title' : 'visually-hidden', text: cat.name }),
        h('div', { class: 'product-grid' }, cat.products.map(productCard))
      )
    );
  }
}

function productCard(p) {
  const canOrder = p.available && menu.store.acceptingOrders;
  return h(
    'article',
    { class: `product-card${p.available ? '' : ' is-unavailable'}`, 'aria-labelledby': `p-${p.id}` },
    productImage(p),
    h(
      'div',
      { class: 'product-body' },
      h('h4', { id: `p-${p.id}`, class: 'product-name', text: p.name }),
      p.description ? h('p', { class: 'product-desc', text: p.description }) : h('p', { class: 'product-desc' }),
      h(
        'div',
        { class: 'product-footer' },
        h('span', { class: 'price', text: money(p.priceCents) }),
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
let qty = 1;

function selectedAddons() {
  return [...dlg.querySelectorAll('input[name="addon"]:checked')].map((i) => Number(i.value));
}

function updateProductTotal() {
  if (!current) return;
  const addons = selectedAddons().map((id) => current.addons.find((a) => a.id === id));
  const unit = current.priceCents + addons.reduce((s, a) => s + (a?.priceCents || 0), 0);
  $('#pd-qty').textContent = String(qty);
  $('#pd-minus').disabled = qty <= 1;
  $('#pd-plus').disabled = qty >= cart.MAX_QTY;
  $('#pd-submit').textContent = `Adicionar ao carrinho · ${money(unit * qty)}`;
}

function openProduct(p) {
  current = p;
  qty = 1;
  $('#pd-title').textContent = p.name;
  $('#pd-desc').textContent = p.description || '';
  const media = $('#pd-media');
  media.textContent = '';
  if (p.image) {
    // sem foto, o diálogo não repete o aviso "Foto em breve" já mostrado no cartão
    const m = productImage(p, { sizes: '560px', eager: true });
    m.className = 'dialog-media';
    media.append(m);
  }
  const list = $('#pd-addons');
  list.textContent = '';
  $('#pd-addons-box').hidden = p.addons.length === 0;
  for (const a of p.addons) {
    list.append(
      h(
        'label',
        { class: 'choice' },
        h('input', { type: 'checkbox', name: 'addon', value: String(a.id), disabled: !a.available, onchange: updateProductTotal }),
        h('span', { text: a.name }),
        h('span', { class: 'choice-extra', text: a.available ? `+ ${money(a.priceCents)}` : 'Indisponível' })
      )
    );
  }
  $('#pd-notes').value = '';
  $('#pd-notes-count').textContent = '0/140';
  updateProductTotal();
  dlg.showModal();
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
  cart.add({ productId: current.id, addonIds: selectedAddons(), quantity: qty, notes: $('#pd-notes').value.trim() });
  dlg.close();
  toast(`${current.name} adicionado ao carrinho.`);
});

// ---------- Carrinho ----------

const cartDlg = $('#cart-dialog');

function lineInfo(item) {
  const p = productsById.get(item.productId);
  if (!p) return { problem: 'Este item não está mais no cardápio.', name: 'Item indisponível', unit: 0, addons: [] };
  const addons = item.addonIds.map((id) => p.addons.find((a) => a.id === id));
  let problem = null;
  if (!p.available) problem = 'Indisponível no momento.';
  else if (addons.some((a) => !a || !a.available)) problem = 'Um adicional não está mais disponível.';
  const unit = p.priceCents + addons.reduce((s, a) => s + (a?.priceCents || 0), 0);
  return { problem, name: p.name, unit, addons: addons.filter(Boolean) };
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
            h('button', {
              class: 'icon-btn',
              type: 'button',
              'aria-label': 'Diminuir',
              onclick: () => cart.setQuantity(index, item.quantity - 1),
            }, icon('minus')),
            h('span', { class: 'qty', text: String(item.quantity) }),
            h('button', {
              class: 'icon-btn',
              type: 'button',
              'aria-label': 'Aumentar',
              disabled: item.quantity >= cart.MAX_QTY,
              onclick: () => cart.setQuantity(index, item.quantity + 1),
            }, icon('plus'))
          ),
          h('button', { class: 'btn btn-danger btn-small', type: 'button', onclick: () => cart.remove(index) }, icon('trash'), 'Remover')
        )
      )
    );
  });
  $('#cart-subtotal').textContent = money(subtotal);
  const alert = $('#cart-alert');
  const blocked = problems > 0 || !menu.store.acceptingOrders;
  alert.textContent = problems
    ? 'Remova os itens indisponíveis para continuar.'
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

cart.subscribe(renderCart);
renderCart();
loadMenu();
