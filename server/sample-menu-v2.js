// Ampliação do cardápio de EXEMPLO (pedido do dono em 06/10/2026: "mais diversidade,
// sem tirar o que já tem"). Aplicada uma única vez em cada banco, por cima da v1:
// - só ADICIONA categorias, produtos, adicionais e grupos de opções que ainda não existem;
// - nunca apaga nada; textos/selos/ordem de itens antigos só mudam se ainda estiverem
//   exatamente como a v1 criou (ou seja, se o dono não editou).
// Preços são sugestões — revise no painel antes de atender clientes reais.
import { transaction } from './db.js';
import { SAMPLE_FLAG } from './sample-menu.js';

export const SAMPLE_FLAG_V2 = '_cardapio_exemplo_v2';

// Grupos de opções: [nome, tipo, obrigatório, máximo, escolhas: [nome, preço]]
const GROUPS = [
  ['Ponto da carne', 'single', true, null, [['Mal passado', 0], ['Ao ponto', 0], ['Bem passado', 0]]],
  ['Tipo de pão', 'single', true, null, [['Tradicional', 0], ['Brioche', 200], ['Australiano', 300]]],
  ['Retirar ingredientes', 'multi', false, null, [['Sem cebola', 0], ['Sem tomate', 0], ['Sem alface', 0], ['Sem picles', 0], ['Sem molho', 0]]],
  ['Sabor do refrigerante', 'single', true, null, [['Cola', 0], ['Cola zero', 0], ['Guaraná', 0], ['Laranja', 0], ['Limão', 0]]],
  ['Sabor do suco', 'single', true, null, [['Laranja', 0], ['Limão', 0], ['Maracujá', 0], ['Abacaxi com hortelã', 0]]],
  ['Sabor do milk-shake', 'single', true, null, [['Chocolate', 0], ['Morango', 0], ['Baunilha', 0], ['Doce de leite', 0]]],
  ['Molho dos nuggets', 'single', true, null, [['Barbecue', 0], ['Mostarda e mel', 0], ['Maionese da casa', 0]]],
  ['Água', 'single', true, null, [['Sem gás', 0], ['Com gás', 0]]],
  ['Acompanhamentos do açaí', 'multi', false, 4, [['Granola', 0], ['Banana', 0], ['Leite condensado', 0], ['Leite em pó', 0], ['Paçoca', 0], ['Morango', 200], ['Creme de avelã', 400]]],
  ['Sabores do sorvete', 'multi', true, 2, [['Creme', 0], ['Chocolate', 0], ['Morango', 0], ['Flocos', 0]]],
  ['Bebida do kids', 'single', true, null, [['Suco de uva', 0], ['Suco de laranja', 0], ['Água', 0]]],
];

const BEEF = ['Ponto da carne', 'Tipo de pão', 'Retirar ingredientes'];
const BREAD = ['Tipo de pão', 'Retirar ingredientes'];
const REMOVE = ['Retirar ingredientes'];

const NEW_ADDONS = [
  ['Calabresa', 400],
  ['Jalapeño', 300],
  ['Picles', 200],
  ['Queijo coalho', 500],
];

const BURGER_ADDONS = ['Bacon extra', 'Cheddar extra', 'Ovo', 'Carne extra (150 g)', 'Cebola caramelizada', 'Catupiry', 'Molho especial', 'Picles'];
const SMASH_ADDONS = ['Bacon extra', 'Cheddar extra', 'Cebola caramelizada', 'Jalapeño', 'Picles', 'Molho especial'];
const DOG_ADDONS = ['Bacon extra', 'Cheddar extra', 'Catupiry', 'Calabresa'];
const PORTION_ADDONS = ['Cheddar extra', 'Bacon extra', 'Catupiry', 'Molho especial'];

// Categorias: [nome, ordem]
const CATEGORY_ORDER = [
  ['Hambúrgueres', 1],
  ['Smash Burgers', 2],
  ['Artesanais Premium', 3],
  ['Combos', 4],
  ['Hot Dogs', 5],
  ['Sanduíches', 6],
  ['Porções', 7],
  ['Kids', 8],
  ['Bebidas', 9],
  ['Açaí', 10],
  ['Sobremesas', 11],
  ['Molhos', 12],
];
const V1_ORDER = { Hambúrgueres: 1, Combos: 2, Porções: 3, Bebidas: 4, Sobremesas: 5 };

