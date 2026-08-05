#!/usr/bin/env python3
"""Chapitre 12 — lire ce que le webhook a reçu.

    ./omlab py tp/12-alertes/lire_evenements.py

Affiche les dernières charges utiles reçues par le conteneur omlab-webhook.
C'est la meilleure façon de comprendre ce qu'OpenMetadata envoie réellement :
la documentation décrit les champs, mais rien ne remplace la lecture d'un
vrai événement.
"""

import json
import urllib.request

# Depuis le conteneur d'ingestion, le récepteur s'appelle omlab-webhook.
URL = "http://omlab-webhook:8000/events"

with urllib.request.urlopen(URL, timeout=15) as resp:
    data = json.loads(resp.read())

print(f"{data['count']} événement(s) reçu(s)\n")

for event in data["events"][:5]:
    payload = event["payload"]
    print(f"--- {event['received_at']} ---")
    print(f"  eventType  : {payload.get('eventType')}")
    print(f"  entityType : {payload.get('entityType')}")
    print(f"  entityFQN  : {payload.get('entityFullyQualifiedName')}")
    print(f"  userName   : {payload.get('userName')}")

    # Le champ le plus utile en pratique : ce qui a changé.
    change = payload.get("changeDescription") or {}
    for field in change.get("fieldsUpdated", []) + change.get("fieldsAdded", []):
        print(f"    champ modifié : {field.get('name')}")

if not data["events"]:
    print(
        "Rien reçu pour l'instant.\n"
        "Avez-vous créé les alertes ?  ./omlab py tp/12-alertes/creer_alerte.py\n"
        "Puis provoqué un événement (test en échec, changement de schéma) ?"
    )
