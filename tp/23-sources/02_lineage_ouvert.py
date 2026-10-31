#!/usr/bin/env python3
"""Chapitre 23 — recevoir du lineage en OpenLineage, et tracer un chemin entre familles d'assets.

    ./omlab py tp/23-sources/02_lineage_ouvert.py
"""

import sys
import time
import urllib.parse
import uuid

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()
SERVICE_OL = "postgresql://omlab-postgres:5432"

# Sans cette table de correspondance, le serveur ne sait pas quel service désigne l'espace de noms.
reglage = api("/system/settings/openLineageSettings", token=admin)
valeur = reglage.get("config_value") or {}
valeur.setdefault("namespaceToServiceMapping", {})[SERVICE_OL] = "omlab_postgres"
valeur["autoCreateEntities"] = False
api("/system/settings", method="PUT", token=admin, body={"config_type": "openLineageSettings", "config_value": valeur})

evenement = {
    "eventType": "COMPLETE",
    "eventTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "producer": "https://omlab.example/etl-maison",
    "schemaURL": "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent",
    "run": {"runId": str(uuid.uuid4())},
    "job": {"namespace": "etl_maison", "name": "enrichit_fct_orders"},
    "inputs": [{"namespace": SERVICE_OL, "name": "omlab.raw.products"}],
    "outputs": [{"namespace": SERVICE_OL, "name": "omlab.analytics.fct_orders"}],
}
reponse = api("/openlineage/lineage", method="POST", token=admin, body=evenement)
print(f"Événement reçu : {reponse}")

graphe = api(f"/lineage/table/name/{fqn('analytics', 'fct_orders')}?upstreamDepth=1&downstreamDepth=0", token=admin)
print(f"En amont de fct_orders : {sorted(n['name'] for n in graphe['nodes'])}")

# Un lien entre deux familles : le topic alimente la table, le tableau de bord lit la vue.
def ajouter(de_type: str, de_nom: str, vers_type: str, vers_nom: str) -> None:
    de = api(f"/{de_type}s/name/{de_nom}", token=admin)
    vers = api(f"/{vers_type}s/name/{vers_nom}", token=admin)
    api("/lineage", method="PUT", token=admin, body={"edge": {
        "fromEntity": {"id": de["id"], "type": de_type},
        "toEntity": {"id": vers["id"], "type": vers_type},
    }})


tableaux = api("/dashboards?service=omlab_metabase&limit=50&fields=charts", token=admin)["data"]
ventes = next(d for d in tableaux if d.get("displayName") == "Ventes")
# Un point dans un nom impose des guillemets dans le FQN : omlab_kafka."commandes.creees".
ajouter("topic", urllib.parse.quote('omlab_kafka."commandes.creees"'), "table", fqn("raw", "orders"))
ajouter("table", fqn("analytics", "v_revenue_monthly"), "dashboard", ventes["fullyQualifiedName"])
modele = api("/mlmodels/name/omlab_mlflow.prevision_ventes", token=admin)
ajouter("table", fqn("analytics", "v_revenue_monthly"), "mlmodel", modele["fullyQualifiedName"])

graphe = api(f"/lineage/table/name/{fqn('analytics', 'v_revenue_monthly')}?upstreamDepth=3&downstreamDepth=1", token=admin)
print("\nAutour de v_revenue_monthly :")
for n in sorted(graphe["nodes"], key=lambda n: n["type"]):
    print(f"  {n['type']:<11} {n.get('displayName') or n['name']}")
