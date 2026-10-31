#!/usr/bin/env python3
"""Chapitre 18 — le jeton personnel : agir en son nom, sans mot de passe.

    ./omlab py tp/18-collaboration/04_jeton_personnel.py
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, jeton_admin

admin = jeton_admin()
cree = api("/users/security/token", method="PUT", token=admin, body={
    "tokenName": "tuto_chapitre_18",
    "JWTTokenExpiry": "7",
})
print(f"Jeton : {cree['tokenName']} ({cree['tokenType']})")
print(f"Agit en tant que : {api('/users/loggedInUser', token=cree['jwtToken'])['name']}")

# On retire tous les jetons de ce TP, y compris ceux d'un passage précédent.
existants = api("/users/security/token", token=admin)["data"]
api("/users/security/token/revoke", method="PUT", token=admin, body={
    "tokenIds": [j["token"] for j in existants if j["tokenName"] == "tuto_chapitre_18"],
})
restants = api("/users/security/token", token=admin)["data"]
print(f"Après révocation : {len(restants)} jeton(s) restant(s)")
try:
    api("/users/loggedInUser", token=cree["jwtToken"])
    print("Le jeton révoqué répond encore")
except SystemExit as err:
    print(f"Le jeton révoqué reçoit : HTTP {str(err).split()[1]}")
