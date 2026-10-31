#!/usr/bin/env python3
"""Chapitre 21 — relier les termes entre eux, et importer une ontologie SKOS.

    ./omlab py tp/21-gouvernance-avancee/02_ontologie.py
"""

import json
import sys

sys.path.insert(0, "/omlab")

from lib.om import api, jeton_admin, texte

admin = jeton_admin()

commande = api("/glossaryTerms/name/Commerce.Commande?fields=relatedTerms", token=admin)
avoir = api("/glossaryTerms/name/Commerce.Avoir", token=admin)
api(f"/glossaryTerms/{commande['id']}/relations", method="POST", token=admin, body={
    "term": {"id": avoir["id"], "type": "glossaryTerm"},
    "relationType": "relatedTo",
})
commande = api("/glossaryTerms/name/Commerce.Commande?fields=relatedTerms", token=admin)
for lien in commande["relatedTerms"]:
    print(f"Commande --{lien['relationType']}--> {lien['term']['name']}")

SKOS = """@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex: <http://exemple.org/logistique#> .

ex:Transport a skos:Concept ; skos:prefLabel "Transport"@fr ;
  skos:definition "Acheminement d'une commande."@fr .
ex:Livraison a skos:Concept ; skos:prefLabel "Livraison"@fr ;
  skos:definition "Remise au client final."@fr ; skos:broader ex:Transport .
"""
api("/glossaries", method="PUT", token=admin, body={
    "name": "Logistique", "description": "Importé depuis une ontologie SKOS.",
})
simulation = json.loads(texte("/glossaries/name/Logistique/importRdf?dryRun=true&format=turtle", "PUT", SKOS, token=admin))
print(f"\nSimulation SKOS : {json.dumps(simulation, ensure_ascii=False)[:300]}")
resultat = json.loads(texte("/glossaries/name/Logistique/importRdf?dryRun=false&format=turtle", "PUT", SKOS, token=admin))
print(f"Import          : {json.dumps(resultat, ensure_ascii=False)[:300]}")
gloss = api("/glossaries/name/Logistique", token=admin)
for t in api(f"/glossaryTerms?glossary={gloss['id']}&fields=parent&limit=20", token=admin)["data"]:
    print(f"  {t['fullyQualifiedName']}  parent={t.get('parent', {}).get('name')}")
