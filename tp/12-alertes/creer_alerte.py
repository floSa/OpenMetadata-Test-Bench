#!/usr/bin/env python3
"""Chapitre 12 — brancher une alerte sur un webhook.

    ./omlab py tp/12-alertes/creer_alerte.py

Un catalogue muet ne sert qu'à ceux qui pensent à le consulter. Les alertes
inversent le sens : c'est OpenMetadata qui vient vous chercher quand un test
échoue, quand une table est supprimée, quand un propriétaire change.

Ici on branche deux alertes sur le petit récepteur HTTP du projet
(conteneur omlab-webhook), pour voir passer les charges utiles en vrai :
  * l'une sur les échecs de tests de qualité ;
  * l'autre sur toute modification de schéma d'une table.

Récepteur : http://localhost:8010/  (ou le port de OMLAB_WEBHOOK_PORT)
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api

# Depuis le serveur OpenMetadata (dans Docker), le récepteur n'est pas sur
# localhost mais sur le nom de service du conteneur.
ENDPOINT = "http://omlab-webhook:8000/hook"

# ----------------------------------------------------------------------
# Anatomie d'une alerte, dans l'ordre où le serveur la lit :
#
#   alertType    Notification (événements du catalogue) ou
#                Observability (résultats de tests, fraîcheur des données)
#   resources    sur QUEL type d'entité on écoute : table, testCase...
#   input        les filtres, sous forme de fonctions nommées + arguments
#                (et non de conditions écrites à la main : le champ
#                 `filteringRules` que renvoie l'API est CALCULÉ, il est
#                 rejeté en écriture avec un « Invalid request format »)
#   destinations où envoyer : webhook, e-mail, Slack, Teams, ou un
#                destinataire interne (propriétaires, équipe, admins)
# ----------------------------------------------------------------------
ALERTES = [
    {
        "name": "omlab_tests_en_echec",
        "displayName": "Tests de qualité en échec",
        "description": "Prévient dès qu'un test de qualité produit un résultat.",
        "alertType": "Observability",
        "resources": ["testCase"],
    },
    {
        "name": "omlab_tables_modifiees",
        "displayName": "Tables modifiées",
        "description": "Prévient à chaque modification d'une table du catalogue.",
        "alertType": "Notification",
        "resources": ["table"],
    },
]


def creer(spec: dict) -> None:
    corps = {
        "name": spec["name"],
        "displayName": spec["displayName"],
        "description": spec["description"],
        "alertType": spec["alertType"],
        "enabled": True,
        "provider": "user",
        "resources": spec["resources"],
        # Sans filtre : tous les événements du type choisi passent.
        # Affiner ensuite (par table, par statut de test) se fait très bien
        # dans l'UI, qui propose la liste des filtres disponibles — c'est
        # l'exercice de fin de chapitre.
        "input": {"filters": [], "actions": []},
        "destinations": [
            {
                "category": "External",
                "type": "Webhook",
                "config": {"endpoint": ENDPOINT},
                "timeout": 10,
                "readTimeout": 12,
                "enabled": True,
            }
        ],
        # Intervalle de dépilement de la file d'événements, en secondes
        "pollInterval": 10,
    }

    if _existe(spec["name"]):
        existant = api(f"/events/subscriptions/name/{spec['name']}")
        corps["id"] = existant["id"]
    api("/events/subscriptions", method="PUT", body=corps)
    print(f"  alerte {spec['name']:24} -> {ENDPOINT}")


def _existe(name: str) -> bool:
    liste = api("/events/subscriptions?limit=100")
    return any(s["name"] == name for s in liste.get("data", []))


for spec in ALERTES:
    creer(spec)

print(
    "\nPour déclencher les alertes :\n"
    "  1. relancez une suite de tests qui échoue :\n"
    "       ./omlab test tp/10-qualite/tests-orders.yaml\n"
    "  2. modifiez le schéma du playground puis réingérez :\n"
    "       ./omlab psql \"ALTER TABLE raw.products ADD COLUMN poids_kg numeric(6,3)\"\n"
    "       ./omlab ingest tp/04-ingestion/metadata.yaml\n"
    "  3. regardez ce qui est arrivé :\n"
    "       ./omlab py tp/12-alertes/lire_evenements.py\n"
    "       (ou http://localhost:8010/ dans le navigateur)"
)
