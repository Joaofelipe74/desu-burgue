// Cardápio de EXEMPLO com preços sugeridos (pedido do dono em 02/10/2026).
// É aplicado uma única vez em cada banco. Tudo pode ser editado, desativado
// ou arquivado no painel (/admin/ → Cardápio, Adicionais e Configurações).
// Revise os preços antes de usar com clientes reais.
import { transaction } from './db.js';

export const SAMPLE_FLAG = '_cardapio_exemplo_v1';

const ADDONS = [
  ['Bacon extra', 400],
  ['Cheddar extra', 350],
  ['Ovo', 250],
  ['Carne extra (150 g)', 700],
  ['Cebola caramelizada', 300],
  ['Catupiry', 400],
  ['Molho especial', 200],
];

const BURGER_ADDONS = ADDONS.map(([n]) => n);
const VEGGIE_ADDONS = ['Cheddar extra', 'Ovo', 'Cebola caramelizada', 'Catupiry', 'Molho especial'];
const CHICKEN_ADDONS = ['Bacon extra', 'Cheddar extra', 'Ovo', 'Cebola caramelizada', 'Catupiry', 'Molho especial'];
const FRIES_ADDONS = ['Cheddar extra', 'Bacon extra', 'Catupiry', 'Molho especial'];
const COMBO_ADDONS = ['Bacon extra', 'Cheddar extra', 'Molho especial'];

// [categoria, ordem, produtos: [nome, descrição, preço em centavos, ilustração, destaque, adicionais]]
const MENU = [
  ['Hambúrgueres', 1, [
    ['X-Bacon', 'Pão, carne, queijo e bacon crocante.', 2490, 'hamburguer-bacon', true, BURGER_ADDONS],
    ['X-Burguer', 'Pão, carne de 150 g, queijo e molho da casa.', 1990, 'hamburguer', false, BURGER_ADDONS],
    ['X-Salada', 'Pão, carne de 150 g, queijo, alface, tomate e maionese.', 2190, 'hamburguer-salada', false, BURGER_ADDONS],
    ['X-Egg', 'Pão, carne de 150 g, queijo, ovo, alface e tomate.', 2290, 'hamburguer-ovo', false, BURGER_ADDONS],
    ['X-Tudo', 'Pão, duas carnes, queijo, bacon, ovo, presunto, alface, tomate e molho da casa.', 3290, 'hamburguer-tudo', true, BURGER_ADDONS],
    ['Desu Smash Duplo', 'Pão brioche, duas carnes smash, cheddar duplo e cebola caramelizada.', 2990, 'smash-duplo', true, BURGER_ADDONS],
    ['Chicken Crispy', 'Pão brioche, frango empanado crocante, alface, tomate e maionese temperada.', 2590, 'frango', false, CHICKEN_ADDONS],
    ['Veggie', 'Pão, hambúrguer de grão-de-bico, queijo, rúcula, tomate e molho de ervas.', 2690, 'veggie', false, VEGGIE_ADDONS],
  ]],
  ['Combos', 2, [
    ['Combo X-Bacon', 'X-Bacon + batata frita pequena + refrigerante lata.', 3690, 'combo', true, COMBO_ADDONS],
    ['Combo Smash', 'Desu Smash Duplo + batata frita pequena + refrigerante lata.', 4190, 'combo', false, COMBO_ADDONS],
    ['Combo Família', '4 X-Burguer + batata frita grande + refrigerante 2 L.', 9990, 'combo-familia', false, COMBO_ADDONS],
  ]],
  ['Porções', 3, [
    ['Batata frita pequena', 'Porção de 200 g, sequinha e crocante.', 1290, 'batata', false, FRIES_ADDONS],
    ['Batata frita grande', 'Porção de 400 g para dividir.', 1990, 'batata', false, FRIES_ADDONS],
    ['Batata cheddar e bacon', 'Batata frita coberta com cheddar cremoso e bacon.', 2690, 'batata-cheddar', false, []],
    ['Onion rings', '10 anéis de cebola empanados.', 1890, 'onion-rings', false, ['Molho especial']],
    ['Nuggets', '10 unidades com molho à escolha (informe na observação).', 1790, 'nuggets', false, ['Molho especial']],
  ]],
  ['Bebidas', 4, [
    ['Refrigerante lata', 'Lata de 350 ml. Informe o sabor na observação.', 650, 'refrigerante-lata', false, []],
    ['Refrigerante 2 L', 'Garrafa de 2 litros. Informe o sabor na observação.', 1490, 'refrigerante-2l', false, []],
    ['Suco natural', 'Copo de 400 ml: laranja, limão ou maracujá (informe na observação).', 990, 'suco', false, []],
    ['Água mineral', 'Garrafa de 500 ml, com ou sem gás.', 400, 'agua', false, []],
    ['Milk-shake', 'Copo de 400 ml: chocolate, morango ou baunilha (informe na observação).', 1690, 'milkshake', false, []],
  ]],
  ['Sobremesas', 5, [
    ['Brownie com sorvete', 'Brownie de chocolate com uma bola de sorvete de creme.', 1590, 'brownie', false, []],
    ['Petit gâteau', 'Bolinho de chocolate com recheio cremoso e sorvete.', 1790, 'petit-gateau', false, []],
    ['Pudim', 'Fatia de pudim de leite com calda de caramelo.', 990, 'pudim', false, []],
  ]],
];

