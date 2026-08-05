#!/usr/bin/env python3
"""Chapitre 09 — équipes, rôles et politiques d'accès.

    ./omlab py tp/09-securite/teams_roles_policies.py

Le modèle de sécurité d'OpenMetadata tient en une phrase :

    une RÈGLE autorise ou interdit des OPÉRATIONS sur des RESSOURCES,
    sous CONDITION ; un ensemble de règles forme une POLITIQUE ;
    une politique attachée à un RÔLE ; un rôle donné à un UTILISATEUR
    ou à une ÉQUIPE.

Ce qui rend le système puissant — et déroutant — c'est la CONDITION :
une expression évaluée à la volée, du type « l'utilisateur est-il
propriétaire de cette table ? ». C'est ce qui permet d'écrire « chacun
peut modifier la description des tables qu'il possède » sans énumérer
personne.

Ce TP crée une petite organisation : une équipe Data, deux utilisateurs,
une politique qui protège les données RH, et le rôle qui va avec.
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api

# ---------------------------------------------------------------------
# 1. Une équipe
# ---------------------------------------------------------------------
# teamType structure la hiérarchie : Organization > BusinessUnit >
# Division > Department > Group. Seuls les Group peuvent avoir des
# utilisateurs pour membres directs — erreur classique au premier essai.
equipe = api(
    "/teams",
    method="PUT",
    body={
        "name": "data_platform",
        "displayName": "Data Platform",
        "description": "Équipe responsable de l'entrepôt et du catalogue.",
        "teamType": "Group",
    },
)
print(f"Équipe : {equipe['fullyQualifiedName']} (type {equipe['teamType']})")

# ---------------------------------------------------------------------
# 2. Des utilisateurs
# ---------------------------------------------------------------------
UTILISATEURS = [
    ("cmartin", "Camille Martin", "camille.martin@omlab.internal"),
    ("lbernard", "Louis Bernard", "louis.bernard@omlab.internal"),
]

for name, display, email in UTILISATEURS:
    user = api(
        "/users",
        method="PUT",
        body={
            "name": name,
            "displayName": display,
            "email": email,
            "teams": [equipe["id"]],
            # isBot=False : un humain. Les bots ont un jeton long, pas de
            # mot de passe, et sont exclus des fils d'activité.
            "isBot": False,
        },
    )
    print(f"  utilisateur : {user['name']} <{user['email']}>")

# ---------------------------------------------------------------------
# 3. Une politique
# ---------------------------------------------------------------------
# Deux règles, et l'ordre ne compte pas : dans OpenMetadata, un DENY
# l'emporte TOUJOURS sur un ALLOW, quelle que soit sa position.
politique = api(
    "/policies",
    method="PUT",
    body={
        "name": "omlab_donnees_rh",
        "displayName": "Protection des données RH",
        "description": "Interdit la consultation des échantillons RH, "
                       "tout en laissant la documentation ouverte.",
        "rules": [
            {
                "name": "interdire_echantillons_rh",
                "effect": "deny",
                # Les noms d'opérations sont contrôlés par le serveur. Une
                # faute de frappe ne donne pas « opération inconnue » mais un
                # laconique « Invalid request format ». La liste exacte pour
                # chaque ressource :  GET /api/v1/policies/resources
                "operations": ["ViewSampleData", "ViewDataProfile"],
                "resources": ["table"],
                # La condition est une expression SpEL évaluée sur l'entité
                # visée. matchAnyTag limite la règle aux tables étiquetées.
                "condition": "matchAnyTag('PII.Sensitive')",
            },
            {
                "name": "autoriser_documentation",
                "effect": "allow",
                "operations": ["EditDescription", "EditTags", "ViewBasic"],
                "resources": ["table"],
                # isOwner() : vrai seulement si l'utilisateur (ou son équipe)
                # est propriétaire de l'entité. Le cœur du modèle.
                "condition": "isOwner()",
            },
        ],
    },
)
print(f"\nPolitique : {politique['name']} ({len(politique['rules'])} règles)")
for r in politique["rules"]:
    print(f"  [{r['effect'].upper():5}] {r['name']:28} si {r.get('condition', '(toujours)')}")

# ---------------------------------------------------------------------
# 4. Le rôle qui porte la politique, donné à l'équipe
# ---------------------------------------------------------------------
role = api(
    "/roles",
    method="PUT",
    body={
        "name": "omlab_data_steward",
        "displayName": "Data Steward omlab",
        "description": "Documente les données dont il est propriétaire, "
                       "sans accès aux échantillons sensibles.",
        "policies": [politique["fullyQualifiedName"]],
    },
)
print(f"\nRôle : {role['name']} -> politiques {[p['name'] for p in role['policies']]}")

# Attacher le rôle à l'équipe : tous ses membres en héritent.
api(
    f"/teams/{equipe['id']}",
    method="PATCH",
    body=[{"op": "add", "path": "/defaultRoles", "value": [
        {"id": role["id"], "type": "role"}
    ]}],
    content_type="application/json-patch+json",
)
print(f"  rôle attaché à l'équipe {equipe['name']}")

# ---------------------------------------------------------------------
# 5. Donner un propriétaire à une table — pour que isOwner() ait un sens
# ---------------------------------------------------------------------
table = api("/tables/name/omlab_postgres.omlab.raw.employees?fields=owners")
api(
    f"/tables/{table['id']}",
    method="PATCH",
    body=[{"op": "add", "path": "/owners", "value": [
        {"id": equipe["id"], "type": "team"}
    ]}],
    content_type="application/json-patch+json",
)
print(f"\nraw.employees appartient désormais à l'équipe {equipe['displayName']}")

print(
    "\nPour vérifier dans l'UI : Paramètres > Équipes, puis Paramètres > Rôles.\n"
    "Pour tester la politique pour de vrai, connectez-vous en tant que\n"
    "cmartin (créez-lui un mot de passe depuis l'administration)."
)
