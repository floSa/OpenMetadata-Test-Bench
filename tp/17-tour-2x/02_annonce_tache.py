#!/usr/bin/env python3
"""Chapitre 17 — annonces et tâches, les deux objets déplacés par la 2.0.

    ./omlab py tp/17-tour-2x/02_annonce_tache.py

Avant la 2.0, annonces, tâches et suggestions passaient par le fil d'activité
(`/v1/feed`). Elles ont maintenant leurs propres routes, et les incidents de
qualité du chapitre 10 sont devenus des tâches comme les autres.
"""

import sys
import time

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

JOUR_MS = 86_400_000
maintenant = int(time.time() * 1000)
ORDERS = fqn("raw", "orders")

# Une annonce en cours par asset : on ne la recrée pas si le script est rejoué.
deja = api("/announcements?limit=50")["data"]
annonce = next((a for a in deja if a["name"] == "refonte_orders"), None)
if annonce is None:
    annonce = api("/announcements", method="POST", body={
        "name": "refonte_orders",
        "displayName": "Refonte de raw.orders",
        "description": "La colonne `currency` disparaîtra dans 30 jours.",
        "entityLink": f"<#E::table::{ORDERS}>",
        "startTime": maintenant,
        "endTime": maintenant + 30 * JOUR_MS,
    })
print(f"Annonce : {annonce['name']} ({annonce.get('status', 'sans statut')})")

taches = api("/tasks?limit=100")["data"]
tache = next((t for t in taches if t["name"] == "documenter_orders_amount"), None)
if tache is None:
    # L'ingestion-bot n'a pas le droit `CreateTask` : une tâche se crée en tant que personne.
    tache = api("/tasks", method="POST", token=jeton_admin(), body={
        "name": "documenter_orders_amount",
        "displayName": "Documenter raw.orders.amount",
        "description": "Préciser le signe des montants et le cas des avoirs.",
        "category": "MetadataUpdate",
        "type": "DescriptionUpdate",
        "priority": "High",
        "about": f"<#E::table::{ORDERS}>",
        "assignees": ["cmartin"],
    })
print(f"Tâche   : {tache['taskId']} {tache['name']} ({tache['status']}, {tache['priority']})")

# Les incidents du chapitre 10 figurent dans la même liste que notre tâche.
print("\nToutes les tâches, par catégorie :")
taches = api("/tasks?limit=100")["data"]
for categorie in sorted({t["category"] for t in taches}):
    noms = [t["name"] for t in taches if t["category"] == categorie]
    print(f"  {categorie:<15} {len(noms)}")
