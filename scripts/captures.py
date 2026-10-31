#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.12.*"
# dependencies = ["playwright==1.58.0", "pillow==11.3.0"]
# ///
"""Génère les captures d'écran du mode d'emploi, dans cours/img/.

    ./omlab captures           toutes les captures
    ./omlab captures 07 10     seulement ces chapitres

Les captures sortent de l'instance du laboratoire, dans un vrai navigateur :
après une montée de version, cette commande refait le manuel d'un coup. Il faut
que tous les TP aient tourné, sans quoi les écrans montreront un catalogue vide.

Le script ne fait que regarder : il ouvre des formulaires sans jamais les
valider, et ne modifie rien dans OpenMetadata. Les pastilles rouges numérotées
sont ajoutées à la page le temps de la capture ; le texte du chapitre y renvoie.
"""

import os
import sys
from collections.abc import Callable
from pathlib import Path

from PIL import Image
from playwright.sync_api import Locator, Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SORTIE = ROOT / "cours" / "img"
OM = os.environ.get("OM_HOST", "http://localhost:8585")
WEBHOOK = f"http://localhost:{os.environ.get('OMLAB_WEBHOOK_PORT', '8010')}"
ADMIN = os.environ.get("OM_ADMIN_USER", "admin@open-metadata.org")
MOT_DE_PASSE = os.environ.get("OM_ADMIN_PASSWORD", "admin")

# Double densité : GitHub réduit l'image à la largeur de la page, et le lecteur
# doit pouvoir zoomer sur un libellé sans qu'il devienne flou.
DENSITE = 2

SERVICE = "omlab_postgres.omlab"
CUSTOMERS = f"/table/{SERVICE}.raw.customers"
ORDERS = f"/table/{SERVICE}.raw.orders"
EMPLOYEES = f"/table/{SERVICE}.raw.employees"
FCT_ORDERS = f"/table/{SERVICE}.analytics.fct_orders"
REVENUE = f"/table/{SERVICE}.analytics.v_revenue_monthly"

PASTILLE = """([x, y, l, h, n]) => {
  const cadre = document.createElement('div');
  cadre.className = 'omlab-pastille';
  cadre.style.cssText = `position:fixed;left:${x - 3}px;top:${y - 3}px;width:${l + 6}px;
    height:${h + 6}px;border:2px solid #e5484d;border-radius:6px;z-index:99998;pointer-events:none`;
  const rond = document.createElement('div');
  rond.className = 'omlab-pastille';
  rond.textContent = n;
  rond.style.cssText = `position:fixed;left:${Math.max(x - 13, 2)}px;top:${Math.max(y - 13, 2)}px;
    width:22px;height:22px;border-radius:50%;background:#e5484d;color:#fff;font:700 13px/22px sans-serif;
    text-align:center;z-index:99999;pointer-events:none;box-shadow:0 0 0 2px #fff`;
  document.body.append(cadre, rond);
}"""


