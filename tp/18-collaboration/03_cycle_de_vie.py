#!/usr/bin/env python3
"""Chapitre 18 — supprimer sans perdre : suppression logique, restauration, suppression définitive.

    ./omlab py tp/18-collaboration/03_cycle_de_vie.py

La table créée ici n'existe que dans le catalogue, et le script finit par l'effacer.
"""

import sys
import urllib.parse

sys.path.insert(0, "/omlab")

from lib.om import api, fqn, jeton_admin

admin = jeton_admin()
NOM = fqn("raw", "table_ephemere")

table = api("/tables", method="PUT", token=admin, body={
    "name": "table_ephemere",
    "databaseSchema": fqn("raw"),
    "columns": [{"name": "id", "dataType": "INT"}],
})
print(f"Créée      : {table['fullyQualifiedName']}")


def visible() -> bool:
    res = api(f"/tables?databaseSchema={urllib.parse.quote(fqn('raw'))}&limit=50")["data"]
    return any(t["name"] == "table_ephemere" for t in res)


api(f"/tables/{table['id']}", method="DELETE", token=admin)
print(f"Supprimée  : visible dans les listes ? {visible()}")
sup = api(f"/tables/name/{NOM}?include=deleted")
print(f"             encore lisible avec include=deleted ? {sup['deleted']}")

api("/tables/restore", method="PUT", token=admin, body={"id": table["id"]})
print(f"Restaurée  : visible dans les listes ? {visible()}")

api(f"/tables/{table['id']}?hardDelete=true", method="DELETE", token=admin)
print(f"Effacée    : visible ? {visible()}")
try:
    api(f"/tables/name/{NOM}?include=all")
    print("             encore lisible")
except SystemExit as err:
    print(f"             include=all répond {str(err).split()[1]}")
