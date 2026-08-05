#!/usr/bin/env python3
"""Chapitre 14 — écrire dans le catalogue avec le SDK.

    ./omlab py tp/14-sdk/02_ecriture.py

Le cas d'usage réel : documenter en masse. Personne ne remplit 4 000
descriptions à la main. En revanche, une équipe a souvent déjà ses
définitions quelque part — un tableur, un dépôt dbt, un wiki — et il
suffit de les déverser dans le catalogue.

Ce script :
  1. pose des descriptions depuis un dictionnaire (votre « source de vérité ») ;
  2. déclare un propriétaire ;
  3. crée une propriété personnalisée et la renseigne ;
  4. applique un niveau de criticité (Tier).

Il est idempotent : relancez-le sans crainte.
"""

import sys

sys.path.insert(0, "/omlab")

from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.teams.team import Team

from lib.om import api, client, fqn

om = client()

# ---------------------------------------------------------------------
# 1. Documentation en masse
# ---------------------------------------------------------------------
# Le SDK expose `patch_description`, qui fait le JSON Patch pour vous.
# force=True écrase une description existante ; sans lui, une description
# déjà présente est respectée — pratique pour ne pas écraser le travail
# des humains avec un script automatique.
DESCRIPTIONS = {
    ("raw", "orders"): "Commandes brutes issues du site marchand. "
                       "Les avoirs y figurent avec un montant négatif.",
    ("raw", "order_items"): "Lignes de commande. Une commande a 1 à 3 lignes.",
    ("raw", "products"): "Catalogue produits. Le SKU n'est pas unique : "
                         "cinq produits partagent SKU-00001.",
    ("analytics", "dim_customer"): "Dimension client, rafraîchie quotidiennement "
                                   "depuis raw.customers.",
}

print("=== 1. Descriptions ===")
for (schema, name), texte in DESCRIPTIONS.items():
    table = om.get_by_name(entity=Table, fqn=fqn(schema, name))
    om.patch_description(entity=Table, source=table, description=texte, force=True)
    print(f"  {schema}.{name:14} documentée")

# ---------------------------------------------------------------------
# 2. Un propriétaire
# ---------------------------------------------------------------------
# « Qui appelle-t-on quand cette table casse ? » Sans réponse à cette
# question, un catalogue reste un annuaire mort. C'est le champ le plus
# important du produit, et le plus souvent laissé vide.
print("\n=== 2. Propriétaire ===")
equipe = om.get_by_name(entity=Team, fqn="data_platform")
if equipe is None:
    print("  Équipe data_platform absente : lancez d'abord le TP du chapitre 09.")
else:
    for schema, name in [("raw", "orders"), ("analytics", "dim_customer")]:
        table = om.get_by_name(entity=Table, fqn=fqn(schema, name), fields=["owners"])
        api(
            f"/tables/{table.id.root}",
            method="PATCH",
            body=[{"op": "add", "path": "/owners",
                   "value": [{"id": str(equipe.id.root), "type": "team"}]}],
            content_type="application/json-patch+json",
        )
        print(f"  {schema}.{name:14} appartient à {equipe.displayName}")

# ---------------------------------------------------------------------
# 3. Une propriété personnalisée
# ---------------------------------------------------------------------
# Les champs natifs ne couvrent jamais tous les besoins d'une organisation.
# Les custom properties étendent le MODÈLE lui-même : ici, on ajoute à
# toutes les tables un champ « durée de rétention », attendu par la RGPD.
print("\n=== 3. Propriété personnalisée ===")

# La propriété se déclare sur le TYPE `table`, pas sur une table donnée.
type_table = api("/metadata/types/name/table?category=entity")
types_disponibles = api("/metadata/types?category=field&limit=50")
type_string = next(t for t in types_disponibles["data"] if t["name"] == "string")

deja = any(
    p["name"] == "retentionMonths"
    for p in api(f"/metadata/types/name/table?fields=customProperties").get("customProperties", [])
)
if not deja:
    api(
        f"/metadata/types/{type_table['id']}",
        method="PUT",
        body={
            "name": "retentionMonths",
            "description": "Durée de conservation réglementaire, en mois.",
            "propertyType": {"id": type_string["id"], "type": "type"},
        },
    )
    print("  propriété retentionMonths déclarée sur le type `table`")
else:
    print("  propriété retentionMonths déjà déclarée")

# On la renseigne ensuite comme n'importe quel champ, dans `extension`.
table = om.get_by_name(entity=Table, fqn=fqn("raw", "employees"))
api(
    f"/tables/{table.id.root}",
    method="PATCH",
    body=[{"op": "add", "path": "/extension", "value": {"retentionMonths": "60"}}],
    content_type="application/json-patch+json",
)
print("  raw.employees.retentionMonths = 60")

# ---------------------------------------------------------------------
# 4. Le Tier : dire ce qui est critique
# ---------------------------------------------------------------------
# Tier1 à Tier5 est une classification fournie d'origine. Son intérêt n'est
# pas décoratif : elle sert à trier les alertes, à prioriser la
# documentation, et à décider ce qu'on surveille vraiment.
print("\n=== 4. Criticité (Tier) ===")
for (schema, name), tier in [
    (("analytics", "v_revenue_monthly"), "Tier.Tier1"),
    (("raw", "orders"), "Tier.Tier1"),
    (("raw", "products"), "Tier.Tier3"),
]:
    table = om.get_by_name(entity=Table, fqn=fqn(schema, name), fields=["tags"])
    existants = [t.tagFQN.root for t in (table.tags or [])]
    if tier in existants:
        print(f"  {schema}.{name:20} déjà {tier}")
        continue
    api(
        f"/tables/{table.id.root}",
        method="PATCH",
        body=[{"op": "add", "path": "/tags/-", "value": {
            "tagFQN": tier, "source": "Classification",
            "labelType": "Manual", "state": "Confirmed"}}],
        content_type="application/json-patch+json",
    )
    print(f"  {schema}.{name:20} -> {tier}")

print("\nRegardez maintenant raw.orders dans l'UI : description, propriétaire,")
print("criticité et termes de glossaire y sont tous visibles d'un coup d'œil.")