class Manuel:
    """La page, plus ce qu'il faut pour annoter et enregistrer une capture."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.numero = 0

    def tid(self, testid: str) -> Locator:
        return self.page.get_by_test_id(testid).first

    def ouvrir(self, chemin: str, hauteur: int = 900, attente: int = 1500) -> None:
        self.page.set_viewport_size({"width": 1440, "height": hauteur})
        url = chemin if chemin.startswith("http") else OM + chemin
        self.page.goto(url)
        self.reposer(attente)

    def reposer(self, attente: int = 800) -> None:
        try:
            self.page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # un écran qui interroge en continu ne doit pas bloquer la capture
        self.page.wait_for_timeout(attente)

    def noter(self, *cibles: Locator | str) -> None:
        """Encadre chaque cible et lui donne le numéro suivant."""
        for cible in cibles:
            element = self.tid(cible) if isinstance(cible, str) else cible
            boite = element.bounding_box(timeout=5000)
            # Défiler décale tout l'écran : on ne le fait que si la cible est hors champ.
            if boite["y"] < 0 or boite["y"] > self.page.viewport_size["height"] - 30:
                element.scroll_into_view_if_needed(timeout=5000)
                boite = element.bounding_box(timeout=5000)
            self.pastille(boite["x"], boite["y"], boite["width"], boite["height"])

    def noter_fil_ariane(self) -> None:
        """Encadre le fil d'Ariane lui-même : son conteneur prend toute la largeur."""
        boites = [e.bounding_box() for e in self.page.get_by_test_id("breadcrumb").first.locator("li").all()]
        droite = max(b["x"] + b["width"] for b in boites)
        self.pastille(boites[0]["x"], boites[0]["y"], droite - boites[0]["x"], boites[0]["height"])

    def pastille(self, x: float, y: float, largeur: float, hauteur: float) -> None:
        self.numero += 1
        self.page.evaluate(PASTILLE, [x, y, largeur, hauteur, self.numero])

    def enregistrer(self, nom: str, cadre: tuple[int, int, int, int] | None = None) -> None:
        chemin = SORTIE / f"{nom}.png"
        self.page.mouse.move(0, 0)  # une souris laissée sur un nom ouvre une carte de profil
        self.page.wait_for_timeout(400)
        options = {"x": cadre[0], "y": cadre[1], "width": cadre[2], "height": cadre[3]} if cadre else None
        self.page.screenshot(path=chemin, clip=options, animations="disabled")
        # 256 couleurs suffisent à une interface et divisent le poids par trois ;
        # sans tramage, le texte reste net quand on zoome.
        Image.open(chemin).convert("RGB").quantize(256, method=2, dither=Image.Dither.NONE).save(chemin, optimize=True)
        self.page.evaluate("document.querySelectorAll('.omlab-pastille').forEach(e => e.remove())")
        self.numero = 0
        print(f"  {nom}.png")

    def recadrer_lineage(self) -> None:
        self.tid("toggle-mind-map").click()  # la mini-carte masque le bas du graphe
        self.tid("fit-screen").click()
        self.page.get_by_text("Fit to screen").click()
        self.page.wait_for_timeout(1000)

    def replier_panneau(self) -> None:
        """Replie le panneau de droite : le tableau des colonnes gagne toute la largeur."""
        self.tid("tab-expand-button").click()
        self.page.mouse.move(700, 5)  # sinon l'infobulle du bouton reste sur la capture
        self.page.wait_for_timeout(800)


# ---------------------------------------------------------------------
# Chapitre par chapitre
# ---------------------------------------------------------------------
def chapitre_01(m: Manuel) -> None:
    m.ouvrir(CUSTOMERS)
    m.noter_fil_ariane()
    m.noter("entity-header-name")
    m.enregistrer("01-fil-ariane", (240, 66, 1200, 124))


def chapitre_02(m: Manuel) -> None:
    m.ouvrir("/my-data")
    m.tid("welcome-screen-close-btn").click()
    m.page.add_style_tag(content="[data-testid='whats-new-alert-card'] { display: none }")
    m.reposer(1500)
    m.noter(
        "side-bar-app-bar-item-explore",
        "side-bar-observability",
        "side-bar-governance",
        m.page.locator("[data-testid='left-sidebar'] a[href='/settings']").locator("xpath=ancestor::li[1]"),
    )
    m.enregistrer("02-accueil")

    m.ouvrir("/settings")
    m.enregistrer("02-reglages")

    m.ouvrir("http://localhost:8080/", attente=2500)
    m.page.fill("input[name=username]", "admin")
    m.page.fill("input[name=password]", "admin")
    m.page.keyboard.press("Enter")
    m.page.wait_for_timeout(3000)
    m.ouvrir("http://localhost:8080/dags", attente=2500)
    m.enregistrer("02-airflow")


def chapitre_03(m: Manuel) -> None:
    m.ouvrir("/explore/tables?search=signup")
    m.noter(m.page.locator(".explore-search-card, [data-testid*='table-data-card']").first)
    m.noter("search-dropdown-Owners")
    m.enregistrer("03-recherche")

    m.ouvrir(ORDERS, hauteur=1250)
    m.noter_fil_ariane()
    m.noter(
        "entity-follow-button",
        "version-button",
        "data-asset-header-metadata",
        "tabs",
        "asset-description-container",
        "entity-table",
    )
    m.enregistrer("03-fiche")

    m.tid("edit-description").click()
    m.page.wait_for_timeout(1500)
    m.enregistrer("03-description")

    m.ouvrir(f"{ORDERS}/versions/0.2")
    m.noter(m.page.get_by_text("Versions History").first)
    m.enregistrer("03-versions")


