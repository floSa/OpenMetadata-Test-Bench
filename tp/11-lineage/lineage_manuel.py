#!/usr/bin/env python3
"""Chapitre 11 — piloter le lineage à la main, via l'API.

    ./omlab py tp/11-lineage/lineage_manuel.py

Le lineage automatique du chapitre 06 est excellent... quand la
transformation est du SQL exécuté sur une base qu'OpenMetadata sait
interroger. Dès qu'un job Spark, un script Python ou un export manuel
entre en jeu, il ne voit plus rien. D'où ce chapitre.

Le script fait le tour complet en quatre temps :
  1. lire une relation existante et sa correspondance de colonnes ;
  2. la supprimer, et constater qu'elle disparaît ;
  3. la recréer à la main, avec une correspondance colonne à colonne ;
  4. montrer qu'un lineage manuel survit à une réexécution du workflow.
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, show

AMONT = fqn("raw", "orders")
AVAL = fqn("analytics", "fct_orders")


def get_ids() -> tuple[str, str]:
    return (
        api(f"/tables/name/{AMONT}")["id"],
        api(f"/tables/name/{AVAL}")["id"],
    )


def edges_vers_aval() -> list[dict]:
    """Renvoie les arêtes entrantes de la table aval."""
    graph = api(f"/lineage/table/name/{AVAL}?upstreamDepth=1&downstreamDepth=0")
    noms = {n["id"]: n["fullyQualifiedName"] for n in graph.get("nodes", [])}
    noms[graph["entity"]["id"]] = graph["entity"]["fullyQualifiedName"]
    return [
        {
            "de": noms.get(e["fromEntity"], e["fromEntity"]),
            "vers": noms.get(e["toEntity"], e["toEntity"]),
            "colonnes": (e.get("lineageDetails") or {}).get("columnsLineage") or [],
            "source": (e.get("lineageDetails") or {}).get("source"),
        }
        for e in graph.get("upstreamEdges", [])
    ]


# ---------------------------------------------------------------------
# 1. L'existant
# ---------------------------------------------------------------------
print("=== 1. Lineage automatique en place ===")
for e in edges_vers_aval():
    print(f"  {e['de']}  ->  {e['vers']}   source={e['source']}")
    for c in e["colonnes"][:3]:
        amont = ", ".join(x.split(".")[-1] for x in c["fromColumns"])
        print(f"      {amont}  ->  {c['toColumn'].split('.')[-1]}")
    if len(e["colonnes"]) > 3:
        print(f"      ... et {len(e['colonnes']) - 3} autres correspondances")

# ---------------------------------------------------------------------
# 2. Suppression
# ---------------------------------------------------------------------
# Note le format de l'URL : type/id/type/id. OpenMetadata raisonne en
# entités génériques, pas en tables — la même API relie une table à un
# tableau de bord ou à un topic Kafka.
print("\n=== 2. Suppression de l'arête raw.orders -> analytics.fct_orders ===")
amont_id, aval_id = get_ids()
api(f"/lineage/table/{amont_id}/table/{aval_id}", method="DELETE")
restantes = edges_vers_aval()
print(f"  Arêtes entrantes restantes : {[e['de'].split('.')[-1] for e in restantes]}")

# ---------------------------------------------------------------------
# 3. Recréation manuelle, colonne à colonne
# ---------------------------------------------------------------------
# C'est ici qu'on gagne vraiment quelque chose : on peut décrire une
# correspondance que le parser SQL n'aurait pas devinée. Ici, la colonne
# is_credit_note de fct_orders est dérivée de amount (amount < 0) : une
# règle métier, pas une copie de colonne.
print("\n=== 3. Recréation manuelle avec correspondance de colonnes ===")

CORRESPONDANCES = [
    (["order_id"], "order_id"),
    (["customer_id"], "customer_id"),
    (["order_date"], "order_date"),
    (["order_date"], "order_month"),   # dérivée : date_trunc('month', ...)
    (["status"], "status"),
    (["amount"], "amount"),
    (["amount"], "is_credit_note"),    # dérivée : amount < 0
]

payload = {
    "edge": {
        "fromEntity": {"id": amont_id, "type": "table"},
        "toEntity": {"id": aval_id, "type": "table"},
        "lineageDetails": {
            "columnsLineage": [
                {
                    "fromColumns": [f"{AMONT}.{c}" for c in sources],
                    "toColumn": f"{AVAL}.{cible}",
                }
                for sources, cible in CORRESPONDANCES
            ],
            # Documenter la transformation : c'est ce que lira le prochain
            # collègue qui se demandera d'où sort is_credit_note.
            "sqlQuery": (
                "INSERT INTO analytics.fct_orders SELECT ..., o.amount < 0 "
                "FROM raw.orders o JOIN raw.customers c USING (customer_id)"
            ),
            "description": "Alimentation quotidienne de la table de faits.",
        },
    }
}
api("/lineage", method="PUT", body=payload)

for e in edges_vers_aval():
    if e["de"] == AMONT:
        print(f"  Recréée : {len(e['colonnes'])} correspondances, source={e['source']}")

# ---------------------------------------------------------------------
# 4. La règle qui compte
# ---------------------------------------------------------------------
print(
    "\n=== 4. Ce qu'il faut retenir ===\n"
    "  Le champ `source` distingue ManualLineage d'un lineage déduit.\n"
    "  Une arête manuelle n'est jamais écrasée par une réexécution du\n"
    "  workflow automatique : votre correction survit. Vérifiez-le :\n"
    "      ./omlab traffic && ./omlab ingest tp/06-usage-lineage/lineage.yaml\n"
    "      ./omlab py tp/11-lineage/lineage_manuel.py\n"
)