// Produtos novos: [categoria, nome, descrição, preço, promo|null, ilustração, selos, grupos, adicionais]
const NEW_PRODUCTS = [
  ['Hambúrgueres', 'X-Calabresa', 'Pão, carne de 150 g, queijo e calabresa acebolada.', 2390, null, 'x-calabresa', [], BEEF, BURGER_ADDONS],
  ['Hambúrgueres', 'X-Frango Catupiry', 'Pão, frango desfiado, catupiry, milho e alface.', 2390, null, 'x-frango', [], BREAD, BURGER_ADDONS],
  ['Hambúrgueres', 'X-Cheddar Bacon', 'Pão, carne de 150 g, cheddar cremoso e bacon em dobro.', 2690, null, 'x-cheddar', [], BEEF, BURGER_ADDONS],

  ['Smash Burgers', 'Smash Simples', 'Pão brioche, uma carne smash de 90 g, queijo, cebola e molho da casa.', 1890, null, 'smash', ['novo'], REMOVE, SMASH_ADDONS],
  ['Smash Burgers', 'Smash Bacon', 'Pão brioche, duas carnes smash, queijo e bacon crocante.', 2290, 1990, 'smash-bacon', [], REMOVE, SMASH_ADDONS],
  ['Smash Burgers', 'Smash Triplo', 'Pão brioche, três carnes smash e três fatias de cheddar.', 3290, null, 'smash-triplo', [], REMOVE, SMASH_ADDONS],
  ['Smash Burgers', 'Smash Picante', 'Pão brioche, duas carnes smash, queijo pepper jack, jalapeño e molho chipotle.', 2490, null, 'smash-picante', ['picante', 'novo'], REMOVE, SMASH_ADDONS],

  ['Artesanais Premium', 'Burger de Costela', 'Pão brioche, blend de costela de 180 g, queijo prato e barbecue.', 3690, null, 'premium-costela', [], BEEF, BURGER_ADDONS],
  ['Artesanais Premium', 'Picanha Burger', 'Pão australiano, blend de picanha de 180 g, queijo coalho e vinagrete.', 3890, null, 'premium-picanha', ['novo'], BEEF, BURGER_ADDONS],
  ['Artesanais Premium', 'Gorgonzola & Mel', 'Pão brioche, blend de 180 g, gorgonzola, mel e rúcula.', 3790, null, 'premium-gorgonzola', [], BEEF, BURGER_ADDONS],
  ['Artesanais Premium', 'Cheddar Onion Crispy', 'Pão brioche, blend de 180 g, cheddar, cebola crispy e maionese defumada.', 3490, null, 'premium-onion', [], BEEF, BURGER_ADDONS],
  ['Artesanais Premium', 'BBQ Defumado', 'Pão australiano, blend de 180 g, bacon defumado, picles e barbecue.', 3590, null, 'premium-bbq', ['picante'], BEEF, BURGER_ADDONS],

  ['Combos', 'Combo Casal', '2 X-Bacon + batata frita grande + refrigerante 2 L.', 7490, 6990, 'combo-casal', ['compartilhar'], ['Sabor do refrigerante', 'Retirar ingredientes'], []],
  ['Combos', 'Combo Smash Bacon', 'Smash Bacon + batata frita pequena + refrigerante lata.', 3490, null, 'combo', [], ['Sabor do refrigerante', 'Retirar ingredientes'], []],

  ['Hot Dogs', 'Hot Dog Tradicional', 'Pão, salsicha, molho de tomate, milho e batata palha.', 1290, null, 'hotdog', [], REMOVE, DOG_ADDONS],
  ['Hot Dogs', 'Hot Dog Especial', 'Pão, duas salsichas, purê, milho, queijo e batata palha.', 1790, 1590, 'hotdog-especial', [], REMOVE, DOG_ADDONS],
  ['Hot Dogs', 'Hot Dog Bacon & Cheddar', 'Pão, salsicha, cheddar cremoso, bacon e batata palha.', 1990, null, 'hotdog-bacon', [], REMOVE, DOG_ADDONS],

  ['Sanduíches', 'Misto Quente', 'Pão de forma na chapa com presunto e queijo.', 1090, null, 'misto-quente', [], [], ['Ovo', 'Catupiry']],
  ['Sanduíches', 'Sanduíche Natural de Frango', 'Pão integral, frango desfiado, cenoura, alface e maionese.', 1490, null, 'sanduiche-natural', [], REMOVE, []],
  ['Sanduíches', 'Beirute de Frango', 'Pão sírio, frango grelhado, queijo, alface, tomate e molho de ervas.', 2690, null, 'beirute', [], REMOVE, ['Catupiry', 'Bacon extra']],

  ['Porções', 'Mandioca frita', 'Porção de 400 g de mandioca crocante.', 1890, null, 'mandioca', ['vegetariano', 'compartilhar'], [], PORTION_ADDONS],
  ['Porções', 'Isca de frango', '400 g de iscas de frango empanadas com molho.', 3290, null, 'isca-frango', ['compartilhar'], ['Molho dos nuggets'], PORTION_ADDONS],
  ['Porções', 'Porção mista', 'Batata frita, onion rings e iscas de frango. Serve 2 a 3 pessoas.', 4990, null, 'porcao-mista', ['compartilhar'], [], PORTION_ADDONS],
  ['Porções', 'Batata rústica com alecrim', 'Batata com casca, alecrim e alho, 300 g.', 2190, null, 'batata-rustica', ['vegetariano', 'novo'], [], PORTION_ADDONS],

  ['Kids', 'Kids Burger', 'Mini hambúrguer com queijo, batata pequena e bebida.', 2490, null, 'kids', [], ['Bebida do kids', 'Retirar ingredientes'], []],
  ['Kids', 'Kids Nuggets', '6 nuggets, batata pequena e bebida.', 2290, null, 'kids-nuggets', [], ['Bebida do kids', 'Molho dos nuggets'], []],

  ['Bebidas', 'Refrigerante 600 ml', 'Garrafa de 600 ml. Escolha o sabor.', 890, null, 'refrigerante-600', [], ['Sabor do refrigerante'], []],
  ['Bebidas', 'Limonada suíça', 'Copo de 400 ml, limão batido com leite condensado.', 1190, null, 'limonada', [], [], []],
  ['Bebidas', 'Chá gelado de pêssego', 'Copo de 400 ml com gelo.', 890, null, 'cha-gelado', [], [], []],

  ['Açaí', 'Açaí 300 ml', 'Açaí cremoso com até 4 acompanhamentos.', 1590, null, 'acai', ['vegetariano'], ['Acompanhamentos do açaí'], []],
  ['Açaí', 'Açaí 500 ml', 'Açaí cremoso com até 4 acompanhamentos.', 2190, 1890, 'acai-grande', ['vegetariano'], ['Acompanhamentos do açaí'], []],
  ['Açaí', 'Açaí na tigela 700 ml', 'Tigela de açaí com até 4 acompanhamentos. Ótima para dividir.', 2990, null, 'acai-tigela', ['vegetariano', 'compartilhar'], ['Acompanhamentos do açaí'], []],

  ['Sobremesas', 'Churros com doce de leite', '4 mini churros com açúcar, canela e doce de leite.', 1290, null, 'churros', ['vegetariano'], [], []],
  ['Sobremesas', 'Sorvete 2 bolas', 'Duas bolas de sorvete com calda.', 1090, null, 'sorvete', ['vegetariano'], ['Sabores do sorvete'], []],
  ['Sobremesas', 'Mousse de maracujá', 'Taça de mousse com calda de maracujá.', 990, null, 'mousse', ['vegetariano'], [], []],

  ['Molhos', 'Maionese da casa', 'Pote de 40 g.', 300, null, 'molho-maionese', ['vegetariano'], [], []],
  ['Molhos', 'Barbecue', 'Pote de 40 g.', 300, null, 'molho-barbecue', ['vegetariano'], [], []],
  ['Molhos', 'Cheddar cremoso', 'Pote de 40 g.', 400, null, 'molho-cheddar', ['vegetariano'], [], []],
  ['Molhos', 'Maionese verde', 'Pote de 40 g, com ervas.', 300, null, 'molho-verde', ['vegetariano'], [], []],
];

