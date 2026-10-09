// Painel administrativo: login, abas e logout.
import { api, toast } from '../lib.js';
import { createAddonsTab, createCatalogTab } from './catalog.js';
import { adminApi, flash, state } from './core.js';
import { createCouponsTab } from './coupons.js';
import { createOptionsTab } from './options.js';
import { createOrdersTab } from './orders.js';
import { createAccountTab, createSettingsTab } from './settings.js';

const $ = (sel) => document.querySelector(sel);
const views = { boot: $('#boot'), login: $('#login-view'), app: $('#app-view') };
let tabs = null;
let activeTab = 'pedidos';

function show(name) {
  for (const [k, el] of Object.entries(views)) el.hidden = k !== name;
  $('#user-bar').hidden = name !== 'app';
}

function showLogin(message) {
  tabs?.pedidos.stop();
  state.csrfToken = null;
  state.user = null;
  show('login');
  const alert = $('#login-alert');
  alert.textContent = message || '';
  $('#login-email').focus();
}
state.onUnauthorized = (msg) => showLogin(msg);

function enterApp(session) {
  state.csrfToken = session.csrfToken;
  state.user = session.user;
  if (typeof session.imageOptimization === 'boolean') state.imageOptimization = session.imageOptimization;
  $('#user-name').textContent = session.user.name;
  show('app');
  if (!tabs) {
    tabs = {
      pedidos: createOrdersTab($('#tab-pedidos')),
      cardapio: createCatalogTab($('#tab-cardapio')),
      adicionais: createAddonsTab($('#tab-adicionais')),
      opcoes: createOptionsTab($('#tab-opcoes')),
      cupons: createCouponsTab($('#tab-cupons')),
      config: createSettingsTab($('#tab-config')),
      conta: createAccountTab($('#tab-conta')),
    };
  }
  selectTab(activeTab);
}

function selectTab(name) {
  activeTab = name;
  for (const btn of document.querySelectorAll('[role="tab"]')) {
    const on = btn.id === `tab-btn-${name}`;
    btn.setAttribute('aria-selected', String(on));
    btn.tabIndex = on ? 0 : -1;
    document.getElementById(btn.getAttribute('aria-controls')).hidden = !on;
  }
  $('#global-alert').textContent = '';
  if (name === 'pedidos') tabs.pedidos.start();
  else tabs.pedidos.stop();
  tabs[name].start();
}

// navegação por teclado entre abas (setas)
$('.admin-tabs').addEventListener('click', (e) => {
  const btn = e.target.closest('[role="tab"]');
  if (btn) selectTab(btn.id.replace('tab-btn-', ''));
});
$('.admin-tabs').addEventListener('keydown', (e) => {
  if (!['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
  const list = [...document.querySelectorAll('[role="tab"]')];
  const i = list.findIndex((b) => b.getAttribute('aria-selected') === 'true');
  const next = list[(i + (e.key === 'ArrowRight' ? 1 : list.length - 1)) % list.length];
  next.focus();
  selectTab(next.id.replace('tab-btn-', ''));
});

$('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = $('#login-submit');
  const alert = $('#login-alert');
  const email = $('#login-email').value.trim();
  const password = $('#login-password').value;
  if (!email || !password) return flash(alert, 'Informe e-mail e senha.');
  btn.disabled = true;
  btn.textContent = 'Entrando…';
  try {
    const session = await api('/api/admin/login', { body: { email, password } });
    $('#login-password').value = '';
    alert.textContent = '';
    const full = await adminApi('/api/admin/session', { headers: {} }).catch(() => session);
    enterApp({ ...session, ...full, csrfToken: full.csrfToken || session.csrfToken });
  } catch (err) {
    flash(alert, err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Entrar';
  }
});

$('#logout').addEventListener('click', async () => {
  try {
    await adminApi('/api/admin/logout', { method: 'POST', body: {} });
  } catch {
    /* mesmo com erro, volta para o login */
  }
  showLogin('');
  toast('Você saiu do painel.');
});

// Ao abrir: verifica se já existe sessão válida.
(async () => {
  try {
    enterApp(await api('/api/admin/session'));
  } catch {
    showLogin('');
  }
})();