def chapitre_04(m: Manuel) -> None:
    m.ouvrir("/settings/services/databases")
    m.noter("add-service-button", m.page.get_by_text("omlab_postgres").first)
    m.enregistrer("04-services")

    m.ouvrir("/databaseServices/add-service")
    m.page.get_by_placeholder("Search for a connector").fill("postgres")
    m.page.wait_for_timeout(500)
    m.noter("Postgres")
    m.enregistrer("04-ajout-service")

    m.tid("Postgres").click()
    m.reposer()
    # Assez haut pour tout voir : un défilement décalerait les pastilles déjà posées.
    m.page.set_viewport_size({"width": 1440, "height": 1500})
    m.page.wait_for_timeout(800)
    m.noter(m.page.get_by_placeholder("Service Name"), "test-connection-btn", "next-button")
    m.enregistrer("04-connexion")

    m.ouvrir("/service/databaseServices/omlab_postgres/ingestions")
    m.page.get_by_role("tab", name="Connection").click()
    m.reposer(1500)
    m.noter(m.page.get_by_role("tab", name="Agents"), m.page.get_by_role("tab", name="Connection"))
    m.noter(m.page.get_by_role("button", name="Test Connection"))
    m.enregistrer("04-connexion-test")

    m.page.get_by_role("tab", name="Agents").click()
    m.reposer(2500)
    m.enregistrer("04-agents")


def chapitre_05(m: Manuel) -> None:
    m.ouvrir(f"{CUSTOMERS}/profiler", hauteur=1000)
    m.noter("profiler", m.page.get_by_role("tab", name="Table Profile"))
    m.enregistrer("05-profil-table")

    m.ouvrir(f"{CUSTOMERS}/profiler/column-profile", hauteur=1200)
    m.noter(m.page.get_by_role("tab", name="Column Profile"), m.page.locator("tr", has_text="country").first)
    m.enregistrer("05-profil-colonnes")

    m.ouvrir(f"{CUSTOMERS}/profiler/column-profile?activeColumnFqn={SERVICE}.raw.customers.country", hauteur=1100, attente=3000)
    m.enregistrer("05-profil-country")


def chapitre_06(m: Manuel) -> None:
    m.ouvrir(f"{REVENUE}/lineage", hauteur=1000, attente=2500)
    m.recadrer_lineage()
    m.noter("lineage", m.page.get_by_role("tab", name="Impact Analysis"), "lineage-layer-btn")
    m.enregistrer("06-lineage")

    m.tid("lineage-layer-btn").click()
    m.page.wait_for_timeout(500)
    m.tid("lineage-layer-column-btn").click()
    m.page.keyboard.press("Escape")  # le menu des calques bloque le reste de l'écran
    m.page.wait_for_timeout(2000)
    m.tid("fit-screen").click()
    m.page.get_by_text("Fit to screen").click()
    m.page.wait_for_timeout(1000)
    m.tid(f"column-{SERVICE}.analytics.v_revenue_monthly.revenue").click(force=True)
    m.page.mouse.move(700, 5)
    m.page.wait_for_timeout(1000)
    m.enregistrer("06-lineage-colonnes")

    m.ouvrir(f"{ORDERS}/lineage", hauteur=1000, attente=2500)
    m.page.get_by_role("tab", name="Impact Analysis").click()
    m.reposer(2000)
    m.enregistrer("06-impact")

    m.ouvrir(f"{CUSTOMERS}/table_queries", hauteur=1000)
    m.noter("table_queries")
    m.enregistrer("06-requetes")

    m.ouvrir("/explore/tables?search=omlab", hauteur=1000, attente=2500)
    m.noter(m.page.get_by_text("Popularity").first)
    m.enregistrer("06-popularite")


