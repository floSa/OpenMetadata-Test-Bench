-- =====================================================================
-- omlab — trafic simulé : donne à manger à pg_stat_statements
-- =====================================================================
-- Les workflows "usage" et "lineage" du connecteur Postgres ne lisent pas
-- un journal de requêtes : ils lisent la vue pg_stat_statements, qui ne
-- contient que ce qui a effectivement été exécuté depuis le dernier reset.
--
-- Sur une base fraîchement créée, cette vue est quasi vide → aucun usage,
-- aucun lineage. Ce script rejoue donc un trafic réaliste.
--
--   make traffic     (à relancer avant chaque ingestion usage/lineage)
-- =====================================================================

-- --- Rechargement des tables analytics (c'est ce SQL qui porte le lineage) ---
TRUNCATE analytics.fct_orders;
INSERT INTO analytics.fct_orders (order_id, customer_id, customer_country, order_date, order_month, status, amount, is_credit_note)
SELECT o.order_id, o.customer_id, c.country, o.order_date,
       date_trunc('month', o.order_date)::date, o.status, o.amount, o.amount < 0
FROM raw.orders o
JOIN raw.customers c ON c.customer_id = o.customer_id;

TRUNCATE analytics.dim_customer CASCADE;
INSERT INTO analytics.dim_customer (customer_id, full_name, email, country, signup_date, is_active)
SELECT customer_id, first_name || ' ' || last_name, email, country, signup_date, is_active
FROM raw.customers;

-- --- Requêtes de lecture : c'est ce qui fait la "popularité" des tables ---
-- La table la plus interrogée doit ressortir en tête du classement d'usage.
SELECT count(*) FROM analytics.v_revenue_monthly;
SELECT count(*) FROM analytics.v_revenue_monthly;
SELECT count(*) FROM analytics.v_revenue_monthly;
SELECT count(*) FROM analytics.v_revenue_monthly;
SELECT count(*) FROM analytics.v_revenue_monthly;

SELECT customer_country, sum(revenue) FROM analytics.v_revenue_monthly GROUP BY 1;
SELECT order_month, sum(revenue) FROM analytics.v_revenue_monthly GROUP BY 1 ORDER BY 1;

SELECT * FROM analytics.v_customer_360 ORDER BY lifetime_value DESC LIMIT 20;
SELECT * FROM analytics.v_customer_360 WHERE country = 'FR' LIMIT 50;

SELECT o.status, count(*), sum(o.amount)
FROM raw.orders o
JOIN raw.customers c ON c.customer_id = o.customer_id
GROUP BY o.status;

SELECT p.category, sum(i.quantity * i.unit_price) AS ca
FROM raw.order_items i
JOIN raw.products p ON p.product_id = i.product_id
GROUP BY p.category
ORDER BY ca DESC;

SELECT department, avg(salary) FROM raw.employees GROUP BY department;

SELECT count(*) FROM raw.customers WHERE country IS NULL;
SELECT count(*) FROM raw.orders WHERE amount < 0;
