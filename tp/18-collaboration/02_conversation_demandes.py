#!/usr/bin/env python3
"""Chapitre 18 — discuter sur un asset, demander une description et un tag, puis répondre.

    ./omlab py tp/18-collaboration/02_conversation_demandes.py
"""

import sys
import urllib.parse

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()
CUSTOMERS = fqn("raw", "customers")
LIEN = f"<#E::table::{CUSTOMERS}::columns::country>"

# Une conversation reste dans /v1/feed : seules annonces et tâches ont déménagé.
QUESTION = "Pourquoi 39 pays manquants ? Cela vient-il de l'import de 2023 ?"
fils = api(f"/feed?entityLink={urllib.parse.quote(LIEN)}&type=Conversation")["data"]
fil = next((f for f in fils if f["message"] == QUESTION), None)
if fil is None:
    fil = api("/feed", method="POST", token=admin, body={
        "message": QUESTION, "about": LIEN, "type": "Conversation",
    })
if not fil.get("postsCount"):
    api(f"/feed/{fil['id']}/posts", method="POST", token=admin, body={
        "message": "Oui, ce fichier n'avait pas de colonne pays.",
    })
fil = api(f"/feed/{fil['id']}")
print(f"Conversation : {fil['message']}")
print(f"  réponses   : {fil['postsCount']}")

taches = api("/tasks?limit=100")["data"]


def demande(nom: str, titre: str, type_tache: str, charge: dict) -> dict:
    existante = next((t for t in taches if t["name"] == nom), None)
    if existante:
        return existante
    return api("/tasks", method="POST", token=admin, body={
        "name": nom,
        "displayName": titre,
        "category": "MetadataUpdate",
        "type": type_tache,
        "about": f"<#E::table::{CUSTOMERS}>",
        "assignees": ["admin"],
        "payload": charge,
    })


description = demande(
    "decrire_customers_country", "Décrire raw.customers.country", "DescriptionUpdate",
    {"fieldPath": "columns::country::description", "currentDescription": "",
     "newDescription": "Pays du client, code ISO à deux lettres. Vide pour l'import de 2023."},
)
etiquette = demande(
    "etiqueter_customers_email", "Étiqueter raw.customers.email", "TagUpdate",
    {"fieldPath": "columns::email::tags", "tagsToAdd": [{"tagFQN": "PII.Sensitive"}]},
)
print(f"Demande de description : {description['taskId']} ({description['status']})")
print(f"Demande de tag         : {etiquette['taskId']} ({etiquette['status']})")

if description["status"] == "Open":
    description = api(f"/tasks/{description['id']}/resolve", method="POST", token=admin, body={
        "resolutionType": "Approved",
        "newValue": "Pays du client, code ISO à deux lettres. Vide pour l'import de 2023.",
        "comment": "Vu avec l'équipe produit.",
    })
if etiquette["status"] == "Open":
    etiquette = api(f"/tasks/{etiquette['id']}/close", method="POST", token=admin, body={
        "comment": "Déjà couvert par la détection de PII du chapitre 08.",
    })
print(f"Après réponse          : {description['status']} / {etiquette['status']}")

table = api(f"/tables/name/{CUSTOMERS}")
colonne = next(c for c in table["columns"] if c["name"] == "country")
print(f"Description de la colonne : {colonne.get('description')!r}")