// Itens da v1: opções/selos que passam a fazer sentido (só se o dono não mexeu).
// [nome, grupos, selos, descrição antiga (v1) -> nova]
const V1_UPDATES = [
  ['X-Bacon', BEEF, [], null],
  ['X-Burguer', BEEF, [], null],
  ['X-Salada', BEEF, [], null],
  ['X-Egg', BEEF, [], null],
  ['X-Tudo', BEEF, [], null],
  ['Desu Smash Duplo', REMOVE, [], null],
  ['Chicken Crispy', BREAD, [], null],
  ['Veggie', BREAD, ['vegetariano'], null],
  ['Combo X-Bacon', ['Sabor do refrigerante', 'Retirar ingredientes'], [], null],
  ['Combo Smash', ['Sabor do refrigerante', 'Retirar ingredientes'], [], null],
  ['Combo Família', ['Sabor do refrigerante', 'Retirar ingredientes'], ['compartilhar'], null],
  ['Batata frita grande', [], ['vegetariano', 'compartilhar'], null],
  ['Batata frita pequena', [], ['vegetariano'], null],
  ['Onion rings', [], ['vegetariano'], null],
  ['Nuggets', ['Molho dos nuggets'], [], ['10 unidades com molho à escolha (informe na observação).', '10 unidades com molho à escolha.']],
  ['Refrigerante lata', ['Sabor do refrigerante'], [], ['Lata de 350 ml. Informe o sabor na observação.', 'Lata de 350 ml. Escolha o sabor.']],
  ['Refrigerante 2 L', ['Sabor do refrigerante'], ['compartilhar'], ['Garrafa de 2 litros. Informe o sabor na observação.', 'Garrafa de 2 litros. Escolha o sabor.']],
  ['Suco natural', ['Sabor do suco'], [], ['Copo de 400 ml: laranja, limão ou maracujá (informe na observação).', 'Copo de 400 ml. Escolha a fruta.']],
  ['Água mineral', ['Água'], [], ['Garrafa de 500 ml, com ou sem gás.', 'Garrafa de 500 ml.']],
  ['Milk-shake', ['Sabor do milk-shake'], [], ['Copo de 400 ml: chocolate, morango ou baunilha (informe na observação).', 'Copo de 400 ml. Escolha o sabor.']],
  ['Brownie com sorvete', [], ['vegetariano'], null],
  ['Petit gâteau', [], ['vegetariano'], null],
  ['Pudim', [], ['vegetariano'], null],
];

