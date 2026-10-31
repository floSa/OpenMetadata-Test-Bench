#!/usr/bin/env python3
"""Chapitre 21 — sous-domaine, formulaire imposé, règles d'instance, masquage des données sensibles.

    ./omlab py tp/21-gouvernance-avancee/03_regles.py

Le formulaire et la règle sont activés le temps de la démonstration, puis retirés :
laissés en place, ils bloqueraient les TP rejoués ensuite.
"""

import base64
import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()


def essai(route: str, corps: dict) -> str:
    try:
        api(route, method="PUT", token=admin, body=corps)
        return "accepté"
    except SystemExit as err:
        return str(err).split("\n", 1)[1][:150]


# --- Sous-domaine ---------------------------------------------------------------
sous = api("/domains", method="PUT", token=admin, body={
    "name": "VentesEurope", "description": "Les ventes du périmètre européen.",
    "domainType": "Consumer-aligned", "parent": "Ventes",
})
print(f"Sous-domaine : {sous['fullyQualifiedName']}")

# --- Formulaire imposé à la création des produits de données ----------------------
formulaires = api("/governance/intakeForms?limit=10", token=admin)["data"]
for ancien in formulaires:
    if ancien["name"] == "produit_avec_proprietaire":
        api(f"/governance/intakeForms/{ancien['id']}?hardDelete=true", method="DELETE", token=admin)
formulaire = api("/governance/intakeForms", method="POST", token=admin, body={
    "name": "produit_avec_proprietaire",
    "entityType": "dataProduct",
    "enabled": True,
    "requiredFields": [{"fieldPath": "owners", "fieldLabel": "Owners", "fieldKind": "native",
                        "errorMessage": "Un produit de données doit avoir un propriétaire."}],
})
produit = {"name": "essai_formulaire", "description": "Démonstration.", "domains": ["Ventes"]}
print(f"Produit sans propriétaire, formulaire actif : {essai('/dataProducts', produit)}")
api(f"/governance/intakeForms/{formulaire['id']}?hardDelete=true", method="DELETE", token=admin)
print(f"Formulaire retiré                           : {essai('/dataProducts', produit)}")
cree = api("/dataProducts/name/essai_formulaire", token=admin)
api(f"/dataProducts/{cree['id']}?hardDelete=true", method="DELETE", token=admin)

# --- Règles d'instance ------------------------------------------------------------
reglage = api("/system/settings/entityRulesSettings", token=admin)
print("\nRègles d'instance :")
for regle in reglage["config_value"]["entitySemantics"]:
    print(f"  {'actif  ' if regle['enabled'] else 'inactif'} {regle['name']}")

# --- Données d'échantillon et étiquette PII ---------------------------------------
table = api(f"/tables/name/{fqn('raw', 'customers')}?fields=columns,tags", token=admin)
sensibles = [c["name"] for c in table["columns"]
             if any(t["tagFQN"] == "PII.Sensitive" for t in c.get("tags") or [])]
print(f"\nColonnes PII.Sensitive de raw.customers : {sensibles}")
echantillon = api(f"/tables/{table['id']}/sampleData", token=admin)["sampleData"]
print(f"Vu par admin      : {dict(zip(echantillon['columns'], echantillon['rows'][0]))}")

# La relectrice du script 01 n'a aucun rôle particulier.
session = api("/users/login", method="POST", token="sans-objet", body={
    "email": "relectrice@omlab.example",
    "password": base64.b64encode(b"Relecture-2026!tuto").decode(),
})["accessToken"]
echantillon = api(f"/tables/{table['id']}/sampleData", token=session)["sampleData"]
print(f"Vu par la relectrice : {dict(zip(echantillon['columns'], echantillon['rows'][0]))}")
