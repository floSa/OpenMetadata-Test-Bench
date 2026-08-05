#!/usr/bin/env python3
"""Chapitre 07 — construire un glossaire métier par le code.

    ./omlab py tp/07-glossaire/creer_glossaire.py

Pourquoi par le code plutôt qu'à la souris ? Parce qu'un glossaire est un
référentiel : il se versionne, se relit en revue, se rejoue à l'identique
sur la préproduction. Le clic est parfait pour explorer, pas pour tenir
un référentiel dans la durée.

Le script est idempotent : relancez-le autant que vous voulez.
"""

import sys

sys.path.insert(0, "/omlab")

from metadata.generated.schema.api.data.createGlossary import CreateGlossaryRequest
from metadata.generated.schema.api.data.createGlossaryTerm import (
    CreateGlossaryTermRequest,
)
from metadata.generated.schema.entity.data.glossary import Glossary
from metadata.generated.schema.entity.data.glossaryTerm import GlossaryTerm

from lib.om import client

om = client()

GLOSSARY_NAME = "Commerce"

# ---------------------------------------------------------------------
# 1. Le glossaire lui-même : un conteneur, rien de plus
# ---------------------------------------------------------------------
glossary = om.create_or_update(
    CreateGlossaryRequest(
        name=GLOSSARY_NAME,
        displayName="Glossaire Commerce",
        description=(
            "Vocabulaire métier de la boutique. Chaque terme y a une "
            "définition unique, opposable, et un responsable."
        ),
    )
)
print(f"Glossaire : {glossary.fullyQualifiedName.root}")

# ---------------------------------------------------------------------
# 2. Les termes
# ---------------------------------------------------------------------
# Deux points de vocabulaire OpenMetadata qui prêtent à confusion :
#
#   synonyms  : d'autres façons de dire LA MÊME chose. Ils alimentent la
#               recherche : chercher « CA » trouvera « Chiffre d'affaires ».
#   parent    : la hiérarchie. Un terme enfant hérite du contexte de son
#               parent, et son FQN devient Commerce.Parent.Enfant.
TERMES = [
    {
        "name": "Client",
        "displayName": "Client",
        "description": (
            "Personne physique ayant créé un compte sur la boutique. "
            "Attention : un client sans commande reste un client."
        ),
        "synonyms": ["Customer", "Acheteur"],
    },
    {
        "name": "Commande",
        "displayName": "Commande",
        "description": (
            "Engagement d'achat validé par un client. Une commande annulée "
            "reste une commande : elle n'est jamais supprimée de l'historique."
        ),
        "synonyms": ["Order"],
    },
    {
        "name": "ChiffreAffaires",
        "displayName": "Chiffre d'affaires",
        "description": (
            "Somme des montants des commandes au statut 'completed', hors "
            "avoirs. Les commandes 'pending' et 'cancelled' en sont exclues."
        ),
        "synonyms": ["CA", "Revenue", "Revenu"],
    },
    {
        "name": "Avoir",
        "displayName": "Avoir",
        "description": (
            "Remboursement enregistré dans raw.orders avec un montant négatif. "
            "Modélisation historique discutable, mais c'est la réalité de la base."
        ),
        "synonyms": ["Credit note"],
    },
]

for spec in TERMES:
    term = om.create_or_update(
        CreateGlossaryTermRequest(glossary=GLOSSARY_NAME, **spec)
    )
    print(f"  terme : {term.fullyQualifiedName.root}")

# ---------------------------------------------------------------------
# 3. Relire ce qu'on vient d'écrire
# ---------------------------------------------------------------------
# Réflexe à prendre : ne jamais faire confiance au retour d'un create.
# On relit toujours depuis le serveur, c'est lui qui fait foi.
stored = om.get_by_name(entity=Glossary, fqn=GLOSSARY_NAME, fields=["owners"])
print(f"\nGlossaire relu : {stored.displayName} (version {stored.version.root})")

for spec in TERMES:
    t = om.get_by_name(entity=GlossaryTerm, fqn=f"{GLOSSARY_NAME}.{spec['name']}")
    print(f"  {t.fullyQualifiedName.root:32} synonymes={[s.root for s in (t.synonyms or [])]}")

print(
    "\nÀ voir dans l'UI : Gouvernance > Glossaire.\n"
    "Le rattachement des termes aux colonnes est l'objet du script suivant."
)
