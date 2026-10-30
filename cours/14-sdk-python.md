# Chapitre 14 — Le SDK Python

> **Objectifs** — Automatiser le catalogue avec du code typé : documenter en
> masse, attribuer des propriétaires, étendre le modèle.
> **Durée** — 45 minutes.

---

## 1. SDK ou API brute ?

| | SDK Python | API REST |
|---|---|---|
| Objets | typés (Pydantic), validés à l'écriture | dictionnaires |
| Erreurs | à l'écriture du code | au retour du serveur |
| Couverture | large, mais pas totale | totale |
| Autres langages | non | oui |

En pratique on mélange : le SDK pour la lecture et les écritures courantes,
l'API pour ce qu'il ne couvre pas. C'est exactement ce que fait
[`lib/om.py`](../lib/om.py), qui expose `client()` et `api()` côte à côte.

## 2. Se connecter

```python
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    AuthProvider, OpenMetadataConnection,
)
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.ingestion.ometa.ometa_api import OpenMetadata

config = OpenMetadataConnection(
    hostPort="http://openmetadata-server:8585/api",   # ← le /api, encore
    authProvider=AuthProvider.openmetadata,
    securityConfig=OpenMetadataJWTClientConfig(jwtToken=TOKEN),
)
om = OpenMetadata(config)
assert om.health_check()
```

Les imports sont interminables — c'est le prix des schémas générés. Dans ce
projet, tout cela est encapsulé :

```python
import sys; sys.path.insert(0, "/omlab")
from lib.om import client, api, fqn
om = client()
```

## 3. Lire

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
  first_name     VARCHAR    NOT_NULL     tags: PII.Sensitive
  ...
```

Trois méthodes suffisent pour 90 % des cas :

```python
om.get_by_name(entity=Table, fqn="...", fields=["columns", "tags", "owners"])
om.get_by_id(entity=Table, entity_id=uuid)
om.list_all_entities(entity=Table, limit=100)     # gère la pagination
```

**Attention à `list_entities` vs `list_all_entities`.** Le premier renvoie une
page ; le second est un générateur qui parcourt tout. Sur un vrai catalogue,
oublier la pagination donne « on n'a que 100 tables » — et une décision prise
sur des données fausses.

### Le typage n'est pas décoratif

`table.columns[0].dataType` est une énumération, pas une chaîne. Une faute de
frappe explose à l'écriture du script, pas en production. En contrepartie,
il faut souvent déballer : `table.fullyQualifiedName.root`,
`column.name.root`, `tag.tagFQN.root`. Le `.root` est la valeur nue derrière
le type Pydantic — on l'oublie une fois, on ne l'oublie plus.

## 4. Écrire

```bash
./omlab py tp/14-sdk/02_ecriture.py
```

```
=== 1. Descriptions ===
  raw.orders         documentée
  raw.order_items    documentée
  raw.products       documentée
  analytics.dim_customer   documentée

=== 2. Propriétaire ===
  raw.orders         appartient à Data Platform

=== 3. Propriété personnalisée ===
  propriété retentionMonths déclarée sur le type `table`
  raw.employees.retentionMonths = 60

=== 4. Criticité (Tier) ===
  analytics.v_revenue_monthly    -> Tier.Tier1
  raw.orders                     -> Tier.Tier1
  raw.products                   -> Tier.Tier3
```

### Documenter en masse

C'est **le** cas d'usage. Personne ne remplit 4 000 descriptions à la souris.
En revanche, la plupart des équipes ont déjà leurs définitions quelque part :
un tableur, des fichiers dbt, un wiki. Le script les déverse.

```python
om.patch_description(entity=Table, source=table, description=texte, force=True)
```

`force=True` écrase une description existante. **Sans lui**, une description
déjà présente est respectée — ce qui est le bon réglage pour un script
automatique qui ne doit pas écraser le travail des humains. Réfléchissez à
celui des deux que vous voulez avant de lancer sur 4 000 tables.

### Le propriétaire, champ le plus important du produit

« Qui appelle-t-on quand cette table casse ? » Sans réponse, le catalogue
reste un annuaire mort. C'est aussi le champ le plus souvent vide.

Un script qui attribue les propriétaires depuis votre référentiel d'équipes
(un CSV, votre annuaire, vos fichiers Terraform) vaut mieux que six mois de
relances par messagerie.

### Les propriétés personnalisées

Les champs natifs ne couvrent jamais tous les besoins. Les *custom properties*
étendent le **modèle lui-même** :

```python
# 1. déclarer la propriété sur le TYPE `table` (une fois)
api(f"/metadata/types/{type_table['id']}", method="PUT", body={
    "name": "retentionMonths",
    "description": "Durée de conservation réglementaire, en mois.",
    "propertyType": {"id": type_string["id"], "type": "type"},
})

