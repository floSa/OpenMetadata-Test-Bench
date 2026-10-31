#!/usr/bin/env python3
"""Chapitre 19 — documenter une table entière d'un coup, depuis un tableur.

    ./omlab py tp/19-import-export/02_colonnes_csv.py
"""

import csv
import io
import json
import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin, texte

admin = jeton_admin()
PRODUCTS = fqn("raw", "products")
DESCRIPTIONS = {
    "product_id": "Identifiant technique du produit.",
    "name": "Nom commercial affiché sur la boutique.",
}

export = texte(f"/tables/name/{PRODUCTS}/export", token=admin)
lignes = list(csv.DictReader(io.StringIO(export)))
for ligne in lignes:
    if ligne["column.name*"] in DESCRIPTIONS:
        ligne["column.description"] = DESCRIPTIONS[ligne["column.name*"]]

sortie = io.StringIO()
ecrivain = csv.DictWriter(sortie, fieldnames=list(lignes[0]))
ecrivain.writeheader()
ecrivain.writerows(lignes)

res = json.loads(texte(f"/tables/name/{PRODUCTS}/import?dryRun=false", "PUT", sortie.getvalue(), token=admin))
print(f"Import : {res['status']}, {res['numberOfRowsPassed']}/{res['numberOfRowsProcessed']} colonnes")
for colonne in api(f"/tables/name/{PRODUCTS}")["columns"]:
    print(f"  {colonne['name']:<12} {colonne.get('description') or '-'}")