def chapitre_07(m: Manuel) -> None:
    m.ouvrir("/glossary/Commerce", hauteur=1000)
    m.noter("side-bar-governance", m.page.get_by_role("tab", name="Terms"), "add-new-tag-button-header")
    m.enregistrer("07-glossaire")

    m.ouvrir("/glossary/Commerce.ChiffreAffaires", hauteur=1000)
    m.noter(m.page.get_by_text("Synonyms").first, m.page.get_by_role("tab", name="Assets"))
    m.enregistrer("07-terme")

    m.ouvrir("/glossary/Commerce.ChiffreAffaires/assets", hauteur=1000)
    m.enregistrer("07-terme-assets")

    m.ouvrir("/explore/glossaries?search=CA", attente=2500)
    m.noter("searchBox")
    m.enregistrer("07-recherche-synonyme")

    m.ouvrir(ORDERS, hauteur=1000)
    m.replier_panneau()
    m.noter(m.page.locator("tr[data-row-key$='.amount'] [data-testid='tag-Commerce.ChiffreAffaires']"))
    m.enregistrer("07-colonne-terme")


def chapitre_08(m: Manuel) -> None:
    m.ouvrir(CUSTOMERS, hauteur=1250)
    m.replier_panneau()
    m.noter(m.page.locator("tr[data-row-key$='.email'] [data-testid^='classification-tags']"))
    m.enregistrer("08-pii-customers")

    m.ouvrir(EMPLOYEES, hauteur=1400)
    m.replier_panneau()
    m.noter(
        m.page.locator("tr[data-row-key$='.full_name'] [data-testid^='classification-tags']"),
        m.page.locator("tr[data-row-key$='.email'] [data-testid^='classification-tags']"),
        m.page.locator("tr[data-row-key$='.phone'] [data-testid^='classification-tags']"),
        m.page.locator("tr[data-row-key$='.national_id'] [data-testid^='classification-tags']"),
    )
    m.enregistrer("08-pii-employees")

    m.page.locator("tr[data-row-key$='.national_id'] [data-testid^='classification-tags'] [data-testid='add-tag']").click()
    m.page.wait_for_timeout(500)
    # « Search Tags » est un simple libellé : le vrai champ est la liste déroulante de la ligne.
    m.page.locator("tr[data-row-key$='.national_id'] input[role='combobox']").fill("PII")
    m.reposer(1200)
    m.enregistrer("08-poser-etiquette")

    m.ouvrir(f"{EMPLOYEES}/sample_data", hauteur=1000)
    m.noter("sample_data")
    m.enregistrer("08-echantillon")


def chapitre_09(m: Manuel) -> None:
    m.ouvrir("/settings/members/teams/data_platform")
    m.noter(m.page.get_by_role("tab", name="Users"), m.page.get_by_role("tab", name="Roles"))
    m.enregistrer("09-equipe")

    m.ouvrir("/settings/access/roles/omlab_data_steward")
    m.enregistrer("09-role")

    m.ouvrir("/settings/access/policies/omlab_donnees_rh", hauteur=1000)
    m.noter(m.page.get_by_text("autoriser_documentation").first, m.page.get_by_text("interdire_echantillons_rh").first)
    m.enregistrer("09-politique")


def chapitre_10(m: Manuel) -> None:
    m.ouvrir("/data-quality/test-cases", hauteur=1200, attente=2500)
    m.noter("side-bar-observability", m.page.get_by_role("tab", name="Test Cases"))
    m.enregistrer("10-vue-qualite")

    m.ouvrir(f"{ORDERS}/profiler/data-quality", hauteur=1100, attente=2500)
    m.noter("profiler", m.page.get_by_role("tab", name="Data Quality"), m.page.get_by_role("tab", name="Incidents"))
    m.enregistrer("10-table-qualite")

    m.ouvrir(f"/test-case/{SERVICE}.raw.orders.orders_aucun_montant_negatif/test-case-results", hauteur=1000, attente=2500)
    m.enregistrer("10-resultat-test")

    m.ouvrir("/incident-manager", hauteur=900, attente=2500)
    m.noter(m.page.locator("tr", has_text="orders_aucun_montant_negatif").first)
    m.enregistrer("10-incidents")

    m.tid("orders_aucun_montant_negatif-status").click()
    m.page.wait_for_timeout(800)
    m.enregistrer("10-incident-statut")