# 2. la renseigner sur une entité, dans `extension`
api(f"/tables/{table_id}", method="PATCH", body=[
    {"op": "add", "path": "/extension", "value": {"retentionMonths": "60"}}
], content_type="application/json-patch+json")
```

Utile pour : durée de rétention, référence d'un ticket, code de centre de
coût, niveau de certification interne. La propriété apparaît ensuite dans
l'UI et devient filtrable dans la recherche.

### Le Tier

`Tier1` à `Tier5` n'est pas décoratif. C'est ce qui permet de filtrer les
alertes du chapitre 12, de prioriser l'effort de documentation, et de décider
ce qu'on surveille vraiment. Trente tables Tier1 bien tenues valent mieux que
4 000 tables tièdes.

## 5. Idempotence

Tous les scripts de ce tutoriel sont rejouables. C'est une discipline, pas une
propriété du SDK :

- utiliser `create_or_update` plutôt que `create` ;
- vérifier avant d'ajouter dans une liste (`if tier in existants: continue`) ;
- s'appuyer sur le fait qu'un patch sans changement n'incrémente pas la version.

Un script d'enrichissement du catalogue tourne tous les jours. S'il n'est pas
idempotent, il produit des doublons et un historique illisible.

---

## TP guidé

```bash
./omlab py tp/14-sdk/01_lecture.py
./omlab py tp/14-sdk/02_ecriture.py
```

1. Ouvrez `raw.orders` dans l'UI : description, propriétaire, Tier1 et terme de
   glossaire, tout est là.
2. Ouvrez `raw.employees` et trouvez `retentionMonths` dans l'onglet
   **Custom Properties**.
3. Relancez `02_ecriture.py` : rien ne change, aucune version créée.
4. Modifiez une description dans le script, relancez, et regardez le diff dans
   l'onglet Versions.

**Vérifier :**

```bash
./omlab check 14
```

```
Chapitre 14 — SDK Python
  OK   raw.orders est documentée
  OK   raw.orders a un propriétaire
  OK   raw.orders porte un niveau de criticité (['Tier.Tier1'])
```

## Exercices

1. Écrivez un script qui produit un **rapport de complétude** : pour chaque
   table, a-t-elle une description, un propriétaire, un Tier ? Sortez-le en CSV.
2. Écrivez un script qui documente les colonnes à partir d'un dictionnaire
   `{nom_de_colonne: description}` appliqué à **toutes** les tables — pour les
   colonnes techniques répétées partout (`created_at`, `updated_at`).
3. Ajoutez une propriété personnalisée `sourceSystem` et renseignez-la.
4. Écrivez un script qui attribue les propriétaires depuis un CSV
   `table,equipe`.
5. Faites tourner un de ces scripts avec un bot dédié (chapitre 09) et
   vérifiez la trace « modifié par ».

## Pièges & FAQ

**« `AttributeError: 'EntityName' object has no attribute 'lower'` »**
Vous manipulez un objet Pydantic comme une chaîne. Ajoutez `.root`.

**« Le SDK ne couvre pas ce que je veux. »**
Passez par `api()`. C'est prévu, et il n'y a aucune honte : `lib/om.py` expose
les deux exprès.

**« Faut-il installer le SDK localement ? »**
Pas nécessaire : `./omlab py` exécute dans le conteneur d'ingestion, qui l'a
déjà. Pour l'autocomplétion dans votre IDE :
`pip install "openmetadata-ingestion==1.13.6.0"`.

**« Comment tester mes scripts ? »**
Sur cette stack, précisément. `./omlab nuke && ./omlab up` remet un
environnement neuf en trois minutes — c'est le meilleur bac à sable possible
avant de lancer un script sur le catalogue de production.

## Pour aller plus loin

- [SDK Python](https://docs.open-metadata.org/v1.13.x/sdk/python)

---

**Précédent :** [13 — API REST](13-api-rest.md) ·
**Suivant :** [15 — Écrire un connecteur](15-connecteur-custom.md)
