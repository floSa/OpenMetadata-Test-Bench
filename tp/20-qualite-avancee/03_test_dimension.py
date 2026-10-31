#!/usr/bin/env python3
"""Chapitre 20 — déclarer un test par segment, puis lire ses résultats segment par segment.

    ./omlab py tp/20-qualite-avancee/03_test_dimension.py
    ./omlab test tp/20-qualite-avancee/tests-dimension.yaml
    ./omlab py tp/20-qualite-avancee/03_test_dimension.py
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()
CUSTOMERS = fqn("raw", "customers")
CAS = f"{CUSTOMERS}.country.customers_pays_par_activite"

api("/dataQuality/testCases", method="PUT", token=admin, body={
    "name": "customers_pays_par_activite",
    "entityLink": f"<#E::table::{CUSTOMERS}::columns::country>",
    "testDefinition": "columnValuesToBeNotNull",
    "computePassedFailedRowCount": True,
    "dimensionColumns": ["is_active"],
})
cas = api(f"/dataQuality/testCases/name/{CAS}?fields=testCaseResult")
print(f"Test : {cas['name']}, découpé par {cas['dimensionColumns']}")
if "testCaseResult" not in cas:
    print("Pas encore de résultat : lancez le workflow, puis rejouez ce script.")
    raise SystemExit

r = cas["testCaseResult"]
print(f"Global : {r['testCaseStatus']}, {r.get('failedRows')} lignes en échec sur {r.get('passedRows', 0) + r.get('failedRows', 0)}")
periode = "startTs=0&endTs=99999999999999"
segments = api(f"/dataQuality/testCases/dimensionResults/{CAS}?dimensionName=is_active&{periode}")["data"]
dernier = {}
for s in sorted(segments, key=lambda s: s["timestamp"]):
    dernier[s["dimensionValues"][0]["value"]] = s
print("Par valeur de is_active :")
for valeur, s in sorted(dernier.items()):
    print(f"  {valeur:<12} {s['testCaseStatus']:<8} {s.get('failedRows', 0):>4} en échec sur {s.get('passedRows', 0) + s.get('failedRows', 0):>5}")
