#!/usr/bin/env python3
"""Chapitre 17 — parler au serveur MCP intégré, sans aucun assistant.

    ./omlab py tp/17-tour-2x/04_client_mcp.py

MCP (Model Context Protocol) est du JSON-RPC sur HTTP. Un assistant ne fait rien
d'autre que ces trois appels : se présenter, lister les outils, en appeler un.
"""

import json
import sys
import urllib.request

sys.path.insert(0, "/omlab")

from lib.om import HOST, TOKEN


def mcp(identifiant: int, methode: str, params: dict) -> dict:
    corps = {"jsonrpc": "2.0", "id": identifiant, "method": methode, "params": params}
    requete = urllib.request.Request(f"{HOST}/mcp", data=json.dumps(corps).encode(), method="POST")
    requete.add_header("Authorization", f"Bearer {TOKEN}")
    requete.add_header("Content-Type", "application/json")
    # Le serveur refuse les clients qui n'acceptent pas les deux formats.
    requete.add_header("Accept", "application/json, text/event-stream")
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        return json.loads(reponse.read().decode())["result"]


serveur = mcp(1, "initialize", {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "omlab", "version": "1"},
})["serverInfo"]
print(f"Serveur : {serveur['name']} {serveur['version']}")

outils = mcp(2, "tools/list", {})["tools"]
print(f"\n{len(outils)} outils :")
for outil in outils:
    print(f"  {outil['name']}")

resultat = mcp(3, "tools/call", {
    "name": "search_metadata",
    "arguments": {"query": "orders", "entityType": "table", "size": 3},
})
print("\nsearch_metadata(query='orders') :")
print(resultat["content"][0]["text"][:600])
