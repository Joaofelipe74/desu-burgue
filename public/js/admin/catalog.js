// Abas "Cardápio" (categorias e produtos) e "Adicionais".
import { centsToInput, h, money, parseMoneyToCents, toast } from '../lib.js';
import { adminApi, checkbox, field, flash, sectionTitle, state, withBusy } from './core.js';

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_UPLOAD = 5 * 1024 * 1024;

export function createCatalogTab(panel) {
  let categories = [];
  let products = [];
  let addons = [];
  let showArchived = false;

  const alert = h('div', { class: 'alert alert-error', role: 'alert' });
  const catList = h('div', { class: 'data-list' });
  const prodList = h('div', { class: 'data-list' });

  // ----- formulário de nova categoria -----
  const catName = h('input', { type: 'text', maxlength: 60, required: true });
  const catOrder = h('input', { type: 'number', min: 0, max: 9999, value: '0' });
  const catAdd = h('button', { class: 'btn btn-secondary', type: 'submit', text: 'Adicionar categoria' });
  const catForm = h(
    'form',
    { class: 'card', novalidate: true },
    h('div', { class: 'row row-3-1' }, field('Nova categoria', catName), field('Ordem', catOrder)),
    catAdd
  );
  catForm.addEventListener('submit', (e) => {
    e.preventDefault();
    withBusy(
      catAdd,
      async () => {
        await adminApi('/api/admin/categories', { body: { name: catName.value, sortOrder: Number(catOrder.value) || 0, active: true } });
        catName.value = '';
        toast('Categoria criada.');
        await load();
      },
      alert
    );
  });

  const archivedToggle = checkbox('Mostrar arquivados', false, {
    onchange: (e) => {
      showArchived = e.target.checked;
      renderProducts();
    },
  });

  panel.append(
    sectionTitle('Categorias'),
    alert,
    catForm,
    h('div', { class: 'mt-8' }, catList),
    sectionTitle(
      'Produtos',
      archivedToggle.el,
      h('button', { class: 'btn btn-primary', type: 'button', text: 'Novo produto', onclick: () => openEditor(null) })
    ),
    prodList
  );

  async function load() {
    try {
      const [c, p, a] = await Promise.all([
        adminApi('/api/admin/categories'),
        adminApi('/api/admin/products'),
        adminApi('/api/admin/addons'),
      ]);
      categories = c.categories;
      products = p.products;
      addons = a.addons;
      renderCategories();
      renderProducts();
    } catch (err) {
      flash(alert, err.message);
    }
  }

  function renderCategories() {
    catList.textContent = '';
    if (!categories.length) catList.append(h('p', { class: 'state', text: 'Nenhuma categoria ainda.' }));
    for (const c of categories) catList.append(categoryRow(c));
  }

  function categoryRow(c) {
    const row = h('div', { class: 'data-item' });
    const view = () => {
      row.textContent = '';
      const active = checkbox('Ativa', c.active, {
        onchange: (e) =>
          adminApi(`/api/admin/categories/${c.id}`, { method: 'PUT', body: { active: e.target.checked } })
            .then(() => toast(e.target.checked ? 'Categoria ativada.' : 'Categoria oculta do cardápio.'))
            .then(load)
            .catch((err) => flash(alert, err.message)),
      });
      row.append(
        h('div', { class: 'grow' }, h('strong', { text: c.name }), h('div', { class: 'muted small', text: `Ordem ${c.sortOrder} · ${c.productCount} produto(s)` })),
        active.el,
        h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Editar', onclick: edit }),
        h('button', {
          class: 'btn btn-danger btn-small',
          type: 'button',
          text: 'Excluir',
          onclick: (e) => {
            const b = e.currentTarget;
            if (b.dataset.confirm !== '1') {
              b.dataset.confirm = '1';
              b.textContent = 'Confirmar exclusão';
              return;
            }
            withBusy(b, async () => {
              await adminApi(`/api/admin/categories/${c.id}`, { method: 'DELETE' });
              toast('Categoria excluída.');
              await load();
            }, alert);
          },
        })
      );
    };
    const edit = () => {
      row.textContent = '';
      const name = h('input', { type: 'text', value: c.name, maxlength: 60 });
      const order = h('input', { type: 'number', value: String(c.sortOrder), min: 0, max: 9999 });
      const save = h('button', { class: 'btn btn-primary btn-small', type: 'button', text: 'Salvar' });
      save.addEventListener('click', () =>
        withBusy(save, async () => {
          await adminApi(`/api/admin/categories/${c.id}`, { method: 'PUT', body: { name: name.value, sortOrder: Number(order.value) || 0 } });
          toast('Categoria atualizada.');
          await load();
        }, alert)
      );
      row.append(
        h('div', { class: 'grow' }, field('Nome', name)),
        field('Ordem', order),
        save,
        h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Cancelar', onclick: view })
      );
      name.focus();
    };
    view();
    return row;
  }

  function renderProducts() {
    prodList.textContent = '';
    const list = products.filter((p) => showArchived || !p.archived);
    if (!list.length) prodList.append(h('p', { class: 'state', text: 'Nenhum produto.' }));
    for (const p of list) {
      const avail = checkbox('Disponível', p.available, {
        disabled: p.archived,
        onchange: (e) =>
          adminApi(`/api/admin/products/${p.id}`, { method: 'PUT', body: { available: e.target.checked } })
            .then(() => toast(e.target.checked ? `${p.name} disponível.` : `${p.name} marcado como indisponível.`))
            .then(load)
            .catch((err) => flash(alert, err.message)),
      });
      prodList.append(
        h(
          'div',
          { class: `data-item${p.archived ? ' is-archived' : ''}` },
          p.image
            ? h('img', { class: 'thumb', src: p.image.thumbSrc || p.image.src, alt: '', width: 64, height: 48 })
            : h('img', { class: 'thumb', src: '/img/placeholder-produto.svg', alt: '', width: 64, height: 48 }),
          h(
            'div',
            { class: 'grow' },
            h('strong', { text: p.name }),
            h('div', { class: 'muted small', text: `${p.categoryName} · ${money(p.priceCents)}${p.archived ? ' · arquivado' : ''}${p.image ? '' : ' · sem foto'}` })
          ),
          avail.el,
          h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Editar', onclick: () => openEditor(p) })
        )
      );
    }
  }

  // ----- editor de produto (diálogo) -----
  const dlg = document.getElementById('product-editor');
  const peBody = document.getElementById('pe-body');
  const peAlert = document.getElementById('pe-alert');
  const peForm = document.getElementById('pe-form');
  const peSave = document.getElementById('pe-save');
  let editing = null;
  let inputs = {};

  dlg.addEventListener('click', (e) => {
    if (e.target === dlg || e.target.closest('[data-close]')) dlg.close();
  });

  function openEditor(p) {
    editing = p;
    peAlert.textContent = '';
    document.getElementById('pe-title').textContent = p ? `Editar: ${p.name}` : 'Novo produto';
    peBody.textContent = '';
    if (!categories.length) {
      flash(alert, 'Crie uma categoria antes de cadastrar produtos.');
      return;
    }
    inputs = {
      name: h('input', { type: 'text', maxlength: 80, value: p?.name || '' }),
      categoryId: h(
        'select',
        {},
        categories.map((c) => h('option', { value: String(c.id), text: c.name, selected: p ? p.categoryId === c.id : false }))
      ),
      description: h('textarea', { maxlength: 300, rows: 3 }),
      price: h('input', { type: 'text', inputmode: 'decimal', placeholder: '24,90', value: p ? centsToInput(p.priceCents) : '' }),
      sortOrder: h('input', { type: 'number', min: 0, max: 9999, value: String(p?.sortOrder ?? 0) }),
      available: checkbox('Disponível para pedidos', p ? p.available : true),
      imageAlt: h('input', { type: 'text', maxlength: 160, value: p?.imageAlt || '' }),
      isReal: checkbox('É foto real deste produto (desmarcado = mostra "Imagem ilustrativa")', p ? !p.imageIsIllustrative : false),
      file: h('input', { type: 'file', accept: ACCEPTED.join(',') }),
    };
    inputs.description.value = p?.description || '';

    const preview = h('img', {
      class: 'image-preview',
      alt: 'Pré-visualização da imagem',
      src: p?.image ? p.image.thumbSrc || p.image.src : '/img/placeholder-produto.svg',
    });
    inputs.file.addEventListener('change', () => {
      const f = inputs.file.files[0];
      peAlert.textContent = '';
      if (!f) return;
      if (!ACCEPTED.includes(f.type)) {
        flash(peAlert, 'Formato não aceito. Use JPG, PNG ou WebP.');
        inputs.file.value = '';
        return;
      }
      if (f.size > MAX_UPLOAD) {
        flash(peAlert, 'Imagem acima de 5 MB. Reduza o arquivo antes de enviar.');
        inputs.file.value = '';
        return;
      }
      preview.src = URL.createObjectURL(f);
    });

    const addonBoxes = addons
      .filter((a) => !a.archived)
      .map((a) => {
        const cb = checkbox(`${a.name} (+ ${money(a.priceCents)})`, p?.addonIds.includes(a.id), { value: String(a.id), name: 'pe-addon' });
        return cb.el;
      });

    const imageActions = h('div', { class: 'toolbar' });
    if (p?.image) {
      const rm = h('button', { class: 'btn btn-danger btn-small', type: 'button', text: 'Remover imagem' });
      rm.addEventListener('click', () =>
        withBusy(rm, async () => {
          await adminApi(`/api/admin/products/${p.id}/image`, { method: 'DELETE' });
          toast('Imagem removida.');
          dlg.close();
          await load();
        }, peAlert)
      );
      imageActions.append(rm);
    }
    if (p) {
      const arch = h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: p.archived ? 'Restaurar produto' : 'Arquivar produto' });
      arch.addEventListener('click', () =>
        withBusy(arch, async () => {
          await adminApi(`/api/admin/products/${p.id}`, { method: 'PUT', body: { archived: !p.archived } });
          toast(p.archived ? 'Produto restaurado.' : 'Produto arquivado (não aparece no cardápio).');
          dlg.close();
          await load();
        }, peAlert)
      );
      imageActions.append(arch);
    }

    peBody.append(
      field('Nome', inputs.name),
      h('div', { class: 'row row-2' }, field('Categoria', inputs.categoryId), field('Preço (R$)', inputs.price)),
      field('Descrição', inputs.description, 'até 300 caracteres'),
      h('div', { class: 'row row-2' }, field('Ordem no cardápio', inputs.sortOrder), h('div', { class: 'field' }, inputs.available.el)),
      h(
        'fieldset',
        {},
        h('legend', { text: 'Adicionais permitidos' }),
        addonBoxes.length ? h('div', { class: 'checkbox-grid' }, addonBoxes) : h('p', { class: 'muted small', text: 'Nenhum adicional cadastrado (aba Adicionais).' })
      ),
      h(
        'fieldset',
        {},
        h('legend', { text: 'Imagem' }),
        preview,
        field('Enviar nova imagem', inputs.file, 'JPG, PNG ou WebP, até 5 MB'),
        h('p', {
          class: 'hint',
          text: state.imageOptimization
            ? 'A imagem será otimizada automaticamente (WebP, sem cortar).'
            : 'Otimização automática desligada no servidor: prefira imagens com até 1200 px e 3 MB.',
        }),
        field('Texto alternativo (descreve a imagem)', inputs.imageAlt, 'ex.: X-Bacon com queijo derretido'),
        inputs.isReal.el,
        imageActions
      )
    );
    dlg.showModal();
    inputs.name.focus();
  }

  peForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const priceCents = parseMoneyToCents(inputs.price.value);
    if (priceCents === null) {
      flash(peAlert, 'Preço inválido. Use o formato 24,90.');
      inputs.price.focus();
      return;
    }
    const body = {
      name: inputs.name.value,
      categoryId: Number(inputs.categoryId.value),
      description: inputs.description.value,
      priceCents,
      sortOrder: Number(inputs.sortOrder.value) || 0,
      available: inputs.available.input.checked,
      imageAlt: inputs.imageAlt.value,
      imageIsIllustrative: !inputs.isReal.input.checked,
      addonIds: [...peBody.querySelectorAll('input[name="pe-addon"]:checked')].map((i) => Number(i.value)),
    };
    withBusy(
      peSave,
      async () => {
        let id = editing?.id;
        if (id) await adminApi(`/api/admin/products/${id}`, { method: 'PUT', body });
        else id = (await adminApi('/api/admin/products', { body })).id;
        const file = inputs.file.files[0];
        if (file) {
          const r = await adminApi(`/api/admin/products/${id}/image`, { method: 'PUT', raw: file, timeoutMs: 60000 });
          toast(r.optimized ? 'Produto e imagem salvos (imagem otimizada).' : 'Produto e imagem salvos.');
        } else {
          toast('Produto salvo.');
        }
        dlg.close();
        await load();
      },
      peAlert
    );
  });

  return { start: load };
}

