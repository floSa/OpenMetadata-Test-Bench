#!/usr/bin/env python3
"""Chapitre 23 — mettre un peu de contenu dans chaque source, avant de les cataloguer.

    ./omlab py tp/23-sources/01_alimenter_sources.py

Rien de spécifique à OpenMetadata ici : ce sont les gestes habituels d'une équipe data.
"""

import io
import json
import time
import urllib.error
import urllib.request

import boto3
import pandas as pd
from confluent_kafka.admin import AdminClient, NewTopic


def appel(url: str, corps: dict | None = None, entetes: dict | None = None) -> dict:
    """Appelle une source, en patientant : Metabase met une à deux minutes à démarrer."""
    requete = urllib.request.Request(
        url, data=json.dumps(corps).encode() if corps is not None else None,
        headers={"Content-Type": "application/json", **(entetes or {})},
    )
    for _ in range(60):
        try:
            with urllib.request.urlopen(requete, timeout=60) as reponse:
                contenu = reponse.read()
            return json.loads(contenu) if contenu else {}
        except urllib.error.HTTPError as err:
            if err.code != 503:  # 503 : Metabase répond avant d'être prêt
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass  # pas encore démarré, ou connecté mais muet
        time.sleep(5)
    raise SystemExit(f"{url} ne répond toujours pas.")


# --- Kafka : deux topics, dont un avec son schéma Avro ------------------------------
admin = AdminClient({"bootstrap.servers": "omlab-redpanda:9092"})
for futur in admin.create_topics([NewTopic(t, 3, 1) for t in ("commandes.creees", "paiements.recus")]).values():
    try:
        futur.result(120)
    except Exception as err:
        if "TOPIC_ALREADY_EXISTS" not in str(err):
            raise
schema = {"type": "record", "name": "CommandeCreee", "namespace": "omlab", "fields": [
    {"name": "order_id", "type": "int", "doc": "Identifiant de la commande"},
    {"name": "amount", "type": "double", "doc": "Montant, négatif pour un avoir"},
]}
appel("http://omlab-redpanda:8081/subjects/commandes.creees-value/versions",
      {"schema": json.dumps(schema)}, {"Content-Type": "application/vnd.schemaregistry.v1+json"})
print("Kafka    : 2 topics, 1 schéma Avro")

# --- S3 : un fichier Parquet, et le manifeste qui dit où regarder ------------------
s3 = boto3.client("s3", endpoint_url="http://omlab-s3:9090", aws_access_key_id="omlab",
                  aws_secret_access_key="omlab_pwd", region_name="us-east-1")
tampon = io.BytesIO()
pd.DataFrame({"sku": ["A1", "B2"], "stock": [12, 0]}).to_parquet(tampon)
s3.put_object(Bucket="omlab-lac", Key="stocks/2026/stocks.parquet", Body=tampon.getvalue())
manifeste = {"entries": [{"dataPath": "stocks", "structureFormat": "parquet", "isPartitioned": False}]}
s3.put_object(Bucket="omlab-lac", Key="openmetadata.json", Body=json.dumps(manifeste).encode())
print("S3       : 1 fichier Parquet, 1 manifeste openmetadata.json")

# --- MLflow : un modèle au registre, avec sa version ----------------------------------
ML = "http://omlab-mlflow:5000/api/2.0/mlflow"
existe = appel(f"{ML}/registered-models/search").get("registered_models")
if not existe:
    # Une version sans exécution d'origine est ignorée par le connecteur (« Run ID not found »).
    experience = appel(f"{ML}/experiments/create", {"name": "ventes"})["experiment_id"]
    run = appel(f"{ML}/runs/create", {"experiment_id": experience})["run"]["info"]["run_id"]
    appel(f"{ML}/runs/log-parameter", {"run_id": run, "key": "fenetre_mois", "value": "12"})
    appel(f"{ML}/runs/log-metric", {"run_id": run, "key": "mape", "value": 0.08, "timestamp": 0})
    appel(f"{ML}/registered-models/create", {"name": "prevision_ventes", "description": "Prévoit le CA du mois suivant."})
    appel(f"{ML}/model-versions/create", {"name": "prevision_ventes", "run_id": run,
                                          "source": "s3://omlab-lac/modeles/prevision_ventes/1"})
print("MLflow   : 1 modèle enregistré")

# --- Metabase : l'assistant d'installation, une base, une question, un tableau de bord -
MB = "http://omlab-metabase:3000/api"
UTILISATEUR, MOT_DE_PASSE = "admin@omlab.example", "Metabase-2026!tuto"
proprietes = appel(f"{MB}/session/properties")
if not proprietes.get("has-user-setup"):
    appel(f"{MB}/setup", {
        "token": proprietes["setup-token"],
        "user": {"email": UTILISATEUR, "password": MOT_DE_PASSE, "first_name": "Omlab", "last_name": "Tuto"},
        "prefs": {"site_name": "Omlab", "allow_tracking": False},
        "database": None,
    })
session = {"X-Metabase-Session": appel(f"{MB}/session", {"username": UTILISATEUR, "password": MOT_DE_PASSE})["id"]}
bases = appel(f"{MB}/database", entetes=session)["data"]
base = next((b for b in bases if b["name"] == "omlab"), None) or appel(f"{MB}/database", {
    "engine": "postgres", "name": "omlab",
    "details": {"host": "omlab-postgres", "port": 5432, "dbname": "omlab", "user": "omlab", "password": "omlab_pwd"},
}, session)
if not any(d["name"] == "Ventes" for d in appel(f"{MB}/dashboard", entetes=session)):
    question = appel(f"{MB}/card", {
        "name": "CA par mois", "display": "table", "visualization_settings": {},
        "dataset_query": {"type": "native", "database": base["id"],
                          "native": {"query": "SELECT * FROM analytics.v_revenue_monthly"}},
    }, session)
    tableau = appel(f"{MB}/dashboard", {"name": "Ventes", "description": "Le suivi mensuel des ventes."}, session)
    requete = urllib.request.Request(
        f"{MB}/dashboard/{tableau['id']}", method="PUT",
        data=json.dumps({"dashcards": [{"id": -1, "card_id": question["id"], "row": 0, "col": 0,
                                        "size_x": 12, "size_y": 6}]}).encode(),
        headers={"Content-Type": "application/json", **session})
    urllib.request.urlopen(requete, timeout=30)
print("Metabase : 1 base, 1 question SQL, 1 tableau de bord")
