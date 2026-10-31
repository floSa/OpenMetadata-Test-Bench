#!/usr/bin/env python3
"""Chapitre 22 — l'organisation : hiérarchie d'équipes, personas, droits vérifiés.

    ./omlab py tp/22-administration/01_organisation.py
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()


def equipe(nom: str, type_equipe: str, parent: str | None = None) -> dict:
    corps = {"name": nom, "teamType": type_equipe}
    if parent:
        corps["parents"] = [api(f"/teams/name/{parent}", token=admin)["id"]]
    return api("/teams", method="PUT", token=admin, body=corps)


# BusinessUnit > Division > Department > Group : seul un Group peut posséder des assets.
equipe("Commerce", "BusinessUnit")
equipe("Europe", "Division", "Commerce")
equipe("Marketing", "Department", "Europe")
groupe = equipe("Crm", "Group", "Marketing")
chemin = api("/teams/name/Crm?fields=parents", token=admin)
print(f"Équipe Crm : type {chemin['teamType']}, parent {[p['name'] for p in chemin['parents']]}")

# Le serveur fait respecter la hiérarchie : un Department ne peut pas chapeauter une Division.
try:
    api(f"/teams/{groupe['id']}", method="PATCH", token=admin,
        content_type="application/json-patch+json",
        body=[{"op": "replace", "path": "/teamType", "value": "Division"}])
    print("Group vers Division : accepté")
except SystemExit as err:
    print(f"Group vers Division : {str(err).splitlines()[1][:120]}")

relectrice = api("/users/name/relectrice", token=admin)
persona = api("/personas", method="PUT", token=admin, body={
    "name": "DataSteward", "displayName": "Data Steward",
    "description": "Gouvernance et glossaires d'abord.",
    "users": [relectrice["id"]],
})
persona = api(f"/personas/{persona['id']}?fields=users", token=admin)
print(f"Persona    : {persona['name']}, utilisateurs {[u['name'] for u in persona['users']]}")

# Le débogueur de permissions répond sans rien tenter pour de vrai.
print("\nDébogueur de permissions pour la relectrice, sur raw.customers :")
ressource = fqn("raw", "customers")
for operation in ("ViewBasic", "ViewSampleData", "EditDescription", "Delete"):
    r = api(f"/permissions/debug/evaluate?user=relectrice&resource=table&resourceId={ressource}&operation={operation}", token=admin)
    print(f"  {operation:<16} {'autorisé' if r['allowed'] else 'refusé'}")
