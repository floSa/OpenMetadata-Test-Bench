#!/usr/bin/env python3
"""Chapitre 22 — fixer un objectif de documentation, et voir où on en est.

    ./omlab py tp/22-administration/03_kpi.py
"""

import sys
import time

sys.path.insert(0, "/omlab")

from lib.om import api, jeton_admin

admin = jeton_admin()
JOUR_MS = 86_400_000
maintenant = int(time.time() * 1000)

kpi = api("/kpi", method="PUT", token=admin, body={
    "name": "description_80_pourcent",
    "displayName": "80 % des assets décrits",
    "description": "Objectif de documentation du trimestre.",
    "dataInsightChart": "percentage_of_data_asset_with_description_kpi",
    "startDate": maintenant,
    "endDate": maintenant + 90 * JOUR_MS,
    "targetValue": 80,
    "metricType": "PERCENTAGE",
})
print(f"KPI : {kpi['name']}, cible {kpi['targetValue']} % ({kpi['metricType']})")
print(f"Graphique suivi : {kpi['dataInsightChart']['name']}")

graphiques = api("/analytics/dataInsights/charts?limit=50", token=admin)["data"]
print(f"\n{len(graphiques)} graphiques Data Insights, dont :")
for g in graphiques[:6]:
    print(f"  {g['name']}")
