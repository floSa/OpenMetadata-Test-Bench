#!/usr/bin/env python3
"""Chapitre 22 — préférences de l'instance, santé, journal d'audit.

    ./omlab py tp/22-administration/02_preferences.py

Le réglage modifié ici est remis à sa valeur d'origine en fin de script.
"""

import json
import sys

sys.path.insert(0, "/omlab")

from lib.om import api, jeton_admin

admin = jeton_admin()

print("Santé de l'instance :")
for nom, etat in api("/system/status", token=admin).items():
    if isinstance(etat, dict) and "passed" in etat:
        print(f"  {'OK' if etat['passed'] else 'KO'}  {nom}")

print("\nPréférences :")
lignage = api("/system/settings/lineageSettings", token=admin)
print(f"  lineage    : profondeur {lignage['config_value']['upstreamDepth']}/{lignage['config_value']['downstreamDepth']}")
connexion = api("/system/settings/loginConfiguration", token=admin)["config_value"]
print(f"  connexion  : {connexion['maxLoginFailAttempts']} essais, blocage {connexion['accessBlockTime']} s, session {connexion['jwtTokenExpiryTime']} s")
courriel = api("/system/settings/emailConfiguration", token=admin)["config_value"]
print(f"  e-mail     : serveur SMTP actif ? {courriel['enableSmtpServer']}")
recherche = api("/system/settings/searchSettings", token=admin)["config_value"]
print(f"  recherche  : {len(recherche['assetTypeConfigurations'])} types d'assets paramétrés")
tables = next(c for c in recherche["assetTypeConfigurations"] if c["assetType"] == "table")
champ = max(tables["searchFields"], key=lambda f: f.get("boost", 0))
print(f"               champ le plus fort sur une table : {champ['field']} (boost {champ['boost']})")

avant = lignage["config_value"]["upstreamDepth"]
nouveau = {**lignage["config_value"], "upstreamDepth": 3}
api("/system/settings", method="PUT", token=admin, body={"config_type": "lineageSettings", "config_value": nouveau})
print(f"\nProfondeur montante : {avant} -> {api('/system/settings/lineageSettings', token=admin)['config_value']['upstreamDepth']}")
api("/system/settings", method="PUT", token=admin, body=lignage)
print(f"Remise à            : {api('/system/settings/lineageSettings', token=admin)['config_value']['upstreamDepth']}")

print("\nJournal d'audit, 5 dernières entrées :")
for e in api("/audit/logs?limit=5", token=admin)["data"]:
    print(f"  {e['eventType']:<18} {e.get('userName', '-'):<15} {e.get('entityType') or '-':<14} {e.get('entityFQN') or ''}"[:100])
print(f"\nRessources pédagogiques intégrées : {api('/learning/resources?limit=1', token=admin)['paging']['total']}")
