// Abas "Configurações" e "Minha conta".
import { centsToInput, h, parseMoneyToCents, toast } from '../lib.js';
import { adminApi, checkbox, field, flash, sectionTitle, state, withBusy } from './core.js';

export function createSettingsTab(panel) {
  const alert = h('div', { class: 'alert alert-error', role: 'alert' });
  const form = h('form', { class: 'card', novalidate: true });
  panel.append(sectionTitle('Configurações da loja'), alert, form);

  async function load() {
    let s;
    try {
      s = (await adminApi('/api/admin/settings')).settings;
    } catch (err) {
      return flash(alert, err.message);
    }
    form.textContent = '';
    const i = {
      storeName: h('input', { type: 'text', maxlength: 60, value: s.store_name }),
      accepting: checkbox('Loja aberta para pedidos', s.accepting_orders),
      closedMessage: h('input', { type: 'text', maxlength: 200, value: s.closed_message }),
      pickup: checkbox('Aceitar retirada no local', s.pickup_enabled),
      pickupAddress: h('input', { type: 'text', maxlength: 200, value: s.pickup_address }),
      delivery: checkbox('Fazer entregas', s.delivery_enabled),
      fee: h('input', { type: 'text', inputmode: 'decimal', value: centsToInput(s.delivery_fee_cents) }),
      minOrder: h('input', { type: 'text', inputmode: 'decimal', value: centsToInput(s.min_order_cents) }),
      dinheiro: checkbox('Dinheiro', s.payment_methods.dinheiro),
      cartao: checkbox('Cartão (maquininha na entrega/retirada)', s.payment_methods.cartao),
      pix: checkbox('Pix (na entrega/retirada)', s.payment_methods.pix),
      phone: h('input', { type: 'text', maxlength: 30, value: s.contact_phone }),
      whatsapp: h('input', { type: 'tel', inputmode: 'tel', maxlength: 20, placeholder: '(11) 91234-5678', value: s.whatsapp }),
      hours: h('input', { type: 'text', maxlength: 120, placeholder: 'Ex.: Terça a domingo, das 18h às 23h', value: s.opening_hours }),
      about: h('textarea', { maxlength: 400, rows: 3 }),
    };
    i.about.value = s.about_text;
    const save = h('button', { class: 'btn btn-primary', type: 'submit', text: 'Salvar configurações' });
    form.append(
      field('Nome da loja', i.storeName),
      h('fieldset', {}, h('legend', { text: 'Funcionamento' }), h('div', { class: 'field' }, i.accepting.el), field('Mensagem quando fechada', i.closedMessage)),
      h(
        'fieldset',
        {},
        h('legend', { text: 'Retirada e entrega' }),
        h('div', { class: 'field' }, i.pickup.el),
        field('Endereço para retirada', i.pickupAddress, 'aparece para o cliente'),
        h('div', { class: 'field' }, i.delivery.el),
        h('div', { class: 'row row-2' }, field('Taxa de entrega (R$)', i.fee), field('Pedido mínimo (R$)', i.minOrder, '0 = sem mínimo'))
      ),
      h(
        'fieldset',
        {},
        h('legend', { text: 'Formas de pagamento (na entrega/retirada)' }),
        h('p', { class: 'muted small', text: 'O site não faz cobranças online. Estas opções só informam como o cliente vai pagar.' }),
        h('div', { class: 'field' }, i.dinheiro.el),
        h('div', { class: 'field' }, i.cartao.el),
        h('div', { class: 'field' }, i.pix.el)
      ),
      h(
        'fieldset',
        {},
        h('legend', { text: 'Página inicial e contato' }),
        field('Horário de funcionamento', i.hours, 'aparece no topo e no rodapé'),
        field('Texto "Sobre"', i.about, 'até 400 caracteres'),
        h('div', { class: 'row row-2' }, field('Telefone de contato', i.phone, 'opcional'), field('WhatsApp (com DDD)', i.whatsapp, 'opcional; cria o botão "Falar no WhatsApp"'))
      ),
      save
    );
    form.onsubmit = (e) => {
      e.preventDefault();
      const fee = parseMoneyToCents(i.fee.value);
      const min = parseMoneyToCents(i.minOrder.value);
      if (fee === null || min === null) return flash(alert, 'Valores em reais inválidos. Use o formato 5,00.');
      withBusy(save, async () => {
        await adminApi('/api/admin/settings', {
          method: 'PUT',
          body: {
            store_name: i.storeName.value,
            accepting_orders: i.accepting.input.checked,
            closed_message: i.closedMessage.value,
            pickup_enabled: i.pickup.input.checked,
            pickup_address: i.pickupAddress.value,
            delivery_enabled: i.delivery.input.checked,
            delivery_fee_cents: fee,
            min_order_cents: min,
            payment_methods: { dinheiro: i.dinheiro.input.checked, cartao: i.cartao.input.checked, pix: i.pix.input.checked },
            contact_phone: i.phone.value,
            whatsapp: i.whatsapp.value.trim(),
            opening_hours: i.hours.value,
            about_text: i.about.value,
          },
        });
        alert.textContent = '';
        toast('Configurações salvas.');
        document.querySelectorAll('[data-store-name]').forEach((el) => (el.textContent = i.storeName.value));
      }, alert);
    };
  }

  return { start: load };
}

export function createAccountTab(panel) {
  const alert = h('div', { class: 'alert', role: 'status' });
  const current = h('input', { type: 'password', autocomplete: 'current-password', maxlength: 512 });
  const next = h('input', { type: 'password', autocomplete: 'new-password', maxlength: 512 });
  const confirm = h('input', { type: 'password', autocomplete: 'new-password', maxlength: 512 });
  const save = h('button', { class: 'btn btn-primary', type: 'submit', text: 'Trocar senha' });
  const form = h(
    'form',
    { class: 'card', novalidate: true },
    h('h3', { text: 'Trocar senha' }),
    field('Senha atual', current),
    field('Nova senha', next, 'mínimo de 15 caracteres; uma frase é ótima'),
    field('Repita a nova senha', confirm),
    alert,
    save
  );
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (next.value !== confirm.value) return flash(alert, 'As senhas novas não conferem.');
    withBusy(save, async () => {
      const r = await adminApi('/api/admin/password', { body: { currentPassword: current.value, newPassword: next.value } });
      state.csrfToken = r.csrfToken;
      form.reset();
      flash(alert, 'Senha alterada. As outras sessões abertas foram encerradas.', 'success');
    }, alert);
  });
  panel.append(sectionTitle('Minha conta'), h('p', { class: 'muted', text: '' }), form);
  return {
    start() {
      panel.querySelector('p.muted').textContent = state.user ? `Conectado como ${state.user.name} (${state.user.email}).` : '';
    },
  };
}
