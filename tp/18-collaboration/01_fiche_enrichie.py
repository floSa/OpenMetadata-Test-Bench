#!/usr/bin/env python3
"""Chapitre 18 — enrichir une fiche : propriété personnalisée, tier, abonnement, vote.

    ./omlab py tp/18-collaboration/01_fiche_enrichie.py

Chaque modification crée une version de la fiche : le script finit par les lire.
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

PATCH = "application/json-patch+json"
admin = jeton_admin()
moi = api("/users/loggedInUser", token=admin)

# Une propriété personnalisée se déclare sur le type d'entité, pas sur une table.
type_table = api("/metadata/types/name/table?fields=customProperties")
type_string = api("/metadata/types/name/string")
if not any(p["name"] == "frequenceMaj" for p in type_table.get("customProperties") or []):
    api(f"/metadata/types/{type_table['id']}", method="PUT", token=admin, body={
        "name": "frequenceMaj",
        "description": "À quel rythme cette table est-elle rafraîchie ?",
        "propertyType": {"id": type_string["id"], "type": "type"},
    })
print("Propriété déclarée sur le type table : frequenceMaj")

table = api(f"/tables/name/{fqn('raw', 'orders')}?fields=extension,tags,followers,votes")
api(f"/tables/{table['id']}", method="PATCH", content_type=PATCH, token=admin, body=[
    {"op": "add", "path": "/extension", "value": {"frequenceMaj": "quotidienne"}},
])

tags = [t for t in table["tags"] if not t["tagFQN"].startswith("Tier.")]
tags.append({"tagFQN": "Tier.Tier1", "source": "Classification", "labelType": "Manual", "state": "Confirmed"})
api(f"/tables/{table['id']}", method="PATCH", content_type=PATCH, token=admin, body=[
    {"op": "add", "path": "/tags", "value": tags},
])

api(f"/tables/{table['id']}/followers", method="PUT", body=moi["id"], token=admin)
api(f"/tables/{table['id']}/vote", method="PUT", body={"updatedVoteType": "votedUp"}, token=admin)

table = api(f"/tables/{table['id']}?fields=extension,tags,followers,votes")
print(f"Extension : {table['extension']}")
print(f"Tier      : {[t['tagFQN'] for t in table['tags'] if t['tagFQN'].startswith('Tier.')]}")
print(f"Abonnés   : {[f['name'] for f in table['followers']]}")
print(f"Votes     : +{table['votes']['upVotes']} / -{table['votes']['downVotes']}")

versions = api(f"/tables/{table['id']}/versions")["versions"]
print(f"\n{len(versions)} versions, dont les 3 dernières :")
import json
for v in versions[:3]:
    v = json.loads(v) if isinstance(v, str) else v
    champs = [c["name"] for g in ("fieldsAdded", "fieldsUpdated", "fieldsDeleted") for c in v["changeDescription"].get(g, [])]
    print(f"  {v['version']:<5} {v['updatedBy']:<15} {', '.join(champs)}")
