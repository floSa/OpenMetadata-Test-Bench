#!/usr/bin/env python3
"""Mesure ce que le cours couvre de la documentation officielle, page par page.

    ./omlab couverture

La référence : les 184 pages *how-to* de la documentation 2.0, relevées le 31/10/2026 dans
son plan du site, plus les familles de connecteurs et les sujets de déploiement. Sont
écartées les références sans fonction propre : 329 pages d'API, 358 fiches de connecteur
une à une, les notes de version et le guide des contributeurs.

Chaque ligne donne un niveau, un chapitre et un mot que ce chapitre doit contenir. Ce mot
empêche de déclarer couvert un sujet que le chapitre ne cite pas ; il ne prouve pas que le
sujet est bien traité.

  TP      un script ou un workflow du dépôt l'exécute
  ecran   l'écran a été ouvert et capturé, sans scénario complet
  doc     expliqué d'après la documentation, sans essai, et le chapitre le dit
"""

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LIGNES = """
how-to-guides|ecran|01|OpenMetadata
how-to-guides/admin-guide|TP|22|administration
how-to-guides/admin-guide/audit-logs|TP|22|audit
how-to-guides/admin-guide/cli-ingestion-with-basic-auth|TP|22|securityConfig
how-to-guides/admin-guide/data-asset-rules|TP|21|Data Asset Rule
how-to-guides/admin-guide/data-insights|ecran|17|Insights
how-to-guides/admin-guide/delete-service-connection|doc|22|Retirer une source
how-to-guides/admin-guide/how-to-ingest-metadata|TP|04|ingest
how-to-guides/admin-guide/learning-resources|TP|22|Ressources pédagogiques
how-to-guides/admin-guide/permission-debugger|TP|22|débogueur
how-to-guides/admin-guide/persona-landing-page-customization|TP|22|persona
how-to-guides/admin-guide/persona-landing-page-customization/customizable-landing-page|ecran|22|Customize UI
how-to-guides/admin-guide/persona-landing-page-customization/defining-persona|TP|22|persona
how-to-guides/admin-guide/preferences|TP|22|/system/settings
how-to-guides/admin-guide/preferences/email|doc|22|SMTP
how-to-guides/admin-guide/preferences/health-check|TP|22|Santé
how-to-guides/admin-guide/preferences/lineage|TP|22|lineageSettings
how-to-guides/admin-guide/preferences/login-configuration|TP|22|loginConfiguration
how-to-guides/admin-guide/preferences/profiler-configuration|doc|20|Profiler Configuration
how-to-guides/admin-guide/preferences/theme-and-branding|doc|22|Thème
how-to-guides/admin-guide/reindexing-search|TP|06|Search Indexing
how-to-guides/admin-guide/roles-policies|TP|09|politique
how-to-guides/admin-guide/roles-policies/authorization|TP|09|politique
how-to-guides/admin-guide/roles-policies/resource-scope|TP|09|opération
how-to-guides/admin-guide/roles-policies/use-cases|TP|09|rôle
how-to-guides/admin-guide/search-configuration-settings|ecran|22|searchSettings
how-to-guides/admin-guide/teams-and-users/add-team|TP|22|Crm
how-to-guides/admin-guide/teams-and-users/add-users|TP|21|relectrice
how-to-guides/admin-guide/teams-and-users/change-team-type|TP|22|Group vers Division
how-to-guides/admin-guide/teams-and-users/invite-users|doc|22|Inviter
how-to-guides/admin-guide/teams-and-users/team-structure-openmetadata|TP|22|BusinessUnit
how-to-guides/context-center|TP|17|Context Center
how-to-guides/context-center/articles|TP|17|articles
how-to-guides/context-center/documents|doc|24|documents
how-to-guides/context-center/memories|TP|24|mémoire
how-to-guides/data-collaboration|TP|18|conversation
how-to-guides/data-collaboration/activity-feeds|TP|18|fil d'activité
how-to-guides/data-collaboration/add-announcement|TP|17|annonce
how-to-guides/data-collaboration/announcements|TP|17|annonce
how-to-guides/data-collaboration/conversation|TP|18|conversation
how-to-guides/data-collaboration/request-description|TP|18|Demande de description
how-to-guides/data-collaboration/request-tags|TP|18|Demande de tag
how-to-guides/data-collaboration/tasks|TP|17|tâche
how-to-guides/data-contracts|TP|16|contrat
how-to-guides/data-contracts/create|TP|16|contrat
how-to-guides/data-contracts/odcs|TP|24|ODCS
how-to-guides/data-contracts/spec|TP|16|sémantique
how-to-guides/data-discovery|TP|03|recherche
how-to-guides/data-discovery/advanced|TP|03|Lucene
how-to-guides/data-discovery/bulk-upload|TP|19|CSV
how-to-guides/data-discovery/details|ecran|03|fiche
how-to-guides/data-discovery/discover|TP|03|recherche
how-to-guides/data-discovery/export|TP|19|export
how-to-guides/data-discovery/hierarchy|ecran|19|hiérarchie
how-to-guides/data-discovery/import|TP|19|import
how-to-guides/data-discovery/preview|ecran|03|fiche
how-to-guides/data-discovery/table-constraint|TP|18|tableConstraints
how-to-guides/data-discovery/troubleshooting|doc|19|Pièges
how-to-guides/data-governance|TP|07|gouvernance
how-to-guides/data-governance/classification|TP|08|classification
how-to-guides/data-governance/classification/assets|TP|08|étiquette
how-to-guides/data-governance/classification/auto-classification|TP|08|auto-classification
how-to-guides/data-governance/classification/auto-classification/auto-pii-tagging|TP|08|PII
how-to-guides/data-governance/classification/auto-classification/external-workflow|TP|08|classify
how-to-guides/data-governance/classification/auto-classification/workflow|TP|08|classify
how-to-guides/data-governance/classification/best-practices|doc|21|Bonnes pratiques
how-to-guides/data-governance/classification/classification|TP|08|classification
how-to-guides/data-governance/classification/manage-classification|TP|08|classification
how-to-guides/data-governance/classification/request-tags|TP|18|Demande de tag
how-to-guides/data-governance/classification/sample-data-using-pii-tag|TP|21|MASKED
how-to-guides/data-governance/classification/tiers|TP|18|tier
how-to-guides/data-governance/column-bulk-operations|ecran|17|Column Bulk Operations
how-to-guides/data-governance/glossary|TP|07|glossaire
how-to-guides/data-governance/glossary/approval|TP|21|Approved
how-to-guides/data-governance/glossary/assets|TP|07|rattach
how-to-guides/data-governance/glossary/best-practices|doc|21|Bonnes pratiques
how-to-guides/data-governance/glossary/create-terms|TP|07|terme
how-to-guides/data-governance/glossary/export|TP|19|Exporté
how-to-guides/data-governance/glossary/glossary-term|TP|07|terme
how-to-guides/data-governance/glossary/import|TP|19|Import
how-to-guides/data-governance/glossary/setup|TP|07|glossaire
how-to-guides/data-governance/glossary/styling|doc|21|Style
how-to-guides/data-governance/glossary/troubleshooting|doc|21|Dépannage
how-to-guides/data-governance/intake-forms|TP|21|Intake Form
how-to-guides/data-governance/metrics|TP|17|Métrique
how-to-guides/data-governance/ontology|ecran|17|Ontology Explorer
how-to-guides/data-governance/ontology/import|TP|21|SKOS
how-to-guides/data-governance/ontology/relationship-types|TP|21|Relation
how-to-guides/data-insights|ecran|17|Insights
how-to-guides/data-insights/data-culture|doc|22|culture
how-to-guides/data-insights/elasticsearch-reindex|TP|06|réindex
how-to-guides/data-insights/email-report|doc|22|Data Insights Report
how-to-guides/data-insights/ingestion|TP|16|DataInsights
how-to-guides/data-insights/kpi|TP|22|KPI
how-to-guides/data-insights/report|ecran|17|Insights
how-to-guides/data-insights/service-insights|ecran|23|Insights
how-to-guides/data-insights/tiering|TP|18|tier
how-to-guides/data-lineage|TP|06|lineage
how-to-guides/data-lineage/column|TP|11|colonne
how-to-guides/data-lineage/cross-database-lineage|doc|23|crossDatabaseServiceNames
how-to-guides/data-lineage/explore|ecran|11|lineage
how-to-guides/data-lineage/manual|TP|11|lineage
how-to-guides/data-lineage/openlineage|TP|23|OpenLineage
how-to-guides/data-lineage/workflow|TP|06|lineage
how-to-guides/data-marketplace|TP|17|Marketplace
how-to-guides/data-marketplace/data-products|TP|17|Produit de données
how-to-guides/data-marketplace/domains|TP|21|Sous-domaine
how-to-guides/data-quality-observability|TP|10|qualité
how-to-guides/data-quality-observability/alerts-notifications|TP|12|alerte
how-to-guides/data-quality-observability/alerts-notifications/alert-behavior-reference|doc|22|déclencheur
how-to-guides/data-quality-observability/alerts-notifications/data-observability-alerts|TP|12|Observability
how-to-guides/data-quality-observability/alerts-notifications/email-alerts-configuration|doc|22|alertes par e-mail
how-to-guides/data-quality-observability/alerts-notifications/generic-webhook-alerts-configuration|TP|12|webhook
how-to-guides/data-quality-observability/alerts-notifications/google-chat-alerts-configuration|TP|22|GChat
how-to-guides/data-quality-observability/alerts-notifications/microsoft-teams-alerts-configuration|TP|22|MsTeams
how-to-guides/data-quality-observability/alerts-notifications/notify-downstream|TP|22|notifyDownstream
how-to-guides/data-quality-observability/alerts-notifications/slack-alerts-configuration|TP|22|Slack
how-to-guides/data-quality-observability/alerts-notifications/system-governance-notifications|TP|12|Notification
how-to-guides/data-quality-observability/alerts-notifications/webhook-payloads-and-delivery|TP|12|charge
how-to-guides/data-quality-observability/incident-manager|TP|20|incident
how-to-guides/data-quality-observability/incident-manager/workflow|TP|20|Resolved
how-to-guides/data-quality-observability/profiler|TP|05|profil
how-to-guides/data-quality-observability/profiler/custom-metrics|TP|20|commandes_annulees
how-to-guides/data-quality-observability/profiler/external-workflow|TP|05|profile
how-to-guides/data-quality-observability/profiler/metrics|TP|05|nullCount
how-to-guides/data-quality-observability/profiler/profiler-workflow|TP|05|profile
how-to-guides/data-quality-observability/profiler/tab|ecran|05|Profile
how-to-guides/data-quality-observability/quality|TP|10|test
how-to-guides/data-quality-observability/quality/adding-test-suites|TP|10|suite
how-to-guides/data-quality-observability/quality/configure|TP|10|test
how-to-guides/data-quality-observability/quality/custom-tests|TP|20|testPlatforms
how-to-guides/data-quality-observability/quality/data-quality-as-code|TP|20|TestRunner
how-to-guides/data-quality-observability/quality/data-quality-as-code/advanced-usage|doc|20|from_yaml
how-to-guides/data-quality-observability/quality/data-quality-as-code/dataframe-validation|TP|20|DataFrameValidator
how-to-guides/data-quality-observability/quality/data-quality-as-code/dataframe-validation-chunking|doc|20|chunks
how-to-guides/data-quality-observability/quality/data-quality-as-code/getting-started|TP|20|TestRunner
how-to-guides/data-quality-observability/quality/data-quality-as-code/publishing-and-best-practices|doc|20|publish
how-to-guides/data-quality-observability/quality/data-quality-as-code/test-definitions|doc|20|metadata.sdk.data_quality
how-to-guides/data-quality-observability/quality/data-quality-as-code/test-definitions/column-tests|doc|20|ColumnValuesToBeBetween
how-to-guides/data-quality-observability/quality/data-quality-as-code/test-runner|TP|20|TestRunner
how-to-guides/data-quality-observability/quality/dimensional-validation|TP|20|dimension
how-to-guides/data-quality-observability/quality/import-export-test-cases|TP|19|Tests réimportés
how-to-guides/data-quality-observability/quality/import-export-test-cases/edit|doc|19|édition en ligne
how-to-guides/data-quality-observability/quality/import-export-test-cases/export|TP|19|Tests d'une table
how-to-guides/data-quality-observability/quality/import-export-test-cases/import|TP|19|Tests réimportés
how-to-guides/data-quality-observability/quality/tab|ecran|10|Data Observability
how-to-guides/data-quality-observability/quality/test|TP|10|test
how-to-guides/data-quality-observability/quality/test-cases-from-yaml-config|TP|10|testCases
how-to-guides/data-quality-observability/quality/test-library|ecran|17|Test Library
how-to-guides/data-quality-observability/quality/tests-ui|ecran|10|test
how-to-guides/data-quality-observability/quality/tests-ui/column-tests|ecran|10|colonne
how-to-guides/data-quality-observability/quality/tests-yaml|TP|10|YAML
how-to-guides/data-quality-observability/quality/tests-yaml-column-tests|TP|10|columnValues
how-to-guides/data-quality-observability/quality/visualize|ecran|10|résultat
how-to-guides/guide-for-data-users|ecran|03|fiche
how-to-guides/guide-for-data-users/add-announcement|TP|17|annonce
how-to-guides/guide-for-data-users/announcements|TP|17|annonce
how-to-guides/guide-for-data-users/basics-openmetadata|ecran|03|fiche
how-to-guides/guide-for-data-users/browser-ext|doc|18|extension
how-to-guides/guide-for-data-users/custom|TP|18|propriété personnalisée
how-to-guides/guide-for-data-users/data-asset-tabs|ecran|03|onglet
how-to-guides/guide-for-data-users/data-ownership|TP|09|propriétaire
how-to-guides/guide-for-data-users/delete|TP|18|Suppression
how-to-guides/guide-for-data-users/description|TP|18|description
how-to-guides/guide-for-data-users/follow-data-asset|TP|18|Abonnés
how-to-guides/guide-for-data-users/glossary|TP|07|glossaire
how-to-guides/guide-for-data-users/personal-access-token|TP|18|jeton personnel
how-to-guides/guide-for-data-users/request-description|TP|18|Demande de description
how-to-guides/guide-for-data-users/request-tags|TP|18|Demande de tag
how-to-guides/guide-for-data-users/tags|TP|08|étiquette
how-to-guides/guide-for-data-users/versions|TP|18|version
how-to-guides/mcp|TP|17|MCP
how-to-guides/mcp/agent-frameworks|doc|24|CrewAI
how-to-guides/mcp/claude|doc|24|Claude Desktop
how-to-guides/mcp/claude-code|doc|24|Claude Code
how-to-guides/mcp/connect|TP|24|client
how-to-guides/mcp/connect-api|TP|17|JSON-RPC
how-to-guides/mcp/cursor|doc|24|Cursor
how-to-guides/mcp/databricks|doc|24|Databricks
how-to-guides/mcp/goose|doc|24|Goose
how-to-guides/mcp/oauth|doc|24|OAuth
how-to-guides/mcp/reference|TP|24|search_metadata
how-to-guides/mcp/semantic-search|doc|24|semantic_search
how-to-guides/mcp/vscode|doc|24|VS Code
connecteurs/base-de-donnees|TP|04|Postgres
connecteurs/messages|TP|23|Redpanda
connecteurs/stockage|TP|23|manifeste
connecteurs/modeles|TP|23|MLflow
connecteurs/tableaux-de-bord|TP|23|Metabase
connecteurs/orchestration|TP|23|Airflow
connecteurs/recherche|TP|23|Elasticsearch
connecteurs/api|TP|23|OpenAPI
connecteurs/dbt|TP|23|dbt
connecteurs/maison|TP|15|connecteur
connecteurs/catalogues-tiers|doc|23|Alation
connecteurs/espaces-de-fichiers|doc|23|Google Drive
deploiement/installation-docker|TP|02|compose
deploiement/montee-de-version|doc|16|montée de version
deploiement/sso|doc|22|SSO
deploiement/scim|doc|22|SCIM
deploiement/sauvegarde|doc|22|Sauvegarde
deploiement/kubernetes|doc|22|Kubernetes
deploiement/rdf|doc|22|RDF
deploiement/ingestion-externe|doc|22|Ingestion externe
""".strip().splitlines()

