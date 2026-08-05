# Chapitre 04 — L'ingestion de métadonnées

> **Objectifs** — Comprendre l'anatomie d'un workflow, savoir écrire et
> déboguer un fichier d'ingestion, maîtriser les filtres, et choisir entre
> l'UI et le YAML en connaissance de cause.
> **Durée** — 50 minutes.

---

## 1. Les quatre blocs, toujours les mêmes

Tout workflow OpenMetadata a la même structure. Une fois qu'on l'a en tête,
les cinq types de workflows des chapitres suivants s'écrivent tout seuls.

```yaml
source:          # d'où viennent les métadonnées, et quoi retenir
processor:       # transformations en cours de route (souvent absent)
sink:            # où les envoyer (en pratique : toujours metadata-rest)
workflowConfig:  # comment joindre le serveur OpenMetadata
```

Ouvrez [`tp/04-ingestion/metadata.yaml`](../tp/04-ingestion/metadata.yaml) et
suivez avec.

### `source` — la connexion et le périmètre

```yaml
source:
  type: postgres                    # le connecteur
  serviceName: omlab_postgres       # le nom dans le catalogue = racine des FQN
  serviceConnection:
    config:
      type: Postgres
      username: om_reader
      authType:
        password: om_reader_pwd
      hostPort: omlab-postgres:5432
      database: omlab
```

Trois pièges dans ces dix lignes :

1. **`serviceName` est définitif en pratique.** C'est le premier segment de
   tous vos FQN. Le changer plus tard, c'est recréer tout le catalogue de ce
   service et perdre descriptions, étiquettes et lineage.
2. **`hostPort` est vu depuis le conteneur d'ingestion.** `localhost:5433`
   fonctionne depuis votre terminal, jamais depuis le workflow. C'est
   `omlab-postgres:5432`.
3. **`type: postgres` (source) et `type: Postgres` (connexion)** ne sont pas
   la même chose et n'ont pas la même casse. Le premier désigne le module
   Python, le second le type de connexion dans le modèle. Oui, c'est
   déroutant ; non, ce n'est pas interchangeable.

### Le compte de service

Notre YAML se connecte avec `om_reader`, créé par
[`docker/seed/04_users.sql`](../docker/seed/04_users.sql) :

```sql
CREATE USER om_reader WITH PASSWORD 'om_reader_pwd';
GRANT USAGE ON SCHEMA raw, analytics TO om_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA raw, analytics TO om_reader;
GRANT pg_read_all_stats TO om_reader;
```

Un catalogue ne se connecte jamais en superutilisateur. Il lui faut le droit
de **lire les métadonnées**, et rien de plus. Le `pg_read_all_stats` servira
aux chapitres 05 et 06 : sans lui, le compte ne voit que ses propres requêtes
dans `pg_stat_statements` — et les workflows d'usage et de lineage remontent
vides sans le moindre message d'erreur.

### `sourceConfig` — ce qu'on ramène et ce qu'on filtre

```yaml
sourceConfig:
  config:
    type: DatabaseMetadata
    includeTables: true
    includeViews: true          # les vues portent le lineage : ne pas couper
    includeTags: true
    markDeletedTables: true
    schemaFilterPattern:
      includes: ["^raw$", "^analytics$"]
    tableFilterPattern:
      excludes: [".*_tmp$", "^tmp_.*"]
```

**Les filtres sont des expressions régulières, pas des jokers.** Le piège
classique est d'écrire `includes: ["raw"]` : sans ancrage, ce motif attrape
aussi `raw_archive`, `raw_2023` et `preraw`. Écrivez `^raw$`.

**`markDeletedTables: true`** signifie : une table disparue de la base est
marquée supprimée dans le catalogue, mais **pas** effacée — son historique et
ses descriptions restent consultables. À `false`, la table reste affichée
comme vivante alors qu'elle n'existe plus : le pire des deux mondes.

**Les filtres sont votre première ligne de défense sur les coûts.** Sur un
entrepôt de 40 000 tables dont 35 000 sont des tables temporaires générées
par des jobs, ingérer tout revient à noyer les 5 000 utiles.

### `workflowConfig` — la connexion au serveur

```yaml
workflowConfig:
  openMetadataServerConfig:
    hostPort: http://openmetadata-server:8585/api    # ← le /api final !
    authProvider: openmetadata
    securityConfig:
      jwtToken: ${OM_TOKEN}
```

L'oubli du suffixe `/api` est l'erreur numéro un sur ce produit. Elle produit
un 404 ou un 401 selon les versions, jamais un message clair.

## 2. Les `${PLACEHOLDERS}`

Vous avez remarqué : le fichier ne contient ni mot de passe ni jeton en clair,
mais `${OMLAB_PG_PASSWORD}` et `${OM_TOKEN}`. C'est une convention **de ce
tutoriel**, pas d'OpenMetadata : `./omlab ingest` fait passer le fichier par
[`scripts/render_yaml.py`](../scripts/render_yaml.py), qui remplace les
variables depuis `.env` et écrit le résultat dans `tmp/` (ignoré par git).

En production, on utilise plutôt un *secrets manager* (AWS Secrets Manager,
Azure Key Vault…), qu'OpenMetadata sait interroger nativement — voir le
chapitre 16.

## 3. Exécuter

```bash
./omlab ingest tp/04-ingestion/metadata.yaml
```

Le workflow commence par tester la connexion, étape par étape :

