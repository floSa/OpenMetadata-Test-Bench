#!/usr/bin/env python3
"""Chapitre 16 — un contrat de données sur analytics.v_revenue_monthly.

    ./omlab py tp/16-contracts-ops/contrat_donnees.py

Un contrat de données répond à une question que ni la documentation ni les
tests ne tranchent seuls : « sur quoi le producteur s'engage-t-il ? ».

Il rassemble en un seul objet, versionné et opposable :
  * le SCHÉMA promis (ces colonnes, ces types, et pas d'autres) ;
  * des règles SÉMANTIQUES (la table a un propriétaire, elle est classée) ;
  * les TESTS de qualité qui font foi ;
  * un responsable, une date d'entrée en vigueur, des conditions d'usage.

La différence avec un simple ensemble de tests : le contrat est publié
côté consommateur. Si le producteur casse le schéma, ce n'est plus un
incident technique, c'est une rupture d'engagement — et OpenMetadata le
dit explicitement.
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn

TABLE_FQN = fqn("analytics", "v_revenue_monthly")
table = api(f"/tables/name/{TABLE_FQN}?fields=columns,owners")

contrat = {
    "name": "contrat_revenue_monthly",
    "displayName": "Contrat — CA mensuel",
    "description": (
        "Vue de référence du chiffre d'affaires mensuel par pays. "
        "Toute rupture de ce contrat doit être annoncée deux semaines "
        "à l'avance sur le canal #data-annonces."
    ),
    "entity": {"id": table["id"], "type": "table"},

    # --- Le schéma promis --------------------------------------------
    # Le contrat ne liste pas forcément TOUTES les colonnes : seulement
    # celles sur lesquelles on s'engage. Ajouter une colonne ne casse
    # rien ; en retirer une du contrat, si.
    "schema": [
        {"name": "order_month", "dataType": "DATE",
         "description": "Premier jour du mois concerné."},
        {"name": "customer_country", "dataType": "VARCHAR",
         "description": "Code pays ISO 3166-1 alpha-2 du client."},
        {"name": "revenue", "dataType": "NUMERIC",
         "description": "Somme des montants des commandes complétées."},
        {"name": "order_count", "dataType": "BIGINT",
         "description": "Nombre de commandes complétées sur le mois."},
    ],

    # --- Règles sémantiques ------------------------------------------
    # Elles portent sur les MÉTADONNÉES, pas sur les données : « cette
    # table doit avoir un propriétaire », « elle doit être documentée ».
    # C'est ce qui empêche une table critique de devenir orpheline.
    "semantics": [
        {
            "name": "proprietaire_obligatoire",
            "description": "Une table sous contrat doit avoir un responsable identifié.",
            "rule": '{"!!": {"var": "owners"}}',
        },
        {
            "name": "description_obligatoire",
            "description": "La table doit rester documentée.",
            "rule": '{"!!": {"var": "description"}}',
        },
    ],

    "termsOfUse": (
        "Usage analytique uniquement. Ne pas rediffuser à des tiers : "
        "les montants sont des données commerciales confidentielles."
    ),
}

resultat = api("/dataContracts", method="PUT", body=contrat)
print(f"Contrat : {resultat['name']} (v{resultat['version']})")
print(f"  entité   : {TABLE_FQN}")
print(f"  colonnes engagées : {[c['name'] for c in resultat.get('schema', [])]}")
print(f"  règles sémantiques : {[s['name'] for s in resultat.get('semantics', [])]}")

# ---------------------------------------------------------------------
# Valider le contrat
# ---------------------------------------------------------------------
# La validation est portée par une application interne,
# DataContractValidationApplication, qu'on peut aussi déclencher à la main.
print("\nDéclenchement de la validation...")
api(f"/dataContracts/{resultat['id']}/validate", method="POST")

resultats = api(f"/dataContracts/{resultat['id']}/results?limit=1")
dernier = resultats["data"][0]

print(f"  statut global : {dernier['contractExecutionStatus']}")

schema_v = dernier["schemaValidation"]
print(f"  schéma        : {schema_v['passed']}/{schema_v['total']} colonnes conformes")
if schema_v["failedFields"]:
    print(f"      colonnes manquantes : {schema_v['failedFields']}")
if schema_v["typeMismatchFields"]:
    print(f"      types divergents    : {schema_v['typeMismatchFields']}")

semantique = dernier["semanticsValidation"]
print(f"  sémantique    : {semantique['passed']}/{semantique['total']} règles respectées")
for regle in semantique.get("failedRules", []):
    print(f"      ÉCHEC {regle['ruleName']} — {regle['reason']}")

print(
    "\nCe premier passage échoue, et c'est exactement le comportement voulu :\n"
    "la vue v_revenue_monthly n'a pas de propriétaire. Un contrat sans\n"
    "responsable identifié est un contrat que personne ne tiendra.\n"
    "\n"
    "Pour le voir passer au vert :\n"
    "  1. dans l'UI, ouvrez analytics.v_revenue_monthly et attribuez-la à\n"
    "     l'équipe Data Platform (créée au chapitre 09) ;\n"
    "  2. relancez ce script.\n"
    "\n"
    "Puis, pour voir la validation de SCHÉMA échouer à son tour :\n"
    "  ./omlab psql \"DROP VIEW analytics.v_revenue_monthly CASCADE\"\n"
    "  (recréez-la ensuite avec docker/seed/03_analytics.sql)"
)