def chapitre_11(m: Manuel) -> None:
    m.ouvrir(f"{FCT_ORDERS}/lineage", hauteur=1000, attente=2500)
    m.recadrer_lineage()
    m.noter("edit-lineage")
    m.enregistrer("11-lineage-fct-orders")

    m.tid(f"edge-{SERVICE}.raw.orders-{SERVICE}.analytics.fct_orders").dispatch_event("click")
    m.reposer(1500)
    m.enregistrer("11-arete-manuelle")


def chapitre_12(m: Manuel) -> None:
    m.ouvrir("/observability/alerts")
    m.noter("side-bar-observability", m.page.get_by_text("Tests de qualité en échec").first)
    m.enregistrer("12-alertes-observabilite")

    m.page.get_by_text("Tests de qualité en échec").first.click()
    m.reposer(1500)
    m.page.set_viewport_size({"width": 1440, "height": 1100})
    m.page.wait_for_timeout(500)
    m.enregistrer("12-alerte-detail")

    m.ouvrir("/settings/notifications/alerts")
    m.noter(m.page.get_by_text("Tables modifiées").first)
    m.enregistrer("12-notifications")

    m.ouvrir(f"{WEBHOOK}/", attente=500)
    m.enregistrer("12-webhook")


def chapitre_13(m: Manuel) -> None:
    m.ouvrir("/docs", attente=3000)
    m.enregistrer("13-swagger")


def chapitre_14(m: Manuel) -> None:
    m.ouvrir(ORDERS, hauteur=1000)
    m.noter("owner-label", "header-tier-container", "asset-description-container")
    m.enregistrer("14-fiche-enrichie")

    m.ouvrir(f"{EMPLOYEES}/custom_properties")
    m.noter("custom_properties", "retentionMonths")
    m.enregistrer("14-propriete")


def chapitre_15(m: Manuel) -> None:
    m.ouvrir("/service/databaseServices/omlab_fichiers/databases")
    m.noter(m.page.get_by_role("tab", name="Databases"), m.page.get_by_text("exports", exact=True).first)
    m.enregistrer("15-service")

    m.ouvrir("/table/omlab_fichiers.exports.ventes.objectifs_2026", hauteur=1000)
    m.noter_fil_ariane()
    m.noter("entity-table")
    m.enregistrer("15-table-csv")


def chapitre_16(m: Manuel) -> None:
    m.ouvrir(f"{REVENUE}/contract", hauteur=1200, attente=2500)
    m.noter("contract")
    m.enregistrer("16-contrat")

    m.ouvrir("/settings/apps", attente=4000)
    m.enregistrer("16-applications")


def chapitre_17(m: Manuel) -> None:
    m.ouvrir("/data-marketplace", hauteur=1000, attente=2500)
    m.noter(m.page.get_by_text("Chiffre d'affaires mensuel").first, m.page.get_by_text("Ventes", exact=True).first)
    m.enregistrer("17-marketplace")

    m.ouvrir("/domain/Ventes", hauteur=800)
    m.noter(m.page.get_by_role("tab", name="Data Products"), m.page.get_by_role("tab", name="Assets"))
    m.enregistrer("17-domaine")

    m.ouvrir("/dataProduct/ca_mensuel/assets", hauteur=1000, attente=2500)
    m.noter(m.page.get_by_role("tab", name="Assets"), m.page.get_by_role("tab", name="Input/Output Ports"))
    m.enregistrer("17-produit")

    m.ouvrir("/metric/ca_mensuel_net", hauteur=800)
    m.page.get_by_role("tab", name="Expression").click()
    m.reposer(1000)
    m.noter(m.page.get_by_role("tab", name="Expression"))
    m.enregistrer("17-metrique")

    m.ouvrir(f"{ORDERS}/activity_feed/tasks", hauteur=1000, attente=2500)
    m.noter(m.page.get_by_text("Refonte de raw.orders").first, m.page.get_by_role("tab", name="Activity Feeds & Tasks"))
    m.enregistrer("17-annonce-taches")

    m.ouvrir("/context-center/articles/lire_les_avoirs", hauteur=900)
    m.noter(m.page.get_by_text("Data Assets", exact=True).first)
    m.enregistrer("17-article")

    m.ouvrir("/governance/ontology", hauteur=900, attente=3000)
    m.enregistrer("17-ontologie")

    m.ouvrir("/workflows", hauteur=900)
    m.enregistrer("17-workflows")

    m.ouvrir("/settings/governance/intake-forms", hauteur=700)
    m.enregistrer("17-intake")

    m.ouvrir("/column-bulk-operations", hauteur=900, attente=2500)
    m.enregistrer("17-colonnes")

    m.ouvrir("/test-library", hauteur=900)
    m.enregistrer("17-test-library")

    m.ouvrir("/lineage", hauteur=900, attente=3000)
    m.enregistrer("17-lineage-service")

    m.ouvrir("/data-insights/data-assets", hauteur=1000, attente=3000)
    m.enregistrer("17-insights")

    m.ouvrir("/settings/apps/McpApplication", hauteur=900)
    m.enregistrer("17-mcp")


