#!/usr/bin/env python3
"""Chapitre 14 — premier contact avec le SDK Python : lire le catalogue.

    ./omlab py tp/14-sdk/01_lecture.py

Le SDK n'est pas un simple wrapper HTTP : il rend des objets Pydantic typés.
Concrètement, `table.columns[0].dataType` est une énumération, pas une chaîne,
et une faute de frappe explose à l'écriture plutôt qu'en production.
"""

import sys

sys.path.insert(0, "/omlab")

from metadata.generated.schema.entity.data.table import Table

from lib.om import DB_FQN, client, fqn

om = client()

# ---------------------------------------------------------------------
# 1. Récupérer une entité par son nom pleinement qualifié (FQN)
# ---------------------------------------------------------------------
# Le FQN est LA clé d'accès dans OpenMetadata : service.base.schéma.table
# `fields` liste les propriétés coûteuses à charger : sans lui, pas de
# colonnes, pas de tags, pas de propriétaire. C'est un choix de performance,
# pas un oubli.
table = om.get_by_name(
    entity=Table,
    fqn=fqn("raw", "customers"),
    fields=["columns", "tags", "owners", "profile"],
)

print(f"Table      : {table.fullyQualifiedName.root}")
print(f"Type       : {table.tableType.value}")
print(f"Description: {table.description.root if table.description else '(aucune)'}")
print(f"Version    : {table.version.root}")

# ---------------------------------------------------------------------
# 2. Parcourir les colonnes
# ---------------------------------------------------------------------
print("\nColonnes :")
for column in table.columns:
    tags = ", ".join(t.tagFQN.root for t in (column.tags or [])) or "—"
    contrainte = column.constraint.value if column.constraint else ""
    print(f"  {column.name.root:14} {column.dataType.value:10} {contrainte:12} tags: {tags}")

# ---------------------------------------------------------------------
# 3. Lister toutes les tables d'un service
# ---------------------------------------------------------------------
# `list_entities` est paginé : il renvoie un objet avec .entities et .after.
# Sur un vrai catalogue (des dizaines de milliers de tables), ne bouclez
# jamais sans gérer la pagination — voir list_all_entities ci-dessous.
print(f"\nTables du service (via list_all_entities) :")
count = 0
for t in om.list_all_entities(entity=Table, limit=100):
    if t.fullyQualifiedName.root.startswith(DB_FQN):
        count += 1
        print(f"  {t.fullyQualifiedName.root}")
print(f"\n{count} tables dans {DB_FQN}")