/** Aplica o cardápio de exemplo (uma vez por banco). Devolve true se aplicou agora. */
export function applySampleMenu(db) {
  if (db.prepare('SELECT 1 FROM settings WHERE key = ?').get(SAMPLE_FLAG)) return false;

  transaction(db, () => {
    const addonId = new Map();
    for (const [name, price] of ADDONS) {
      const found = db.prepare('SELECT id FROM addons WHERE name = ?').get(name);
      addonId.set(
        name,
        found ? found.id : Number(db.prepare('INSERT INTO addons (name, price_cents) VALUES (?, ?)').run(name, price).lastInsertRowid)
      );
    }

    for (const [catName, catOrder, products] of MENU) {
      const cat = db.prepare('SELECT id FROM categories WHERE name = ?').get(catName);
      const catId = cat
        ? cat.id
        : Number(db.prepare('INSERT INTO categories (name, sort_order) VALUES (?, ?)').run(catName, catOrder).lastInsertRowid);

      products.forEach(([name, description, price, illustration, featured, addonNames], i) => {
        const existing = db.prepare('SELECT id, illustration FROM products WHERE name = ? COLLATE NOCASE').get(name);
        let productId;
        if (existing) {
          // produto que já existia (ex.: X-Bacon original): mantém preço e textos, só completa ilustração e destaque
          productId = existing.id;
          db.prepare('UPDATE products SET illustration = COALESCE(illustration, ?), featured = ? WHERE id = ?').run(
            illustration,
            featured ? 1 : 0,
            productId
          );
        } else {
          productId = Number(
            db
              .prepare(
                `INSERT INTO products (category_id, name, description, price_cents, illustration, featured, sort_order, image_alt)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
              )
              .run(catId, name, description, price, illustration, featured ? 1 : 0, i + 1, `Ilustração de ${name}`).lastInsertRowid
          );
        }
        const link = db.prepare('INSERT OR IGNORE INTO product_addons (product_id, addon_id) VALUES (?, ?)');
        for (const a of addonNames) link.run(productId, addonId.get(a));
      });
    }

    // Configurações de exemplo — só preenche o que ainda está no padrão vazio.
    const get = (k) => {
      const r = db.prepare('SELECT value FROM settings WHERE key = ?').get(k);
      return r ? JSON.parse(r.value) : undefined;
    };
    const set = (k, v) =>
      db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value').run(k, JSON.stringify(v));
    if (!get('delivery_enabled') && !get('delivery_fee_cents')) {
      set('delivery_enabled', true);
      set('delivery_fee_cents', 600);
    }
    if (!get('opening_hours')) set('opening_hours', 'Terça a domingo, das 18h às 23h');
    if (!get('about_text')) {
      set(
        'about_text',
        'Hambúrguer feito na hora, do jeito que você gosta. Escolha seu lanche, personalize com adicionais, ' +
          'receba em casa ou retire no balcão e acompanhe o pedido pelo site.'
      );
    }
    set(SAMPLE_FLAG, true);
  });
  return true;
}
