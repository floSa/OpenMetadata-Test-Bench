#!/usr/bin/env python3
"""Chapitre 19 — éditer un glossaire en CSV : exporter, modifier, simuler, importer.

    ./omlab py tp/19-import-export/01_glossaire_csv.py
"""

import csv
import io
import json
import sys

sys.path.insert(0, "/omlab")

from lib.om import api, jeton_admin, texte

admin = jeton_admin()

export = texte("/glossaries/name/Commerce/export", token=admin)
lignes = list(csv.DictReader(io.StringIO(export)))
print(f"Exporté : {len(lignes)} termes, colonnes : {', '.join(list(lignes[0])[:6])}...")

if not any(l["name*"] == "Panier" for l in lignes):
    lignes.append({**dict.fromkeys(lignes[0], ""), "name*": "Panier", "displayName": "Panier",
                   "description": "Ensemble des lignes d'une commande avant paiement.",
                   "synonyms": "Cart;Caddie"})

sortie = io.StringIO()
ecrivain = csv.DictWriter(sortie, fieldnames=list(lignes[0]))
ecrivain.writeheader()
ecrivain.writerows(lignes)

# dryRun=true valide tout et n'écrit rien : à faire systématiquement avant le vrai import.
simulation = json.loads(texte("/glossaries/name/Commerce/import?dryRun=true", "PUT", sortie.getvalue(), token=admin))
print(f"Simulation : {simulation['status']}, {simulation['numberOfRowsPassed']}/{simulation['numberOfRowsProcessed']} lignes")
print(f"  Panier existe après simulation ? {any(t['name'] == 'Panier' for t in api('/glossaryTerms?glossary=' + api('/glossaries/name/Commerce')['id'] + '&limit=50')['data'])}")

resultat = json.loads(texte("/glossaries/name/Commerce/import?dryRun=false", "PUT", sortie.getvalue(), token=admin))
print(f"Import     : {resultat['status']}, {resultat['numberOfRowsPassed']}/{resultat['numberOfRowsProcessed']} lignes")
terme = api("/glossaryTerms/name/Commerce.Panier")
print(f"  Panier   : statut {terme.get('entityStatus')}, synonymes {terme['synonyms']}")

# Une ligne fautive : la simulation dit laquelle, et pourquoi.
fautif = sortie.getvalue() + ",Fautif,Fautif,,,CeTermeNexistePas,,,,,,,,,\r\n"
essai = json.loads(texte("/glossaries/name/Commerce/import?dryRun=true", "PUT", fautif, token=admin))
print(f"\nAvec une ligne fautive : {essai['status']}, {essai['numberOfRowsFailed']} ligne en échec")
for ligne in csv.DictReader(io.StringIO(essai["importResultsCsv"])):
    if ligne["status"] == "failure":
        print(f"  {ligne['name*']} : {ligne['details']}")