export function createAddonsTab(panel) {
  let addons = [];
  const alert = h('div', { class: 'alert alert-error', role: 'alert' });
  const list = h('div', { class: 'data-list' });
  const name = h('input', { type: 'text', maxlength: 60 });
  const price = h('input', { type: 'text', inputmode: 'decimal', placeholder: '4,00' });
  const add = h('button', { class: 'btn btn-secondary', type: 'submit', text: 'Adicionar' });
  const form = h(
    'form',
    { class: 'card', novalidate: true },
    h('p', { class: 'muted small', text: 'Cadastre aqui os adicionais e depois escolha em cada produto quais ele aceita.' }),
    h('div', { class: 'row row-3-1' }, field('Nome do adicional', name), field('Preço (R$)', price)),
    add
  );
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const cents = parseMoneyToCents(price.value);
    if (cents === null) return flash(alert, 'Preço inválido. Use o formato 4,00.');
    withBusy(add, async () => {
      await adminApi('/api/admin/addons', { body: { name: name.value, priceCents: cents, available: true } });
      name.value = '';
      price.value = '';
      toast('Adicional criado.');
      await load();
    }, alert);
  });
  panel.append(sectionTitle('Adicionais'), alert, form, h('div', { class: 'mt-8' }, list));

  async function load() {
    try {
      addons = (await adminApi('/api/admin/addons')).addons;
      render();
    } catch (err) {
      flash(alert, err.message);
    }
  }

  function render() {
    list.textContent = '';
    if (!addons.length) list.append(h('p', { class: 'state', text: 'Nenhum adicional cadastrado.' }));
    for (const a of addons) {
      const row = h('div', { class: `data-item${a.archived ? ' is-archived' : ''}` });
      const update = (body, msg) =>
        adminApi(`/api/admin/addons/${a.id}`, { method: 'PUT', body })
          .then(() => toast(msg))
          .then(load)
          .catch((err) => flash(alert, err.message));
      const view = () => {
        row.textContent = '';
        row.append(
          h('div', { class: 'grow' }, h('strong', { text: a.name }), h('div', { class: 'muted small', text: `${money(a.priceCents)}${a.archived ? ' · arquivado' : ''}` })),
          checkbox('Disponível', a.available, { disabled: a.archived, onchange: (e) => update({ available: e.target.checked }, 'Adicional atualizado.') }).el,
          h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Editar', onclick: edit }),
          h('button', {
            class: 'btn btn-secondary btn-small',
            type: 'button',
            text: a.archived ? 'Restaurar' : 'Arquivar',
            onclick: () => update({ archived: !a.archived }, a.archived ? 'Adicional restaurado.' : 'Adicional arquivado.'),
          })
        );
      };
      const edit = () => {
        row.textContent = '';
        const n = h('input', { type: 'text', value: a.name, maxlength: 60 });
        const p = h('input', { type: 'text', inputmode: 'decimal', value: centsToInput(a.priceCents) });
        const save = h('button', { class: 'btn btn-primary btn-small', type: 'button', text: 'Salvar' });
        save.addEventListener('click', () => {
          const cents = parseMoneyToCents(p.value);
          if (cents === null) return flash(alert, 'Preço inválido.');
          withBusy(save, () => update({ name: n.value, priceCents: cents }, 'Adicional atualizado.'), alert);
        });
        row.append(h('div', { class: 'grow' }, field('Nome', n)), field('Preço (R$)', p), save, h('button', { class: 'btn btn-secondary btn-small', type: 'button', text: 'Cancelar', onclick: view }));
      };
      view();
      list.append(row);
    }
  }

  return { start: load };
}
