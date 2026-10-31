#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.12.*"
# dependencies = ["mcp==1.26.0"]
# ///
"""Chapitre 24 — un vrai client MCP, celui du SDK officiel, comme le ferait un assistant.

    OM_TOKEN=$(grep ^OM_TOKEN .env | cut -d= -f2) uv run --script tp/24-standards-agents/02_client_mcp_officiel.py

Ce script tourne sur la machine hôte : c'est là que se trouverait votre assistant.
"""

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = os.environ.get("OM_HOST", "http://localhost:8585") + "/mcp"
ENTETES = {"Authorization": f"Bearer {os.environ['OM_TOKEN']}"}


async def principal() -> None:
    async with streamablehttp_client(URL, headers=ENTETES) as (lecture, ecriture, _):
        async with ClientSession(lecture, ecriture) as session:
            info = await session.initialize()
            print(f"Connecté à {info.serverInfo.name} {info.serverInfo.version}")

            outils = (await session.list_tools()).tools
            print(f"{len(outils)} outils disponibles")

            reponse = await session.call_tool("search_metadata", {"query": "ventes", "size": 3})
            resultats = json.loads(reponse.content[0].text)
            print(f"\nsearch_metadata(query='ventes') : {resultats.get('total')} résultat(s)")
            for r in (resultats.get("results") or resultats.get("hits") or [])[:3]:
                print(f"  {r.get('entityType', '?'):<12} {r.get('fullyQualifiedName')}")

            reponse = await session.call_tool("get_entity_lineage", {
                "entityType": "table",
                "fqn": "omlab_postgres.omlab.analytics.v_revenue_monthly",
                "upstreamDepth": 1,
                "downstreamDepth": 1,
            })
            graphe = json.loads(reponse.content[0].text)
            print(f"\nget_entity_lineage : {graphe['returnedEdges']} arête(s), racine {graphe['root']}")


asyncio.run(principal())
