# Chapitre 11 — Lineage manuel et analyse d'impact

> **Objectifs** — Compléter à la main ce que le parseur SQL ne peut pas voir,
> décrire une correspondance colonne à colonne, et se servir du graphe pour
> décider.
> **Durée** — 35 minutes.

---

## 1. Pourquoi le manuel reste indispensable

Le chapitre 06 a produit un lineage riche, sans rien écrire. Mais il ne voit
que ce qui passe par du SQL exécuté sur une base qu'OpenMetadata sait
interroger. Tout le reste lui échappe :

- un job Spark ou pandas qui lit un fichier et écrit une table ;
- un export manuel vers un tableur qu'une équipe utilise tous les mois ;
- une procédure stockée trop dynamique pour être analysée ;
- une copie entre deux systèmes que le catalogue ne connaît pas encore.

Le lineage manuel est le filet. Et comme tout filet, il n'a de valeur que si
quelqu'un le maintient — un lineage manuel jamais mis à jour est un mensonge
avec l'apparence de la vérité.

## 2. La règle qui gouverne tout

> **Le lineage manuel n'est jamais écrasé par le lineage automatique.**

Chaque arête porte une `source` : `QueryLineage` (déduite), `ViewLineage`
(définition de vue), `Manual` (vous), `DbtLineage`… Le workflow automatique
ne touche pas aux arêtes manuelles. Votre correction survit à toutes les
réexécutions.

C'est ce qui rend la démarche viable : on laisse la machine faire 90 %, on
corrige les 10 % restants une fois pour toutes.

## 3. Le TP

```bash
./omlab py tp/11-lineage/lineage_manuel.py
```

Le script fait le tour complet :

```
=== 1. Lineage automatique en place ===
  raw.customers -> analytics.fct_orders   source=QueryLineage
      country -> customer_country
  raw.orders    -> analytics.fct_orders   source=QueryLineage
      amount -> amount
      customer_id -> customer_id
      amount -> is_credit_note
      ... et 4 autres correspondances

=== 2. Suppression de l'arête raw.orders -> analytics.fct_orders ===
  Arêtes entrantes restantes : ['customers']

=== 3. Recréation manuelle avec correspondance de colonnes ===
  Recréée : 7 correspondances, source=Manual
```

### L'API de lineage

Elle raisonne en **entités génériques**, pas en tables. La même route relie
une table à un tableau de bord ou à un topic Kafka :

```
GET    /api/v1/lineage/table/name/{fqn}?upstreamDepth=3&downstreamDepth=3
PUT    /api/v1/lineage
DELETE /api/v1/lineage/{type}/{id}/{type}/{id}
```

La charge utile d'un `PUT` :

```python
{
  "edge": {
    "fromEntity": {"id": amont_id, "type": "table"},
    "toEntity":   {"id": aval_id,  "type": "table"},
    "lineageDetails": {
      "columnsLineage": [
        {"fromColumns": ["...raw.orders.amount"],
         "toColumn":    "...analytics.fct_orders.is_credit_note"}
      ],
      "sqlQuery": "INSERT INTO analytics.fct_orders SELECT ..., o.amount < 0 ...",
      "description": "Alimentation quotidienne de la table de faits."
    }
  }
}
```

Trois remarques sur ce payload.

**`fromColumns` est une liste.** Une colonne cible peut dériver de plusieurs
sources : `full_name` vient de `first_name` **et** `last_name`. C'est
exactement ce qu'il faut décrire.

**`sqlQuery` et `description` ne sont pas décoratifs.** Ils répondent à la
question que se posera le prochain collègue : *d'où sort `is_credit_note` ?*
Une flèche seule dit qu'il y a un lien ; ces champs disent lequel.

**Les FQN de colonnes sont complets** : `service.base.schéma.table.colonne`.

## 4. L'analyse d'impact

C'est l'usage qui justifie tout le reste. Avant de modifier `raw.orders` :

```bash
curl -s -H "Authorization: Bearer $OM_TOKEN" \
  "localhost:8585/api/v1/lineage/table/name/omlab_postgres.omlab.raw.orders?upstreamDepth=0&downstreamDepth=5" \
  | jq '.nodes[].fullyQualifiedName'
```

Dans l'UI, le bouton **Impact Analysis** de l'onglet Lineage fait la même
chose visuellement, et affiche aussi les tableaux de bord et pipelines en
aval — pas seulement les tables.

Le réflexe à prendre : **avant toute migration, on regarde l'aval**. Cinq
minutes de graphe évitent la réunion de crise du lendemain.

---

## TP guidé

```bash
./omlab py tp/11-lineage/lineage_manuel.py
```

1. Dans l'UI, ouvrez `analytics.fct_orders`, onglet **Lineage**. L'arête depuis
   `raw.orders` est marquée manuelle.
2. Activez la vue colonne à colonne et suivez `amount → is_credit_note`.
3. Cliquez sur l'arête : la requête SQL et la description s'affichent.
4. **Vérifiez que le manuel résiste** :
   ```bash
   ./omlab traffic
   ./omlab ingest tp/06-usage-lineage/lineage.yaml
   ./omlab py tp/11-lineage/lineage_manuel.py
   ```
   L'arête est toujours `Manual`.
5. Ajoutez une arête entièrement à la main depuis l'UI : bouton **Edit** de
   l'onglet Lineage, puis glissez une entité.

**Vérifier :**

```bash
./omlab check 11
```

```
Chapitre 11 — Lineage manuel
  OK   au moins une arête est manuelle (sources : {'QueryLineage', 'Manual'})
```

## Exercices

1. Déclarez le lineage d'un job externe : créez une table
   `analytics.export_finance`, et déclarez qu'elle vient de
   `analytics.v_revenue_monthly` sans qu'aucun SQL ne l'ait produite.
2. Écrivez un script qui liste toutes les tables **sans aucun lineage** — ni
   amont ni aval. Ce sont vos angles morts.
3. Supprimez une arête depuis l'UI et retrouvez la trace de la suppression.
4. Créez un service de pipelines et une entité `Pipeline`, puis intercalez-la
   sur une arête pour documenter *par quoi* passe la transformation.

## Pièges & FAQ

**« Mon arête manuelle a disparu après une ingestion. »**
Vérifiez sa `source` : si elle vaut `QueryLineage`, c'est qu'elle a été
recréée automatiquement, pas préservée. Une arête créée via `PUT /lineage`
sans `lineageDetails.source` explicite est bien marquée `Manual` — c'est ce
qu'on observe dans le TP.

**« Faut-il décrire toutes les colonnes ? »**
Non. Concentrez-vous sur celles qui portent une règle métier ou une donnée
sensible. Une correspondance `id → id` n'apprend rien à personne.

**« Comment gérer un lineage massif ? »**
Par script, depuis votre orchestrateur : c'est lui qui sait ce qu'il a lu et
écrit. Un job Airflow ou Spark peut déclarer son lineage en fin d'exécution —
c'est bien plus fiable qu'une saisie humaine.

## Pour aller plus loin

- [Lineage](https://docs.open-metadata.org/v1.13.x/how-to-guides/data-lineage)

---

**Précédent :** [10 — Qualité](10-data-quality.md) ·
**Suivant :** [12 — Alertes et webhooks](12-alertes-webhooks.md)
