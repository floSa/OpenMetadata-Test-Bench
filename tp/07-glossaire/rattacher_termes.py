#!/usr/bin/env python3
"""Chapitre 07 — rattacher les termes du glossaire aux données.

    ./omlab py tp/07-glossaire/rattacher_termes.py

Un glossaire que personne ne relie aux tables reste un joli document mort.
Toute la valeur vient du rattachement : à partir de là, chercher « Chiffre
d'affaires » dans la barre de recherche ramène les colonnes concernées,
et ouvrir une colonne affiche la définition officielle.

Ce script utilise du JSON Patch, le mécanisme d'écriture partielle
d'OpenMetadata (chapitre 13). Deux raisons de le préférer à un PUT :
  * on ne réécrit que le champ visé, donc on n'écrase pas le travail
    d'un collègue sur le reste de l'entité ;
  * chaque patch produit une entrée d'historique lisible dans l'UI.
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn

# Quel terme sur quelle colonne. C'est ce tableau qui mérite la revue en
# équipe, pas le code qui l'applique.
RATTACHEMENTS = [
    ("raw", "customers", "customer_id", "Commerce.Client"),
    ("raw", "customers", "email", "Commerce.Client"),
    ("raw", "orders", "order_id", "Commerce.Commande"),
    ("raw", "orders", "amount", "Commerce.ChiffreAffaires"),
    ("analytics", "fct_orders", "amount", "Commerce.ChiffreAffaires"),
    ("analytics", "fct_orders", "is_credit_note", "Commerce.Avoir"),
    ("analytics", "v_revenue_monthly", "revenue", "Commerce.ChiffreAffaires"),
]


def patch_column_tag(schema: str, table: str, column: str, term_fqn: str) -> str:
    table_fqn = fqn(schema, table)
    entity = api(f"/tables/name/{table_fqn}?fields=columns,tags")

    index = next(
        (i for i, c in enumerate(entity["columns"]) if c["name"] == column), None
    )
    if index is None:
        return f"colonne {column} introuvable dans {table_fqn}"

    existing = [t["tagFQN"] for t in entity["columns"][index].get("tags", [])]
    if term_fqn in existing:
        return "déjà rattaché"

    # Le point clé : source = "Glossary". Avec source = "Classification",
    # OpenMetadata chercherait une étiquette de classification du même nom
    # et refuserait le patch.
    patch = [
        {
            "op": "add",
            "path": f"/columns/{index}/tags/-",
            "value": {
                "tagFQN": term_fqn,
                "source": "Glossary",
                "labelType": "Manual",
                "state": "Confirmed",
            },
        }
    ]
    api(
        f"/tables/{entity['id']}",
        method="PATCH",
        body=patch,
        content_type="application/json-patch+json",
    )
    return "rattaché"


for schema, table, column, term in RATTACHEMENTS:
    status = patch_column_tag(schema, table, column, term)
    print(f"  {schema}.{table}.{column:16} <- {term:28} {status}")

# ---------------------------------------------------------------------
# Vérification : le terme connaît-il ses assets ?
# ---------------------------------------------------------------------
# La relation est bidirectionnelle. Depuis le terme, OpenMetadata sait
# lister tout ce qui le porte : c'est ce qui permet de répondre à
# « où est calculé notre chiffre d'affaires ? ».
print("\nAssets portant le terme Commerce.ChiffreAffaires :")
result = api(
    "/search/query?q=*&index=table_search_index&size=50"
    "&query_filter=" + '{"query":{"term":{"columns.tags.tagFQN":"Commerce.ChiffreAffaires"}}}'
)
for hit in result.get("hits", {}).get("hits", []):
    print(f"  {hit['_source']['fullyQualifiedName']}")