```
Running CheckAccess...      Running GetSchemas...     Running GetViews...
Running GetDatabases...     Running GetTables...      Running GetTableComments...
```

C'est précieux au débogage : si `CheckAccess` passe mais que `GetSchemas`
échoue, le problème est un droit manquant, pas un mot de passe faux.

Puis le résumé :

```
Workflow Postgres Summary:
Processed records: 13      ← entités produites par la source
Filtered: 2                ← écartées par vos filtres
Errors: 0
Workflow Success %: 100.0
```

> **Lisez toujours `Filtered`.** Un `Processed: 0, Filtered: 12000` veut dire
> que votre expression régulière ne matche rien. Le workflow affichera
> pourtant fièrement « Success 100 % » : il a parfaitement réussi à ne rien
> faire.

## 4. UI ou YAML ?

Les deux chemins mènent au même endroit — l'UI **génère** un YAML et le fait
exécuter par Airflow.

| | UI | YAML + CLI |
|---|---|---|
| Découverte, premier essai | ✅ formulaires, test de connexion | ❌ |
| Planification | ✅ intégrée (cron) | ❌ à faire soi-même |
| Revue de code, versionnage | ❌ | ✅ |
| Reproductible d'un environnement à l'autre | ❌ | ✅ |
| CI/CD | ❌ | ✅ |

En pratique : on explore dans l'UI, on industrialise en YAML. Ce tutoriel est
en YAML parce que c'est ce qui se versionne, se relit et se rejoue.

### Faire la même chose dans l'UI

Cela vaut la peine de le faire une fois, pour voir le formulaire :
*Settings → Services → Databases → Add New Service → Postgres*, puis
*Add Ingestion*. Le bouton **Test Connection** rejoue exactement les étapes
vues plus haut. Une fois déployé, le workflow apparaît dans Airflow
(http://localhost:8080) sous forme de DAG.

## 5. Ce qui a réellement été créé

```bash
./omlab py tp/14-sdk/01_lecture.py
```

```
Table      : omlab_postgres.omlab.raw.customers
Type       : Regular
Description: Clients de la boutique, un enregistrement par client.
Version    : 0.2

Colonnes :
  customer_id    INT        PRIMARY_KEY  tags: —
  email          VARCHAR    NULL         tags: PII.Sensitive
  ...
```

Notez ce que le connecteur a rapatrié sans qu'on lui demande : les types, les
contraintes (`PRIMARY_KEY`, `NOT_NULL`), et les commentaires SQL transformés
en descriptions.

---

## TP guidé

1. Relancez l'ingestion et observez `Processed`/`Filtered`.
2. **Cassez volontairement un filtre.** Remplacez `"^raw$"` par `"^raws$"`,
   relancez, et lisez le résumé. Combien de `Processed` ? Combien de
   `Filtered` ? Le workflow est-il en échec ?
3. Remettez le filtre correct.
4. Ajoutez une table à la base et réingérez :
   ```bash
   ./omlab psql "CREATE TABLE raw.fournisseurs (id int PRIMARY KEY, nom text)"
   ./omlab ingest tp/04-ingestion/metadata.yaml
   ```
   Elle doit apparaître dans le catalogue.
5. Supprimez-la, réingérez, et cherchez-la dans l'UI : elle est marquée
   supprimée, pas disparue (`markDeletedTables`).
   ```bash
   ./omlab psql "DROP TABLE raw.fournisseurs"
   ./omlab ingest tp/04-ingestion/metadata.yaml
   ```

**Vérifier :** `./omlab check 04`

## Exercices

1. Écrivez un filtre qui ingère `raw` **sauf** la table `employees`.
2. Configurez le même service depuis l'UI, avec le nom `omlab_postgres_ui`.
   Comparez les FQN obtenus. Que se passerait-il si vous aviez repris le même
   `serviceName` ?
3. Dans le YAML, passez `includeViews` à `false` et réingérez. Qu'advient-il
   des deux vues déjà cataloguées ?
4. Planifiez l'ingestion toutes les heures depuis l'UI et retrouvez le DAG
   correspondant dans Airflow.

## Pièges & FAQ

**« Success 100 %, mais rien dans le catalogue. »**
Regardez `Filtered`. Vos motifs ne matchent probablement rien. Testez-les :
`python3 -c "import re; print(re.match('^raw$', 'raw'))"`.

**« `Connection refused` alors que `./omlab psql` marche. »**
`psql` tourne depuis votre machine, le workflow depuis un conteneur. Utilisez
`omlab-postgres:5432`, jamais `localhost:5433`.

**« Faut-il un workflow par base ? »**
`ingestAllDatabases: true` permet d'en balayer plusieurs d'un coup — pratique,
mais on perd le contrôle fin des filtres. Sur un gros serveur, préférez un
workflow par base : les échecs restent isolés et les durées restent lisibles.

**« À quelle fréquence ingérer ? »**
Les métadonnées bougent peu : une fois par jour suffit presque toujours. Le
profiler et les tests, eux, coûtent cher — voir les chapitres 05 et 10.

## Pour aller plus loin

- [Connecteur Postgres](https://docs.open-metadata.org/v1.13.x/connectors/database/postgres)
- [Ingestion en ligne de commande](https://docs.open-metadata.org/v1.13.x/connectors/ingestion/workflows/metadata)

---

**Précédent :** [03 — Le catalogue](03-catalogue-decouverte.md) ·
**Suivant :** [05 — Profiling](05-profiler.md)
