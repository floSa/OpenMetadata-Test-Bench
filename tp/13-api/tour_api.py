#!/usr/bin/env python3
"""Chapitre 13 — l'API REST, sans SDK.

    ./omlab py tp/13-api/tour_api.py

Tout ce que fait l'UI passe par cette API. Tout ce que fait le SDK aussi.
La comprendre, c'est cesser d'être bloqué dès que le SDK ne couvre pas un
besoin — et c'est aussi la seule façon d'intégrer OpenMetadata depuis un
langage qui n'a pas de SDK.

Cinq idées suffisent :
  1. le FQN sert d'identifiant lisible, en plus de l'UUID ;
  2. `fields` décide de ce qu'on charge (rien n'est chargé par défaut) ;
  3. PUT écrase, PATCH modifie chirurgicalement ;
  4. la recherche ne passe PAS par la même route que la lecture ;
  5. tout est versionné, et l'historique est interrogeable.
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn

TABLE_FQN = fqn("raw", "products")

# ---------------------------------------------------------------------
# 1. Lire — et le rôle décisif de `fields`
# ---------------------------------------------------------------------
print("=== 1. GET, avec et sans `fields` ===")
maigre = api(f"/tables/name/{TABLE_FQN}")
gras = api(f"/tables/name/{TABLE_FQN}?fields=tags,owners,followers,usageSummary,profile")

print(f"  sans fields : {len(maigre)} clés")
print(f"  avec fields : {len(gras)} clés")
print(f"  champs gagnés : {sorted(set(gras) - set(maigre))}")
# Nuance qui surprend : `columns` fait partie du socle renvoyé d'office
# pour une table. En revanche tags, owners, usageSummary et profile sont
# des jointures coûteuses, donc absentes tant qu'on ne les demande pas.
print(f"  colonnes déjà là sans les demander ? {'columns' in maigre}")
print("  Sur un catalogue de 50 000 tables, chaque champ demandé est une")
print("  jointure de plus. `fields` n'est pas un détail de confort.")

# ---------------------------------------------------------------------
# 2. Écrire — PATCH plutôt que PUT
# ---------------------------------------------------------------------
print("\n=== 2. PATCH : ne toucher qu'un champ ===")
# Un PUT exigerait de renvoyer l'entité ENTIÈRE. Deux conséquences :
#   * tout champ oublié est effacé ;
#   * on écrase le travail d'un collègue fait entre-temps.
# Le PATCH décrit l'intention, pas l'état final (RFC 6902).
avant = maigre.get("description")
version_avant = maigre["version"]
api(
    f"/tables/{maigre['id']}",
    method="PATCH",
    body=[
        {
            "op": "add" if not avant else "replace",
            "path": "/description",
            "value": "Catalogue produits. Attention : le SKU n'est pas unique "
                     "(cf. test products_sku_unique).",
        }
    ],
    content_type="application/json-patch+json",
)
apres = api(f"/tables/name/{TABLE_FQN}")
print(f"  description : {apres['description'][:70]}...")
print(f"  version     : {version_avant} -> {apres['version']}")
# Une écriture qui change réellement quelque chose incrémente la version.
# Un patch qui réécrit la même valeur ne l'incrémente PAS : au deuxième
# lancement de ce script, la version ne bouge plus. Une écriture inutile
# ne pollue donc pas l'historique — propriété précieuse pour un script
# qu'on rejoue tous les jours.

# ---------------------------------------------------------------------
# 3. L'historique des versions
# ---------------------------------------------------------------------
print("\n=== 3. Historique ===")
versions = api(f"/tables/{maigre['id']}/versions")
print(f"  {len(versions['versions'])} version(s) enregistrée(s)")
for v in versions["versions"][:3]:
    import json as _json
    data = _json.loads(v) if isinstance(v, str) else v
    change = data.get("changeDescription") or {}
    champs = [f["name"] for f in change.get("fieldsUpdated", []) + change.get("fieldsAdded", [])]
    print(f"    v{data.get('version')} par {data.get('updatedBy'):14} champs={champs}")

# ---------------------------------------------------------------------
# 4. La recherche : une autre route, un autre moteur
# ---------------------------------------------------------------------
print("\n=== 4. Recherche (Elasticsearch, pas la base) ===")
# /tables interroge la base relationnelle : exact, lent à filtrer.
# /search/query interroge l'index : approximatif, rapide, avec pertinence.
# C'est pour ça qu'une entité fraîchement créée peut mettre un instant à
# apparaître dans la recherche : l'indexation est asynchrone.
resultats = api("/search/query?q=commande&index=table_search_index&size=5")
print(f"  {resultats['hits']['total']['value']} résultat(s) pour « commande » :")
for hit in resultats["hits"]["hits"]:
    print(f"    {hit['_score']:6.2f}  {hit['_source']['fullyQualifiedName']}")

# ---------------------------------------------------------------------
# 5. Pagination
# ---------------------------------------------------------------------
print("\n=== 5. Pagination par curseur ===")
# Pas d'offset : un curseur opaque (`after`). C'est ce qui permet de
# parcourir un gros catalogue sans que l'insertion d'une entité en cours
# de route ne décale tout.
page = api("/tables?limit=4")
print(f"  page 1 : {[t['name'] for t in page['data']]}")
if page["paging"].get("after"):
    page2 = api(f"/tables?limit=4&after={page['paging']['after']}")
    print(f"  page 2 : {[t['name'] for t in page2['data']]}")
print(f"  total  : {page['paging']['total']} tables")
