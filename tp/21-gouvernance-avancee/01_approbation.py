#!/usr/bin/env python3
"""Chapitre 21 — un glossaire avec relecteur : le terme attend son approbation.

    ./omlab py tp/21-gouvernance-avancee/01_approbation.py

Si l'auteur est lui-même relecteur, le workflow approuve d'office et aucune tâche
n'apparaît : ici, admin écrit le terme et un second compte le relit, avec sa propre
session. Le terme repart de zéro à chaque passage : tout PUT relance le workflow,
et la nouvelle instance annule la tâche de la précédente.
"""

import base64
import sys
import time

sys.path.insert(0, "/omlab")

from lib.om import api, jeton_admin

admin = jeton_admin()
MOT_DE_PASSE = "Relecture-2026!tuto"
EMAIL = "relectrice@omlab.example"


def statut(terme: dict) -> str:
    return api(f"/glossaryTerms/{terme['id']}", token=admin)["entityStatus"]


def attendre(condition, essais: int = 30):
    """Le workflow tourne en tâche de fond : son effet arrive quelques secondes plus tard."""
    for _ in range(essais):
        resultat = condition()
        if resultat:
            return resultat
        time.sleep(2)
    raise SystemExit("Le workflow n'a pas abouti à temps.")


try:
    relectrice = api("/users/name/relectrice", token=admin)
except SystemExit:
    relectrice = api("/users", method="POST", token=admin, body={
        "name": "relectrice", "email": EMAIL, "displayName": "Relectrice du tuto",
        "isAdmin": False, "createPasswordType": "ADMIN_CREATE",
        "password": MOT_DE_PASSE, "confirmPassword": MOT_DE_PASSE,
    })
session = api("/users/login", method="POST", token="sans-objet", body={
    "email": EMAIL, "password": base64.b64encode(MOT_DE_PASSE.encode()).decode(),
})["accessToken"]

api("/glossaries", method="PUT", token=admin, body={
    "name": "Finance",
    "description": "Vocabulaire de la direction financière. Tout nouveau terme est relu.",
    "reviewers": [{"id": relectrice["id"], "type": "user"}],
})
try:
    ancien = api("/glossaryTerms/name/Finance.MargeBrute", token=admin)
    api(f"/glossaryTerms/{ancien['id']}?hardDelete=true&recursive=true", method="DELETE", token=admin)
except SystemExit:
    pass

terme = api("/glossaryTerms", method="POST", token=admin, body={
    "glossary": "Finance",
    "name": "MargeBrute",
    "displayName": "Marge brute",
    "description": "Chiffre d'affaires moins coût des marchandises vendues.",
})
print(f"Terme créé : {terme['fullyQualifiedName']}, statut {terme['entityStatus']}")


def tache_ouverte() -> dict | None:
    # Le type réel est RequestApproval : l'énumération GlossaryApproval n'est pas utilisée ici.
    taches = api("/tasks?limit=100", token=admin)["data"]
    return next((t for t in taches if t["type"] == "RequestApproval" and t["status"] == "Open"
                 and t["about"]["id"] == terme["id"]), None)


tache = attendre(tache_ouverte)
print(f"Tâche      : {tache['taskId']} ({tache['type']}), assignée à {[a['name'] for a in tache['assignees']]}")
print(f"Statut     : {statut(terme)}")

api(f"/tasks/{tache['id']}/resolve", method="POST", token=session, body={
    "resolutionType": "Approved", "comment": "Définition validée.",
})
attendre(lambda: statut(terme) == "Approved")
print(f"Après relecture : {statut(terme)}")

instances = api("/governance/workflowInstances?startTs=0&endTs=99999999999999&limit=50"
                "&workflowDefinitionName=GlossaryTermApprovalWorkflow", token=admin)["data"]
instance = next(i for i in instances if i["variables"].get("global_relatedEntityId") == terme["id"])
etapes = api(f"/governance/workflowInstanceStates/GlossaryTermApprovalWorkflow/{instance['id']}"
             "?startTs=0&endTs=99999999999999", token=admin)["data"]
print("\nÉtapes du workflow :")
for etape in sorted(etapes, key=lambda e: e["timestamp"]):
    print(f"  {etape['stage']['name']}")