def chapitre_18(m: Manuel) -> None:
    m.ouvrir(f"{ORDERS}/custom_properties", hauteur=700)
    m.noter(m.page.get_by_text("frequenceMaj").first, m.page.get_by_text("Tier1").first)
    m.enregistrer("18-propriete")

    m.ouvrir(f"{CUSTOMERS}/activity_feed/all", hauteur=900, attente=2500)
    m.noter(m.page.get_by_text("Pourquoi 39 pays").first, m.page.get_by_text("Oui, ce fichier").first)
    m.enregistrer("18-conversation")

    m.ouvrir(f"{ORDERS}/versions/0.4", hauteur=900, attente=2500)
    m.enregistrer("18-versions")

    m.ouvrir("/users/admin/access-token", hauteur=700)
    m.enregistrer("18-jeton")


def chapitre_19(m: Manuel) -> None:
    m.ouvrir("/bulk/import/glossary/Commerce", hauteur=800, attente=2500)
    m.enregistrer("19-import-glossaire")

    m.ouvrir("/bulk/import/table/omlab_postgres.omlab.raw.products", hauteur=800, attente=2500)
    m.enregistrer("19-import-table")


def chapitre_20(m: Manuel) -> None:
    m.ouvrir(f"/test-case/{SERVICE}.raw.customers.country.customers_pays_par_activite", hauteur=1000, attente=3000)
    m.page.get_by_role("tab", name="Dimensionality").click()
    m.reposer(2500)
    m.noter(m.page.get_by_role("tab", name="Dimensionality"))
    m.enregistrer("20-test-dimension")

    m.ouvrir(f"{ORDERS}/profiler/table-profile", hauteur=1000, attente=3000)
    cible = m.page.get_by_text("commandes_annulees").first
    cible.scroll_into_view_if_needed(timeout=10000)
    m.reposer(1500)
    m.noter(cible)
    m.enregistrer("20-metrique-maison")

    m.ouvrir("/incident-manager", hauteur=900, attente=2500)
    m.enregistrer("20-incidents")

    m.ouvrir(f"/test-case/{SERVICE}.raw.orders.rapprochement_compta", hauteur=900, attente=2500)
    m.enregistrer("20-test-externe")


def chapitre_21(m: Manuel) -> None:
    m.ouvrir("/glossary/Finance.MargeBrute", hauteur=800)
    m.noter(m.page.get_by_text("Approved").first, m.page.get_by_text("Workflow History").first, m.page.get_by_text("Reviewers").first)
    m.enregistrer("21-terme-approuve")

    m.ouvrir("/glossary/Logistique", hauteur=800)
    m.enregistrer("21-skos")

    m.ouvrir("/settings/governance/glossary-term-relations", hauteur=900)
    m.enregistrer("21-relations")

    m.ouvrir("/workflows", hauteur=800, attente=2500)
    m.page.get_by_text("Glossary Approval Workflow", exact=True).first.click()
    m.reposer(3500)
    m.enregistrer("21-workflow")

    m.ouvrir("/settings/preferences/dataAssetRules", hauteur=800, attente=2500)
    m.enregistrer("21-regles")


