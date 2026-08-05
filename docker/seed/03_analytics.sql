-- =====================================================================
-- omlab — couche analytics : c'est elle qui produit du lineage
-- =====================================================================
-- Deux mécanismes de lineage différents sont mis en scène ici :
--
--   1. Les VUES  : le connecteur Postgres lit leur définition SQL et en
--      déduit le lineage de façon fiable, dès l'ingestion de métadonnées.
--   2. Les TABLES alimentées par INSERT ... SELECT : le lineage n'apparaît
--      que si la requête a été observée (pg_stat_statements ou query log).
--      C'est tout l'objet du chapitre 06.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Tables cibles
-- ---------------------------------------------------------------------
CREATE TABLE analytics.dim_customer (
    customer_id    integer PRIMARY KEY,
    full_name      varchar(200),
    email          varchar(200),
    country        varchar(2),
    signup_date    date,
    is_active      boolean
);

COMMENT ON TABLE analytics.dim_customer IS 'Dimension client, dérivée de raw.customers.';

CREATE TABLE analytics.fct_orders (
    order_id       integer PRIMARY KEY,
    customer_id    integer,
    customer_country varchar(2),
    order_date     date,
    order_month    date,
    status         varchar(20),
    amount         numeric(12,2),
    is_credit_note boolean
);

COMMENT ON TABLE analytics.fct_orders IS 'Table de faits des commandes, une ligne par commande.';

-- ---------------------------------------------------------------------
-- Alimentation (le SQL qui crée le lineage raw -> analytics)
-- ---------------------------------------------------------------------
INSERT INTO analytics.dim_customer (customer_id, full_name, email, country, signup_date, is_active)
SELECT
    customer_id,
    first_name || ' ' || last_name,
    email,
    country,
    signup_date,
    is_active
FROM raw.customers;

INSERT INTO analytics.fct_orders (order_id, customer_id, customer_country, order_date, order_month, status, amount, is_credit_note)
SELECT
    o.order_id,
    o.customer_id,
    c.country,
    o.order_date,
    date_trunc('month', o.order_date)::date,
    o.status,
    o.amount,
    o.amount < 0
FROM raw.orders o
JOIN raw.customers c ON c.customer_id = o.customer_id;

-- ---------------------------------------------------------------------
-- Vues : lineage garanti dès l'ingestion de métadonnées
-- ---------------------------------------------------------------------
CREATE VIEW analytics.v_revenue_monthly AS
SELECT
    order_month,
    customer_country,
    count(*)          AS order_count,
    sum(amount)       AS revenue,
    avg(amount)       AS avg_basket
FROM analytics.fct_orders
WHERE status = 'completed'
GROUP BY order_month, customer_country;

COMMENT ON VIEW analytics.v_revenue_monthly IS 'Chiffre d''affaires mensuel par pays, commandes complétées uniquement.';

CREATE VIEW analytics.v_customer_360 AS
SELECT
    c.customer_id,
    c.email,
    c.country,
    count(o.order_id)                AS lifetime_orders,
    coalesce(sum(o.amount), 0)       AS lifetime_value,
    max(o.order_date)                AS last_order_date
FROM raw.customers c
LEFT JOIN raw.orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.email, c.country;

ANALYZE;
