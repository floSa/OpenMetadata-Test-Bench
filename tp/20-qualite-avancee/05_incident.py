#!/usr/bin/env python3
"""Chapitre 20 — faire vivre un incident : pris en compte, assigné, résolu.

    ./omlab py tp/20-qualite-avancee/05_incident.py
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()
CAS = f"{fqn('raw', 'customers')}.country.customers_pays_renseigne"
ROUTE = "/dataQuality/testCases/testCaseIncidentStatus"
PERIODE = "startTs=0&endTs=99999999999999"


def etapes() -> list[dict]:
    res = api(f"{ROUTE}?testCaseFQN={CAS}&{PERIODE}&latest=false&limit=50")["data"]
    return sorted(res, key=lambda e: e["timestamp"])


cmartin = api("/users/name/cmartin")
print(f"Avant : {[e['testCaseResolutionStatusType'] for e in etapes()]}")

if etapes()[-1]["testCaseResolutionStatusType"] != "Resolved":
    api(ROUTE, method="POST", token=admin, body={
        "testCaseReference": CAS, "testCaseResolutionStatusType": "Ack", "severity": "Severity2",
    })
    api(ROUTE, method="POST", token=admin, body={
        "testCaseReference": CAS, "testCaseResolutionStatusType": "Assigned",
        "testCaseResolutionStatusDetails": {
            "assignee": {"id": cmartin["id"], "type": "user", "name": "cmartin"},
        },
    })
    api(ROUTE, method="POST", token=admin, body={
        "testCaseReference": CAS, "testCaseResolutionStatusType": "Resolved",
        "testCaseResolutionStatusDetails": {
            "resolvedBy": {"id": cmartin["id"], "type": "user", "name": "cmartin"},
            "testCaseFailureReason": "MissingData",
            "testCaseFailureComment": "Import de 2023 sans colonne pays. Reprise prévue.",
        },
    })

print(f"Après : {[e['testCaseResolutionStatusType'] for e in etapes()]}")
final = etapes()[-1]
print(f"Cause : {final['testCaseResolutionStatusDetails'].get('testCaseFailureReason')}")
