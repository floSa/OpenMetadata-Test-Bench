-- =====================================================================
-- omlab — schéma du mini-entrepôt "retail" servant de terrain de jeu
-- =====================================================================
-- Deux schémas :
--   raw       : les données "brutes" telles qu'elles arriveraient des systèmes source
--   analytics : les tables et vues dérivées (matière à lineage)
--
-- Certaines tables sont commentées, d'autres non : c'est volontaire.
-- Le chapitre 03 vous fera écrire les descriptions manquantes dans OpenMetadata.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;

-- ---------------------------------------------------------------------
-- raw.customers — contient de la PII (email) et des trous volontaires
-- ---------------------------------------------------------------------
CREATE TABLE raw.customers (
    customer_id   integer PRIMARY KEY,
    email         varchar(200),          -- PII, avec des doublons volontaires
    first_name    varchar(100) NOT NULL,
    last_name     varchar(100) NOT NULL,
    country       varchar(2),            -- ~8 % de NULL volontaires
    city          varchar(120),
    signup_date   date         NOT NULL,
    is_active     boolean      NOT NULL DEFAULT true
);

COMMENT ON TABLE  raw.customers IS 'Clients de la boutique, un enregistrement par client.';
COMMENT ON COLUMN raw.customers.email IS 'Adresse e-mail de contact du client.';

-- ---------------------------------------------------------------------
-- raw.products — sku volontairement non unique (piège pour les tests)
-- ---------------------------------------------------------------------
CREATE TABLE raw.products (
    product_id   integer PRIMARY KEY,
    sku          varchar(32)  NOT NULL,   -- devrait être unique... mais ne l'est pas
    name         varchar(200) NOT NULL,
    category     varchar(60)  NOT NULL,
    unit_price   numeric(10,2) NOT NULL,
    created_at   timestamp    NOT NULL DEFAULT now()
);

COMMENT ON TABLE raw.products IS 'Catalogue produits.';

-- ---------------------------------------------------------------------
-- raw.orders — montants parfois négatifs (avoirs mal modélisés)
-- ---------------------------------------------------------------------
CREATE TABLE raw.orders (
    order_id     integer PRIMARY KEY,
    customer_id  integer NOT NULL REFERENCES raw.customers(customer_id),
    order_date   date    NOT NULL,
    status       varchar(20) NOT NULL,
    amount       numeric(12,2) NOT NULL,  -- valeurs négatives volontaires
    currency     varchar(3) NOT NULL DEFAULT 'EUR'
);

-- (pas de COMMENT ici : à vous de jouer au chapitre 03)

-- ---------------------------------------------------------------------
-- raw.order_items
-- ---------------------------------------------------------------------
CREATE TABLE raw.order_items (
    order_item_id integer PRIMARY KEY,
    order_id      integer NOT NULL REFERENCES raw.orders(order_id),
    product_id    integer NOT NULL REFERENCES raw.products(product_id),
    quantity      integer NOT NULL,        -- des 0 volontaires
    unit_price    numeric(10,2) NOT NULL
);

-- ---------------------------------------------------------------------
-- raw.employees — la table la plus sensible : PII + données RH
-- ---------------------------------------------------------------------
CREATE TABLE raw.employees (
    employee_id  integer PRIMARY KEY,
    full_name    varchar(200) NOT NULL,
    email        varchar(200) NOT NULL,   -- PII
    phone        varchar(40),             -- PII
    national_id  varchar(20),             -- PII sensible (type NIR/SSN)
    department   varchar(60)  NOT NULL,
    salary       numeric(10,2) NOT NULL,  -- confidentiel
    hired_at     date         NOT NULL
);

COMMENT ON TABLE raw.employees IS 'Référentiel RH. Contient des données personnelles.';

-- ---------------------------------------------------------------------
-- Index (le profiler et les connecteurs les remontent)
-- ---------------------------------------------------------------------
CREATE INDEX idx_orders_customer ON raw.orders(customer_id);
CREATE INDEX idx_orders_date     ON raw.orders(order_date);
CREATE INDEX idx_items_order     ON raw.order_items(order_id);
