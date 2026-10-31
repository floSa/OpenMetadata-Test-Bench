#!/usr/bin/env python3
"""Chapitre 22 — Slack, Teams, Google Chat : le même événement, trois formats.

    ./omlab py tp/22-administration/04_destinations.py

Faute de vrais espaces de discussion, les trois destinations visent le récepteur du
chapitre 12. On voit ainsi ce qui partirait, sans compte Slack ni Teams.
"""

import json
import sys
import time
import urllib.request

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()
RECEPTEUR = "http://omlab-webhook:8000"
TYPES = {"Slack": "omlab_slack", "MsTeams": "omlab_teams", "GChat": "omlab_gchat"}


def recus() -> list[dict]:
    with urllib.request.urlopen(f"{RECEPTEUR}/events", timeout=15) as reponse:
        return json.loads(reponse.read())["events"]


for type_dest, nom in TYPES.items():
    corps = {
        "name": nom, "alertType": "Notification", "enabled": True, "provider": "user",
        "resources": ["table"], "input": {"filters": [], "actions": []}, "pollInterval": 5,
        "destinations": [{
            "category": "External", "type": type_dest,
            "config": {"endpoint": f"{RECEPTEUR}/hook"},
            "timeout": 10, "readTimeout": 12, "enabled": True,
        }],
    }
    api("/events/subscriptions", method="PUT", token=admin, body=corps)
print(f"Alertes créées : {', '.join(TYPES)}")

# Prévenir aussi l'aval : les propriétaires des tables qui consomment celle-ci.
api("/events/subscriptions", method="PUT", token=admin, body={
    "name": "omlab_aval", "alertType": "Notification", "enabled": True, "provider": "user",
    "resources": ["table"], "input": {"filters": [], "actions": []},
    "destinations": [{
        "category": "Owners", "type": "ActivityFeed",
        "notifyDownstream": True, "downstreamDepth": 2,
    }],
})
aval = api("/events/subscriptions/name/omlab_aval", token=admin)["destinations"][0]
print(f"Vers l'aval : profondeur {aval['downstreamDepth']}, activé {aval['notifyDownstream']}")

avant = len(recus())
table = api(f"/tables/name/{fqn('raw', 'order_items')}", token=admin)
api(f"/tables/{table['id']}", method="PATCH", token=admin, content_type="application/json-patch+json",
    body=[{"op": "add", "path": "/description", "value": f"Lignes de commande. Relu le {time.strftime('%d/%m %H:%M:%S')}."}])
for _ in range(20):
    time.sleep(3)
    nouveaux = recus()[:len(recus()) - avant]
    if len(nouveaux) >= 3:
        break

print(f"\n{len(nouveaux)} messages reçus. Clés de premier niveau :")
for e in nouveaux[:6]:
    print(f"  {sorted(e['payload'])[:6]}")

for nom in [*TYPES.values(), "omlab_aval"]:
    alerte = api(f"/events/subscriptions/name/{nom}", token=admin)
    api(f"/events/subscriptions/{alerte['id']}?hardDelete=true", method="DELETE", token=admin)
print("\nAlertes de démonstration retirées.")
