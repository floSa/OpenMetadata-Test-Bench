#!/usr/bin/env python3
"""Chapitre 24 — échanger un contrat au format ouvert ODCS : exporter, valider, importer.

    ./omlab py tp/24-standards-agents/01_odcs.py

ODCS (Open Data Contract Standard) permet de garder le contrat dans Git, à côté du code.
"""

import json
import sys

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin, texte

admin = jeton_admin()
YAML = "application/yaml"

contrats = api("/dataContracts?limit=20", token=admin)["data"]
existant = next(c for c in contrats if c["name"] == "contrat_revenue_monthly")
exporte = texte(f"/dataContracts/{existant['id']}/odcs/yaml", token=admin)
print("Contrat du chapitre 16, exporté en ODCS :")
for ligne in exporte.splitlines()[:7]:
    print(f"  {ligne}")

ODCS = """apiVersion: v3.1.0
kind: DataContract
id: 2f1a7c5e-6b1d-4a32-9f1e-0c1d2e3f4a5b
name: contrat_products
version: 1.0.0
status: active
description:
  purpose: Catalogue des produits vendus.
schema:
  - name: products
    physicalType: table
    properties:
      - name: product_id
        logicalType: integer
        required: true
      - name: sku
        logicalType: string
slaProperties:
  - property: freshness
    value: 24
    unit: hour
"""
table = api(f"/tables/name/{fqn('raw', 'products')}", token=admin)
PARAMS = f"entityId={table['id']}&entityType=table"

FAUTIF = ODCS.replace("name: sku", "name: colonne_fantome")
essai = json.loads(texte(f"/dataContracts/odcs/validate/yaml?{PARAMS}", "POST", FAUTIF, admin, YAML))
print(f"\nAvec une colonne qui n'existe pas : valide ? {essai['valid']}")
print(f"  {essai['constraintErrors'][0]}")

validation = json.loads(texte(f"/dataContracts/odcs/validate/yaml?{PARAMS}", "POST", ODCS, admin, YAML))
print(f"Document corrigé : valide ? {validation['valid']}")

importe = json.loads(texte(f"/dataContracts/odcs/yaml?{PARAMS}&mode=replace", "PUT", ODCS, admin, YAML))
print(f"\nImporté : {importe['name']}, statut {importe.get('entityStatus')}")
print(f"  colonnes promises : {[c['name'] for c in importe.get('schema') or []]}")
print(f"  SLA               : {importe.get('sla')}")
