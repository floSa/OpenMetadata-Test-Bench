#!/usr/bin/env python3
"""Chapitre 20 — ajouter ses propres métriques au profiler, et régler son échantillonnage.

    ./omlab py tp/20-qualite-avancee/02_metrique_profil.py
    ./omlab profile tp/20-qualite-avancee/profiler-orders.yaml
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()
table = api(f"/tables/name/{fqn('raw', 'orders')}")

# Sans columnName, la métrique vaut pour la table ; avec, pour la colonne.
api(f"/tables/{table['id']}/customMetric", method="PUT", token=admin, body={
    "name": "commandes_annulees",
    "description": "Nombre de commandes annulées.",
    "expression": "SELECT COUNT(*) FROM raw.orders WHERE status = 'cancelled'",
})
api(f"/tables/{table['id']}/customMetric", method="PUT", token=admin, body={
    "name": "montant_des_avoirs",
    "columnName": "amount",
    "expression": "SELECT COALESCE(SUM(amount), 0) FROM raw.orders WHERE amount < 0",
})

# Ce réglage vit sur la table : il prime sur celui du workflow.
api(f"/tables/{table['id']}/tableProfilerConfig", method="PUT", token=admin, body={
    "profileSampleType": "PERCENTAGE",
    "profileSample": 100,
    "excludeColumns": ["currency"],
})
config = api(f"/tables/{table['id']}/tableProfilerConfig")["tableProfilerConfig"]
print(f"Réglage de la table : {config}")
metriques = api(f"/tables/{table['id']}?fields=customMetrics,columns")
print(f"Métriques de table  : {[m['name'] for m in metriques.get('customMetrics') or []]}")
amount = next(c for c in metriques["columns"] if c["name"] == "amount")
print(f"Métriques d'amount  : {[m['name'] for m in amount.get('customMetrics') or []]}")
