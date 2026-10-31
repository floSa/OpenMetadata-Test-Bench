#!/usr/bin/env python3
"""Chapitre 19 — tout ce qui s'exporte, en tête de fichier.

    ./omlab py tp/19-import-export/03_autres_exports.py
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import fqn, jeton_admin, texte

admin = jeton_admin()
ORDERS = fqn("raw", "orders")

EXPORTS = {
    "Service entier": "/services/databaseServices/name/omlab_postgres/export",
    "Équipes": "/teams/name/Organization/export",
    "Tests d'une table": f"/dataQuality/testCases/name/{ORDERS}/export",
    "Métrique": "/metrics/name/ca_mensuel_net/export",
    "Lineage": f"/lineage/export?fqn={ORDERS}&type=table&upstreamDepth=1&downstreamDepth=1",
    "Colonnes du catalogue": "/columns/export",
    "Résultats de recherche": "/search/export?q=orders&index=table",
}
for titre, route in EXPORTS.items():
    lignes = texte(route, token=admin).splitlines()
    print(f"{titre:<24} {len(lignes) - 1:>4} lignes  [{lignes[0][:58]}...]")
