PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    website TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    category_id INTEGER,
    unit_id INTEGER,
    sku TEXT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    product_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES providers (id),
    FOREIGN KEY (category_id) REFERENCES categories (id),
    FOREIGN KEY (unit_id) REFERENCES units (id),
    UNIQUE (provider_id, sku)
);

CREATE TABLE IF NOT EXISTS price_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    observed_at TEXT NOT NULL,
    source_url TEXT,
    raw_price TEXT,
    price_amount REAL NOT NULL CHECK (price_amount >= 0),
    currency TEXT NOT NULL DEFAULT 'PEN',
    raw_unit TEXT,
    normalized_unit_id INTEGER,
    availability TEXT,
    extraction_status TEXT NOT NULL DEFAULT 'success',
    FOREIGN KEY (product_id) REFERENCES products (id),
    FOREIGN KEY (normalized_unit_id) REFERENCES units (id)
);

CREATE TABLE IF NOT EXISTS apu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    unit_id INTEGER NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (unit_id) REFERENCES units (id)
);

CREATE TABLE IF NOT EXISTS apu_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apu_item_id INTEGER NOT NULL,
    product_id INTEGER,
    component_type TEXT NOT NULL CHECK (component_type IN ('material', 'equipment', 'labor', 'other')),
    quantity REAL NOT NULL CHECK (quantity >= 0),
    unit_id INTEGER NOT NULL,
    notes TEXT,
    FOREIGN KEY (apu_item_id) REFERENCES apu_items (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id),
    FOREIGN KEY (unit_id) REFERENCES units (id)
);

CREATE INDEX IF NOT EXISTS idx_products_provider ON products (provider_id);
CREATE INDEX IF NOT EXISTS idx_products_normalized_name ON products (normalized_name);
CREATE INDEX IF NOT EXISTS idx_observations_product_date ON price_observations (product_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_observations_date ON price_observations (observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_apu_components_item ON apu_components (apu_item_id);