def chapitre_22(m: Manuel) -> None:
    m.ouvrir("/settings/members/teams/Commerce", hauteur=700)
    m.enregistrer("22-equipes")

    m.ouvrir("/settings/persona/DataSteward", hauteur=700)
    m.enregistrer("22-persona")

    m.ouvrir("/settings/access/permission-debugger", hauteur=900, attente=2500)
    champ = m.page.get_by_role("combobox").last
    champ.click()
    champ.fill("relectrice")
    m.reposer(2500)
    m.page.locator(".ant-select-dropdown:visible .ant-select-item-option").first.click()
    m.reposer(3000)
    m.enregistrer("22-permissions")

    m.ouvrir("/settings/access/audit-logs", hauteur=900, attente=5000)
    m.enregistrer("22-audit")

    m.ouvrir("/settings/preferences/om-health", hauteur=1000, attente=4000)
    m.noter(m.page.get_by_text("Object Storage").first)
    m.enregistrer("22-sante")

    m.ouvrir("/settings/preferences/search-settings", hauteur=900, attente=2500)
    m.enregistrer("22-recherche")

    m.ouvrir("/data-insights/kpi", hauteur=800, attente=2500)
    m.enregistrer("22-kpi")


def chapitre_23(m: Manuel) -> None:
    m.ouvrir(f"/table/{SERVICE}.analytics.v_revenue_monthly/lineage", hauteur=1000, attente=3500)
    m.recadrer_lineage()
    m.enregistrer("23-lineage-complet")

    m.ouvrir(f"/table/{SERVICE}.analytics_dbt.ventes_par_pays/dbt", hauteur=900, attente=2500)
    m.enregistrer("23-dbt")

    m.ouvrir('/topic/omlab_kafka."commandes.creees"/schema', hauteur=800, attente=2500)
    m.enregistrer("23-topic")

    m.ouvrir("/mlmodel/omlab_mlflow.prevision_ventes/details", hauteur=900, attente=2500)
    m.enregistrer("23-modele")

    m.ouvrir("/container/omlab_s3.omlab-lac.stocks/schema", hauteur=800, attente=2500)
    m.enregistrer("23-conteneur")

    m.ouvrir("/service/pipelineServices/omlab_airflow/pipelines", hauteur=800, attente=3000)
    m.enregistrer("23-airflow")

    m.ouvrir("/apiEndpoint/omlab_api.commandes.%2Fcommandes%2F%7Bid%7D%2Fget", hauteur=800, attente=4000)
    m.enregistrer("23-api")


def chapitre_24(m: Manuel) -> None:
    m.ouvrir(f"/table/{SERVICE}.raw.products/contract", hauteur=1000, attente=3000)
    m.enregistrer("24-contrat")

    m.ouvrir("/context-center/memories", hauteur=800, attente=2500)
    m.enregistrer("24-memoires")


CHAPITRES: dict[str, Callable[[Manuel], None]] = {
    nom.removeprefix("chapitre_"): f for nom, f in list(globals().items()) if nom.startswith("chapitre_")
}


def connexion_anonyme(navigateur) -> None:
    page = navigateur.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=DENSITE, locale="en-US")
    m = Manuel(page)
    m.ouvrir("/signin")
    m.tid("email").wait_for(timeout=30000)  # sans cache, la première page tarde à se construire
    m.noter("email", "password", "login")
    m.enregistrer("02-connexion")
    page.close()


def main() -> int:
    demandes = sys.argv[1:] or sorted(CHAPITRES)
    SORTIE.mkdir(parents=True, exist_ok=True)
    echecs = 0
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        if "02" in demandes:
            connexion_anonyme(navigateur)
        contexte = navigateur.new_context(
            viewport={"width": 1440, "height": 900}, device_scale_factor=DENSITE, locale="en-US"
        )
        page = contexte.new_page()
        page.goto(f"{OM}/signin")
        page.fill("#email", ADMIN)
        page.fill("#password", MOT_DE_PASSE)
        page.click("button[type=submit]")
        page.wait_for_url(lambda url: "/signin" not in url, timeout=30000)
        for numero in demandes:
            print(f"Chapitre {numero}")
            try:
                CHAPITRES[numero](Manuel(page))
            except Exception as exc:
                echecs += 1
                print(f"  ÉCHEC : {str(exc).splitlines()[0]}")
        navigateur.close()
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
