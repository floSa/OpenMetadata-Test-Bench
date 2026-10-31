#!/usr/bin/env python3
"""Chapitre 20 — publier le résultat d'un outil externe sur un test maison.

    ./omlab py tp/20-qualite-avancee/01_test_externe.py

OpenMetadata n'exécute rien ici : `testPlatforms: ["Other"]` dit qu'un autre outil
fait le contrôle. Le catalogue centralise seulement son verdict.
"""

import sys
import time

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()
ORDERS = fqn("raw", "orders")
CAS = f"{ORDERS}.rapprochement_compta"

api("/dataQuality/testDefinitions", method="PUT", token=admin, body={
    "name": "rapprochementComptable",
    "description": "Écart entre le total des commandes et le grand livre.",
    "entityType": "TABLE",
    "testPlatforms": ["Other"],
    "parameterDefinition": [{"name": "ecartMax", "dataType": "INT", "required": True}],
})
api("/dataQuality/testCases", method="PUT", token=admin, body={
    "name": "rapprochement_compta",
    "entityLink": f"<#E::table::{ORDERS}>",
    "testDefinition": "rapprochementComptable",
    "parameterValues": [{"name": "ecartMax", "value": "100"}],
})
api(f"/dataQuality/testCases/testCaseResults/{CAS}", method="POST", token=admin, body={
    "timestamp": int(time.time() * 1000),
    "testCaseStatus": "Success",
    "result": "Écart de 12 EUR avec le grand livre.",
    "testResultValue": [{"name": "ecart", "value": "12"}],
})
resultat = api(f"/dataQuality/testCases/name/{CAS}?fields=testCaseResult")["testCaseResult"]
print(f"Test maison : {CAS.rsplit('.', 1)[-1]}")
print(f"  statut    : {resultat['testCaseStatus']}")
print(f"  message   : {resultat['result']}")