export function applySampleMenuV2(db) {
  // Só amplia bancos que receberam o cardápio de exemplo v1.
  if (!db.prepare('SELECT 1 FROM settings WHERE key = ?').get(SAMPLE_FLAG)) return false;
  if (db.prepare('SELECT 1 FROM settings WHERE key = ?').get(SAMPLE_FLAG_V2)) return false;

  transaction(db, () => {
    // grupos de opções
    const groupId = new Map();
    for (const [name, kind, required, max, choices] of GROUPS) {
      const found = db.prepare('SELECT id FROM option_groups WHERE name = ?').get(name);
      let id = found?.id;
      if (!id) {
        id = Number(
          db.prepare('INSERT INTO option_groups (name, kind, required, max_choices) VALUES (?, ?, ?, ?)').run(name, kind, required ? 1 : 0, max)
            .lastInsertRowid
        );
        choices.forEach(([cname, price], i) =>
          db.prepare('INSERT INTO option_choices (group_id, name, price_cents, sort_order) VALUES (?, ?, ?, ?)').run(id, cname, price, i + 1)
        );
      }
      groupId.set(name, id);
    }

    // adicionais novos
    for (const [name, price] of NEW_ADDONS) {
      if (!db.prepare('SELECT 1 FROM addons WHERE name = ?').get(name)) {
        db.prepare('INSERT INTO addons (name, price_cents) VALUES (?, ?)').run(name, price);
      }
    }
    const addonId = (name) => db.prepare('SELECT id FROM addons WHERE name = ?').get(name)?.id;

    // categorias (cria as novas; reordena as antigas só se ainda estiverem na ordem da v1)
    const catId = new Map();
    for (const [name, order] of CATEGORY_ORDER) {
      const found = db.prepare('SELECT id, sort_order FROM categories WHERE name = ?').get(name);
      if (found) {
        if (V1_ORDER[name] === found.sort_order) db.prepare('UPDATE categories SET sort_order = ? WHERE id = ?').run(order, found.id);
        catId.set(name, found.id);
      } else {
        catId.set(name, Number(db.prepare('INSERT INTO categories (name, sort_order) VALUES (?, ?)').run(name, order).lastInsertRowid));
      }
    }

    const linkGroups = (productId, names) => {
      if (db.prepare('SELECT 1 FROM product_option_groups WHERE product_id = ?').get(productId)) return; // já configurado
      names.forEach((n, i) =>
        db.prepare('INSERT OR IGNORE INTO product_option_groups (product_id, group_id, sort_order) VALUES (?, ?, ?)').run(productId, groupId.get(n), i + 1)
      );
    };
    const linkAddons = (productId, names) => {
      for (const n of names) {
        const a = addonId(n);
        if (a) db.prepare('INSERT OR IGNORE INTO product_addons (product_id, addon_id) VALUES (?, ?)').run(productId, a);
      }
    };

    // produtos novos (pula os que já existem com o mesmo nome)
    const nextOrder = new Map();
    for (const [cat, name, description, price, promo, illustration, tags, groups, addons] of NEW_PRODUCTS) {
      if (db.prepare('SELECT 1 FROM products WHERE name = ? COLLATE NOCASE').get(name)) continue;
      const cid = catId.get(cat);
      if (!nextOrder.has(cid)) {
        nextOrder.set(cid, db.prepare('SELECT COALESCE(MAX(sort_order), 0) AS n FROM products WHERE category_id = ?').get(cid).n);
      }
      const order = nextOrder.get(cid) + 1;
      nextOrder.set(cid, order);
      const id = Number(
        db
          .prepare(
            `INSERT INTO products (category_id, name, description, price_cents, promo_price_cents, illustration, tags, sort_order, image_alt)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
          )
          .run(cid, name, description, price, promo, illustration, JSON.stringify(tags), order, `Ilustração de ${name}`).lastInsertRowid
      );
      linkGroups(id, groups);
      linkAddons(id, addons);
    }

    // itens da v1 (sem sobrescrever o que o dono já editou)
    for (const [name, groups, tags, desc] of V1_UPDATES) {
      const p = db.prepare('SELECT id, tags, description FROM products WHERE name = ? COLLATE NOCASE').get(name);
      if (!p) continue;
      linkGroups(p.id, groups);
      if (tags.length && (p.tags === '[]' || !p.tags)) db.prepare('UPDATE products SET tags = ? WHERE id = ?').run(JSON.stringify(tags), p.id);
      if (desc && p.description === desc[0]) db.prepare('UPDATE products SET description = ? WHERE id = ?').run(desc[1], p.id);
    }
    // novos adicionais combinam com os hambúrgueres de carne
    for (const n of ['X-Bacon', 'X-Burguer', 'X-Salada', 'X-Egg', 'X-Tudo', 'Desu Smash Duplo']) {
      const p = db.prepare('SELECT id FROM products WHERE name = ? COLLATE NOCASE').get(n);
      if (p) linkAddons(p.id, ['Picles', 'Jalapeño']);
    }

    db.prepare('INSERT INTO settings (key, value) VALUES (?, ?)').run(SAMPLE_FLAG_V2, 'true');
  });
  return true;
}

export const SAMPLE_FLAG_V3 = '_cardapio_exemplo_v3';

/**
 * Ajuste das ilustrações (07/10/2026): o Combo Casal ganhou desenho próprio
 * (2 lanches) em vez de reaproveitar o do Combo Família (4 lanches).
 * Só troca se o produto ainda estiver com a ilustração que o exemplo colocou.
 */
export function applySampleMenuV3(db) {
  if (!db.prepare('SELECT 1 FROM settings WHERE key = ?').get(SAMPLE_FLAG_V2)) return false;
  if (db.prepare('SELECT 1 FROM settings WHERE key = ?').get(SAMPLE_FLAG_V3)) return false;
  transaction(db, () => {
    db.prepare(
      "UPDATE products SET illustration = 'combo-casal' WHERE name = 'Combo Casal' COLLATE NOCASE AND illustration = 'combo-familia'"
    ).run();
    db.prepare('INSERT INTO settings (key, value) VALUES (?, ?)').run(SAMPLE_FLAG_V3, 'true');
  });
  return true;
}