# Des fonctions que la 2.0 cite mais que ce cours ne fait pas tourner et n'explique pas en détail.
ABSENT = [
    "how-to-guides/data-quality-observability/anomaly-detection (Collate, simple mention au chapitre 20)",
]


def main() -> int:
    chapitres = {f.name[:2]: f.read_text().lower() for f in (ROOT / "cours").glob("[0-9][0-9]-*.md")}
    niveaux: Counter[str] = Counter()
    par_section: dict[str, Counter[str]] = {}
    erreurs = []
    for ligne in LIGNES:
        page, niveau, chapitre, mot = ligne.split("|")
        niveaux[niveau] += 1
        parties = page.split("/")
        section = parties[1] if parties[0] == "how-to-guides" and len(parties) > 1 else parties[0]
        par_section.setdefault(section, Counter())[niveau] += 1
        if mot.lower() not in chapitres.get(chapitre, ""):
            erreurs.append(f"{page} : « {mot} » absent du chapitre {chapitre}")

    total = sum(niveaux.values())
    print(f"{total} sujets de référence\n")
    print(f"{'Section':<30} {'TP':>4} {'écran':>6} {'doc':>4}")
    for section, c in sorted(par_section.items()):
        print(f"{section:<30} {c['TP']:>4} {c['ecran']:>6} {c['doc']:>4}")
    print()
    print(f"Exécuté par un TP      : {niveaux['TP']:>3}  ({niveaux['TP'] / total:.0%})")
    print(f"Écran ouvert et capturé : {niveaux['ecran']:>3}  ({niveaux['ecran'] / total:.0%})")
    print(f"Expliqué, sans essai    : {niveaux['doc']:>3}  ({niveaux['doc'] / total:.0%})")
    print(f"\nEssayé pour de vrai (TP + écran) : {(niveaux['TP'] + niveaux['ecran']) / total:.0%}")
    print(f"\nHors décompte : {'; '.join(ABSENT)}")
    if erreurs:
        print(f"\n{len(erreurs)} ligne(s) sans appui dans le chapitre cité :")
        for e in erreurs:
            print(f"  {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
