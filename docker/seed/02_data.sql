-- =====================================================================
-- omlab — génération des données (déterministe grâce à setseed)
-- =====================================================================
-- Les défauts sont semés à dessein : ce sont eux qui feront échouer
-- les tests de qualité du chapitre 10, pour de vraies raisons.
-- =====================================================================

SELECT setseed(0.42);

-- ---------------------------------------------------------------------
-- 500 clients
-- ---------------------------------------------------------------------
INSERT INTO raw.customers (customer_id, email, first_name, last_name, country, city, signup_date, is_active)
SELECT
    i,
    'user' || i || '@example.com',
    (ARRAY['Camille','Louis','Sofia','Malik','Emma','Noah','Lina','Hugo','Alice','Yanis'])[1 + (i % 10)],
    (ARRAY['Martin','Bernard','Dubois','Petit','Robert','Richard','Durand','Leroy','Moreau','Simon'])[1 + (i % 10)],
    -- ~8 % de pays manquants
    CASE WHEN random() < 0.08 THEN NULL
         ELSE (ARRAY['FR','BE','CH','DE','ES','IT','NL','UK'])[1 + (i % 8)] END,
    (ARRAY['Paris','Lyon','Bruxelles','Genève','Berlin','Madrid','Milan','Amsterdam'])[1 + (i % 8)],
    DATE '2023-01-01' + (i % 730),
    random() > 0.15
FROM generate_series(1, 500) AS i;

-- Doublons d'e-mails volontaires : 12 clients partagent l'adresse d'un autre
UPDATE raw.customers
SET email = 'user1@example.com'
WHERE customer_id IN (SELECT customer_id FROM raw.customers WHERE customer_id % 41 = 0 AND customer_id > 41);

-- ---------------------------------------------------------------------
-- 80 produits
-- ---------------------------------------------------------------------
INSERT INTO raw.products (product_id, sku, name, category, unit_price)
SELECT
    i,
    'SKU-' || lpad(i::text, 5, '0'),
    (ARRAY['Croquettes','Litière','Panier','Collier','Jouet','Gamelle','Laisse','Shampooing'])[1 + (i % 8)]
        || ' ' || (ARRAY['S','M','L','XL'])[1 + (i % 4)],
    (ARRAY['Alimentation','Hygiène','Accessoires','Jouets'])[1 + (i % 4)],
    round((5 + random() * 95)::numeric, 2)
FROM generate_series(1, 80) AS i;

-- SKU dupliqués volontaires : 4 produits réutilisent le SKU d'un autre
UPDATE raw.products SET sku = 'SKU-00001' WHERE product_id IN (17, 34, 51, 68);

-- ---------------------------------------------------------------------
-- 3 000 commandes
-- ---------------------------------------------------------------------
INSERT INTO raw.orders (order_id, customer_id, order_date, status, amount, currency)
SELECT
    i,
    1 + (i * 7) % 500,
    DATE '2024-01-01' + (i % 550),
    (ARRAY['completed','completed','completed','pending','cancelled','refunded'])[1 + (i % 6)],
    -- ~3 % de montants négatifs (avoirs enregistrés comme des commandes)
    CASE WHEN random() < 0.03 THEN -round((10 + random() * 200)::numeric, 2)
         ELSE round((10 + random() * 400)::numeric, 2) END,
    'EUR'
FROM generate_series(1, 3000) AS i;

-- ---------------------------------------------------------------------
-- ~7 000 lignes de commande
-- ---------------------------------------------------------------------
INSERT INTO raw.order_items (order_item_id, order_id, product_id, quantity, unit_price)
SELECT
    row_number() OVER (),
    o.order_id,
    1 + ((o.order_id * n) % 80),
    -- ~2 % de quantités nulles (lignes annulées non supprimées)
    CASE WHEN random() < 0.02 THEN 0 ELSE 1 + (n % 4) END,
    round((5 + random() * 95)::numeric, 2)
FROM raw.orders o
CROSS JOIN generate_series(1, 3) AS n
WHERE (o.order_id + n) % 5 <> 0;

-- ---------------------------------------------------------------------
-- 60 salariés (PII)
-- ---------------------------------------------------------------------
INSERT INTO raw.employees (employee_id, full_name, email, phone, national_id, department, salary, hired_at)
SELECT
    i,
    (ARRAY['Camille','Louis','Sofia','Malik','Emma','Noah'])[1 + (i % 6)] || ' ' ||
    (ARRAY['Martin','Bernard','Dubois','Petit','Robert','Richard'])[1 + (i % 6)],
    'prenom.nom' || i || '@omlab.internal',
    '+33 6 ' || lpad(((i * 137) % 100)::text, 2, '0') || ' '
              || lpad(((i * 71)  % 100)::text, 2, '0') || ' '
              || lpad(((i * 29)  % 100)::text, 2, '0') || ' '
              || lpad(((i * 13)  % 100)::text, 2, '0'),
    '1' || lpad(((i * 9176) % 100000000)::text, 12, '0'),
    (ARRAY['Data','Finance','RH','Logistique','Marketing','Support'])[1 + (i % 6)],
    round((32000 + random() * 48000)::numeric, 2),
    DATE '2019-01-01' + (i * 37)
FROM generate_series(1, 60) AS i;

ANALYZE;
