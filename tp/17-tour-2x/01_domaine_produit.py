#!/usr/bin/env python3
"""Chapitre 17 — un domaine, un produit de données et une métrique.

    ./omlab py tp/17-tour-2x/01_domaine_produit.py

Le domaine dit à qui appartient un périmètre, le produit de données dit ce que
ce périmètre publie, et la métrique dit comment un chiffre se calcule. Les trois
alimentent la page Data Marketplace.
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn

revenue = api(f"/tables/name/{fqn('analytics', 'v_revenue_monthly')}")
faits = api(f"/tables/name/{fqn('analytics', 'fct_orders')}")

domaine = api("/domains", method="PUT", body={
    "name": "Ventes",
    "displayName": "Ventes",
    "description": "Tout ce qui décrit les commandes et le chiffre d'affaires.",
    "domainType": "Consumer-aligned",
})
print(f"Domaine  : {domaine['fullyQualifiedName']} ({domaine['domainType']})")

produit = api("/dataProducts", method="PUT", body={
    "name": "ca_mensuel",
    "displayName": "Chiffre d'affaires mensuel",
    "description": "Le CA par mois et par pays, prêt à consommer.",
    "domains": ["Ventes"],
})
print(f"Produit  : {produit['fullyQualifiedName']}")

# Le champ `assets` de la création est ignoré sans erreur : les tables se rattachent
# d'abord au domaine, puis au produit, par ces deux routes dédiées.
assets = {"assets": [{"id": t["id"], "type": "table"} for t in (revenue, faits)]}
api("/domains/Ventes/assets/add", method="PUT", body=assets)
api("/dataProducts/ca_mensuel/assets/add", method="PUT", body=assets)

metrique = api("/metrics", method="PUT", body={
    "name": "ca_mensuel_net",
    "displayName": "CA mensuel net",
    "description": "Somme des montants des commandes terminées, hors avoirs.",
    "metricType": "SUM",
    "granularity": "MONTH",
    "unitOfMeasurement": "OTHER",
    "customUnitOfMeasurement": "EUR",
    "metricExpression": {
        "language": "SQL",
        "code": "SELECT sum(amount) FROM raw.orders WHERE status = 'completed' AND amount > 0",
    },
})
print(f"Métrique : {metrique['fullyQualifiedName']} ({metrique['metricType']}, {metrique['granularity']})")

relue = api(f"/tables/name/{fqn('analytics', 'v_revenue_monthly')}?fields=domains,dataProducts")
print("\nSur analytics.v_revenue_monthly :")
print(f"  domaine : {[d['name'] for d in relue.get('domains', [])]}")
print(f"  produit : {[p['name'] for p in relue.get('dataProducts', [])]}")
