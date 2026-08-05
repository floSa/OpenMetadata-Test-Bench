-- =====================================================================
-- omlab — comptes de service utilisés par OpenMetadata
-- =====================================================================
-- Bonne pratique reprise de la doc : on ne connecte JAMAIS OpenMetadata
-- avec le superutilisateur. On crée un compte dédié en lecture seule,
-- plus le droit de lire les statistiques (nécessaire pour usage/lineage).
-- =====================================================================

CREATE USER om_reader WITH PASSWORD 'om_reader_pwd';

GRANT CONNECT ON DATABASE omlab TO om_reader;

GRANT USAGE ON SCHEMA raw, analytics TO om_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA raw, analytics TO om_reader;

-- Les tables créées plus tard seront lisibles elles aussi
ALTER DEFAULT PRIVILEGES IN SCHEMA raw       GRANT SELECT ON TABLES TO om_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO om_reader;

-- Indispensable pour les workflows "usage" et "lineage" :
-- sans ce droit, om_reader ne voit que ses propres requêtes dans pg_stat_statements.
GRANT pg_read_all_stats TO om_reader;
