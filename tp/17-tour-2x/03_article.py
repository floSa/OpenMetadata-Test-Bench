#!/usr/bin/env python3
"""Chapitre 17 — un article du Context Center, qui remplace le Knowledge Center.

    ./omlab py tp/17-tour-2x/03_article.py
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn

orders = api(f"/tables/name/{fqn('raw', 'orders')}")

article = api("/contextCenter/pages", method="PUT", body={
    "name": "lire_les_avoirs",
    "displayName": "Lire les avoirs dans raw.orders",
    # Le texte de l'article est sa description : `page` ne porte que ses métadonnées.
    "description": "Les avoirs sont des commandes au montant négatif. Excluez-les du CA.",
    "pageType": "Article",
    "page": {},
    "relatedEntities": [{"id": orders["id"], "type": "table"}],
})
print(f"Article : {article['fullyQualifiedName']} ({article['pageType']})")
print(f"Lié à   : {[e['name'] for e in article.get('relatedEntities', [])]}")
