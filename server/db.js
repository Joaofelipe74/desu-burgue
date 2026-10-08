// Banco de dados SQLite embutido no Node (node:sqlite).
// Todas as consultas usam parâmetros (?, :nome) — nunca concatenação de texto —
// o que impede SQL injection.
import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { applySampleMenu } from './sample-menu.js';
import { applySampleMenuV2, applySampleMenuV3 } from './sample-menu-v2.js';

const MIGRATIONS = [
  // 1: estrutura inicial
  `
  CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(name) BETWEEN 1 AND 60),
    sort_order INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );

  CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 80),
    description TEXT NOT NULL DEFAULT '' CHECK (length(description) <= 300),
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0 AND price_cents <= 100000000),
    image_file TEXT,
    image_thumb_file TEXT,
    image_width INTEGER,
    image_height INTEGER,
    image_alt TEXT NOT NULL DEFAULT '' CHECK (length(image_alt) <= 160),
    image_is_illustrative INTEGER NOT NULL DEFAULT 1 CHECK (image_is_illustrative IN (0,1)),
    available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0,1)),
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0,1)),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );
  CREATE INDEX idx_products_category ON products(category_id);

  CREATE TABLE addons (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(name) BETWEEN 1 AND 60),
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0 AND price_cents <= 10000000),
    available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0,1)),
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );

  CREATE TABLE product_addons (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    addon_id INTEGER NOT NULL REFERENCES addons(id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, addon_id)
  );

  CREATE TABLE coupons (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE CHECK (code GLOB '[A-Z0-9]*' AND length(code) BETWEEN 3 AND 20),
    kind TEXT NOT NULL CHECK (kind IN ('percent','fixed')),
    value INTEGER NOT NULL CHECK (value > 0),
    min_order_cents INTEGER NOT NULL DEFAULT 0 CHECK (min_order_cents >= 0),
    max_uses INTEGER CHECK (max_uses IS NULL OR max_uses > 0),
    uses INTEGER NOT NULL DEFAULT 0 CHECK (uses >= 0),
    valid_until TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (kind <> 'percent' OR value <= 100)
  );

  CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
  );

  CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    tracking_token TEXT NOT NULL UNIQUE,
    idempotency_key TEXT NOT NULL UNIQUE,
    request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('recebido','em_preparo','pronto','saiu_para_entrega','concluido','cancelado')),
    fulfillment TEXT NOT NULL CHECK (fulfillment IN ('entrega','retirada')),
    customer_name TEXT,
    customer_phone TEXT,
    address_json TEXT,
    notes TEXT NOT NULL DEFAULT '',
    payment_method TEXT NOT NULL CHECK (payment_method IN ('dinheiro','cartao','pix')),
    change_for_cents INTEGER,
    subtotal_cents INTEGER NOT NULL CHECK (subtotal_cents >= 0),
    discount_cents INTEGER NOT NULL DEFAULT 0 CHECK (discount_cents >= 0),
    delivery_fee_cents INTEGER NOT NULL DEFAULT 0 CHECK (delivery_fee_cents >= 0),
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    coupon_code TEXT,
    personal_data_purged_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (total_cents = subtotal_cents - discount_cents + delivery_fee_cents)
  );
  CREATE INDEX idx_orders_status ON orders(status, created_at);

  CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER,
    product_name TEXT NOT NULL,
    base_price_cents INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    line_total_cents INTEGER NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
  );
  CREATE INDEX idx_order_items_order ON order_items(order_id);

  CREATE TABLE order_item_addons (
    order_item_id INTEGER NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
    addon_id INTEGER,
    addon_name TEXT NOT NULL,
    price_cents INTEGER NOT NULL
  );

  CREATE TABLE order_status_history (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    from_status TEXT,
    to_status TEXT NOT NULL,
    admin_user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );

  CREATE TABLE admin_users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    last_login_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );

  CREATE TABLE sessions (
    id_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
  );
  CREATE INDEX idx_sessions_user ON sessions(user_id);

  CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    admin_user_id INTEGER,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id INTEGER,
    details TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );
  `,
  // 2: ilustrações e destaques na página inicial
  `
  ALTER TABLE products ADD COLUMN illustration TEXT;
  ALTER TABLE products ADD COLUMN featured INTEGER NOT NULL DEFAULT 0 CHECK (featured IN (0,1));
  `,
  // 3: preço promocional, selos e grupos de opções (ponto da carne, pão, retirar ingredientes, sabores...)
  `
  ALTER TABLE products ADD COLUMN promo_price_cents INTEGER CHECK (promo_price_cents IS NULL OR promo_price_cents >= 0);
  ALTER TABLE products ADD COLUMN tags TEXT NOT NULL DEFAULT '[]';

  CREATE TABLE option_groups (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(name) BETWEEN 1 AND 60),
    kind TEXT NOT NULL CHECK (kind IN ('single','multi')),
    required INTEGER NOT NULL DEFAULT 0 CHECK (required IN (0,1)),
    max_choices INTEGER CHECK (max_choices IS NULL OR max_choices >= 1),
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );

  CREATE TABLE option_choices (
    id INTEGER PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES option_groups(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 60),
    price_cents INTEGER NOT NULL DEFAULT 0 CHECK (price_cents >= 0 AND price_cents <= 1000000),
    available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0,1)),
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0,1)),
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE (group_id, name)
  );
  CREATE INDEX idx_option_choices_group ON option_choices(group_id);

  CREATE TABLE product_option_groups (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES option_groups(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (product_id, group_id)
  );

  CREATE TABLE order_item_options (
    order_item_id INTEGER NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
    group_name TEXT NOT NULL,
    choice_id INTEGER,
    choice_name TEXT NOT NULL,
    price_cents INTEGER NOT NULL
  );
  `,
];

