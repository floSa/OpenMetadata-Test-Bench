#!/usr/bin/env python3
"""Chapitre 24 — une mémoire du Context Center : le savoir que les agents peuvent relire.

    ./omlab py tp/24-standards-agents/03_memoire.py
"""

import sys

sys.path.insert(0, "/omlab")

from lib.om import api, jeton_admin

admin = jeton_admin()
memoire = api("/contextCenter/memories", method="PUT", token=admin, body={
    "name": "ca_hors_avoirs",
    "title": "Le CA exclut les avoirs",
    "question": "Le chiffre d'affaires inclut-il les avoirs ?",
    "answer": "Non. Il se calcule sur les commandes au statut completed, montants négatifs exclus.",
    "memoryType": "Faq",
})
print(f"Mémoire : {memoire['name']} ({memoire['memoryType']}, {memoire.get('memoryScope')})")
print(f"  Q : {memoire['question']}")
print(f"  R : {memoire['answer']}")
print(f"Total : {api('/contextCenter/memories?limit=5', token=admin)['paging']['total']}")

# Les documents déposés demandent un stockage objet, absent de ce labo.
stockage = api("/system/status", token=admin)["Object Storage"]
print(f"\nDocuments : stockage objet actif ? {stockage['passed']}")
