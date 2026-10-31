#!/usr/bin/env python3
"""Chapitre 21 — observer et suspendre un workflow de gouvernance.

    ./omlab py tp/21-gouvernance-avancee/04_workflows.py

Un workflow suspendu n'approuve plus rien : le script le réactive aussitôt.
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, jeton_admin

admin = jeton_admin()
NOM = "GlossaryTermApprovalWorkflow"

definitions = api("/governance/workflowDefinitions?limit=50", token=admin)["data"]
print(f"{len(definitions)} workflows fournis d'origine, dont {definitions[0]['name']}")

definition = api(f"/governance/workflowDefinitions/name/{NOM}", token=admin)
print(f"\n{NOM} : déclenché par {definition['trigger']['type']}")
print(f"  sur {definition['trigger']['config']['entityTypes']}, événements {definition['trigger']['config']['events']}")
print(f"  {len(definition['nodes'])} étapes, {len(definition['edges'])} transitions")

print("\nÉtapes qui attendent un humain :")
for etape in definition["nodes"]:
    if etape["type"] == "userTask":
        print(f"  {etape['name']}")

api(f"/governance/workflowDefinitions/name/{NOM}/suspend", method="PUT", token=admin, body={})
print(f"\nSuspendu ? {api(f'/governance/workflowDefinitions/name/{NOM}', token=admin).get('suspended')}")
api(f"/governance/workflowDefinitions/name/{NOM}/resume", method="PUT", token=admin, body={})
print(f"Après reprise ? {api(f'/governance/workflowDefinitions/name/{NOM}', token=admin).get('suspended')}")