export const DEFAULT_SETTINGS = {
  store_name: 'Desu Burguer',
  accepting_orders: true,
  closed_message: 'No momento não estamos recebendo pedidos.',
  pickup_enabled: true,
  pickup_address: '',
  delivery_enabled: false,
  delivery_fee_cents: 0,
  min_order_cents: 0,
  payment_methods: { dinheiro: true, cartao: true, pix: true },
  contact_phone: '',
  whatsapp: '',
  opening_hours: '',
  about_text: '',
};

/**
 * Abre (ou cria) o banco. `sampleMenu`: aplica uma única vez o cardápio de
 * exemplo com preços sugeridos (server/sample-menu.js). Os testes desligam.
 */
export function openDatabase(file, { sampleMenu = true } = {}) {
  if (file !== ':memory:') fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new DatabaseSync(file);
  db.exec('PRAGMA foreign_keys = ON;');
  db.exec('PRAGMA busy_timeout = 5000;');
  if (file !== ':memory:') db.exec('PRAGMA journal_mode = WAL;');
  migrate(db);
  seed(db);
  if (sampleMenu) {
    applySampleMenu(db);
    applySampleMenuV2(db);
    applySampleMenuV3(db);
  }
  return db;
}

function migrate(db) {
  const current = db.prepare('PRAGMA user_version').get().user_version;
  for (let v = current; v < MIGRATIONS.length; v++) {
    transaction(db, () => {
      db.exec(MIGRATIONS[v]);
      db.exec(`PRAGMA user_version = ${v + 1}`);
    });
  }
}

/**
 * Dados iniciais: apenas o que já existia no projeto original
 * (categoria de hambúrgueres e o X-Bacon a R$ 24,90). Só roda com o banco vazio.
 */
function seed(db) {
  const insertSetting = db.prepare('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)');
  for (const [k, v] of Object.entries(DEFAULT_SETTINGS)) insertSetting.run(k, JSON.stringify(v));

  const hasCategories = db.prepare('SELECT COUNT(*) AS n FROM categories').get().n > 0;
  if (hasCategories) return;
  transaction(db, () => {
    const cat = db.prepare('INSERT INTO categories (name, sort_order) VALUES (?, ?)').run('Hambúrgueres', 1);
    db.prepare(
      `INSERT INTO products (category_id, name, description, price_cents, image_alt, sort_order)
       VALUES (?, ?, ?, ?, ?, ?)`
    ).run(
      cat.lastInsertRowid,
      'X-Bacon',
      'Pão, carne, queijo e bacon crocante.',
      2490,
      'X-Bacon: hambúrguer com carne, queijo e bacon crocante',
      1
    );
  });
}

/** Executa fn dentro de uma transação (BEGIN IMMEDIATE trava a escrita até o fim). */
export function transaction(db, fn) {
  db.exec('BEGIN IMMEDIATE');
  try {
    const result = fn();
    db.exec('COMMIT');
    return result;
  } catch (err) {
    db.exec('ROLLBACK');
    throw err;
  }
}

export function nowIso() {
  return new Date().toISOString();
}
