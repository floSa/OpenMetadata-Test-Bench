#!/usr/bin/env python3
"""Vérifie que les TP d'un chapitre ont bien produit ce qu'ils devaient.

    ./omlab check          toutes les vérifications
    ./omlab check 04       seulement le chapitre 04

Ces contrôles interrogent l'API : ils constatent l'état réel du catalogue,
pas ce que les logs ont bien voulu afficher. Un chapitre non encore fait
apparaît en échec — c'est normal, c'est votre liste de courses.
"""

import sys
import urllib.parse

sys.path.insert(0, "/omlab")

from lib.om import Check, api, fqn

SERVICE = "omlab_postgres"


def get(path: str):
    """GET tolérant : renvoie None sur 404 au lieu de tout arrêter."""
    try:
        return api(path)
    except SystemExit:
        return None


# ---------------------------------------------------------------------
def check_04(c: Check) -> None:
    """Ingestion des métadonnées."""
    tables = api(f"/tables?limit=100&database={SERVICE}.omlab")["data"]
    noms = {t["fullyQualifiedName"].replace(f"{SERVICE}.omlab.", "") for t in tables}
    attendues = {
        "raw.customers", "raw.orders", "raw.order_items", "raw.products",
        "raw.employees", "analytics.dim_customer", "analytics.fct_orders",
        "analytics.v_revenue_monthly", "analytics.v_customer_360",
    }
    c.expect(attendues <= noms, f"les 9 tables du playground sont cataloguées ({len(noms)} trouvées)")

    vues = [t for t in tables if t["tableType"] == "View"]
    c.expect(len(vues) == 2, f"les 2 vues sont reconnues comme des vues ({len(vues)})")

    orders = api(f"/tables/name/{fqn('raw', 'orders')}")
    c.expect(len(orders["columns"]) == 6, "raw.orders a bien 6 colonnes")


def check_05(c: Check) -> None:
    """Profiler."""
    col = "country"
    res = get(
        f"/tables/{urllib.parse.quote(fqn('raw', 'customers'))}.{col}"
        f"/columnProfile?startTs=0&endTs=99999999999999"
    )
    profils = (res or {}).get("data") or []
    c.expect(bool(profils), "un profil existe pour raw.customers.country")
    if profils:
        nulls = profils[0].get("nullCount")
        c.expect(nulls == 39, f"le profiler compte 39 pays manquants (trouvé {nulls})")


def check_06(c: Check) -> None:
    """Usage et lineage automatique."""
    tables = api("/tables?limit=100&fields=usageSummary")["data"]
    avec_usage = [
        t for t in tables
        if (t.get("usageSummary") or {}).get("weeklyStats", {}).get("count", 0) > 0
    ]
    c.expect(len(avec_usage) >= 5, f"au moins 5 tables ont des statistiques d'usage ({len(avec_usage)})")

    graphe = api(
        f"/lineage/table/name/{urllib.parse.quote(fqn('analytics', 'fct_orders'))}"
        "?upstreamDepth=2&downstreamDepth=2"
    )
    amont = graphe.get("upstreamEdges", [])
    c.expect(len(amont) >= 2, f"fct_orders a au moins 2 sources en amont ({len(amont)})")

    avec_colonnes = [
        e for e in amont
        if (e.get("lineageDetails") or {}).get("columnsLineage")
    ]
    c.expect(bool(avec_colonnes), "le lineage descend au niveau des colonnes")


def check_07(c: Check) -> None:
    """Glossaire."""
    glossaire = get("/glossaries/name/Commerce")
    c.expect(glossaire is not None, "le glossaire Commerce existe")

    # Le filtre `glossary` attend l'identifiant, pas le nom : passer
    # "Commerce" renvoie une liste vide, sans la moindre erreur.
    termes = get(f"/glossaryTerms?glossary={glossaire['id']}&limit=50") if glossaire else None
    noms = {t["name"] for t in (termes or {}).get("data", [])}
    c.expect(
        {"Client", "Commande", "ChiffreAffaires", "Avoir"} <= noms,
        f"les 4 termes sont créés ({sorted(noms)})",
    )

    # `fields=columns,tags` et non `fields=columns` : les colonnes sont
    # renvoyées d'office, mais LEURS ÉTIQUETTES non. Sans `tags`, la liste
    # arrive vide — et on croit à tort que les étiquettes ont disparu.
    orders = api(f"/tables/name/{fqn('raw', 'orders')}?fields=columns,tags")
    tags_amount = [
        t["tagFQN"]
        for col in orders["columns"] if col["name"] == "amount"
        for t in col.get("tags", [])
    ]
    c.expect(
        "Commerce.ChiffreAffaires" in tags_amount,
        "raw.orders.amount porte le terme Commerce.ChiffreAffaires",
    )


def check_08(c: Check) -> None:
    """Classification automatique et échantillons."""
    customers = api(f"/tables/name/{fqn('raw', 'customers')}?fields=columns,tags")
    pii = {
        col["name"]
        for col in customers["columns"]
        for t in col.get("tags", [])
        if t["tagFQN"].startswith("PII.")
    }
    c.expect("email" in pii, "raw.customers.email est étiquetée PII")

    table_id = customers["id"]
    echantillon = get(f"/tables/{table_id}/sampleData")
    lignes = ((echantillon or {}).get("sampleData") or {}).get("rows") or []
    c.expect(len(lignes) > 0, f"un échantillon est stocké ({len(lignes)} lignes)")


def check_09(c: Check) -> None:
    """Équipes, rôles et politiques."""
    c.expect(get("/teams/name/data_platform") is not None, "l'équipe data_platform existe")
    c.expect(get("/users/name/cmartin") is not None, "l'utilisateur cmartin existe")

    politique = get("/policies/name/omlab_donnees_rh")
    c.expect(politique is not None, "la politique omlab_donnees_rh existe")
    if politique:
        effets = {r["effect"] for r in politique["rules"]}
        c.expect({"deny", "allow"} <= effets, "la politique combine une règle deny et une allow")

    c.expect(get("/roles/name/omlab_data_steward") is not None, "le rôle omlab_data_steward existe")


def check_10(c: Check) -> None:
    """Qualité de données."""
    cas = api("/dataQuality/testCases?limit=100&fields=testCaseResult")["data"]
    noms = {t["name"] for t in cas}
    c.expect(len(cas) >= 12, f"au moins 12 tests sont enregistrés ({len(cas)})")

    resultats = {
        t["name"]: (t.get("testCaseResult") or {}).get("testCaseStatus")
        for t in cas
    }

    # Les échecs attendus : ils prouvent que les tests voient vraiment les données.
    for nom in ["orders_aucun_montant_negatif", "customers_pays_renseigne", "products_sku_unique"]:
        c.expect(
            resultats.get(nom) == "Failed",
            f"{nom} échoue (c'est le comportement attendu)",
        )

    for nom in ["orders_volume_attendu", "products_categorie_connue"]:
        c.expect(resultats.get(nom) == "Success", f"{nom} passe")


def check_11(c: Check) -> None:
    """Lineage manuel."""
    graphe = api(
        f"/lineage/table/name/{urllib.parse.quote(fqn('analytics', 'fct_orders'))}"
        "?upstreamDepth=1&downstreamDepth=0"
    )
    sources = {
        (e.get("lineageDetails") or {}).get("source")
        for e in graphe.get("upstreamEdges", [])
    }
    c.expect("Manual" in sources, f"au moins une arête est manuelle (sources : {sources})")


def check_12(c: Check) -> None:
    """Alertes."""
    abonnements = api("/events/subscriptions?limit=50")["data"]
    noms = {a["name"] for a in abonnements}
    c.expect(
        {"omlab_tests_en_echec", "omlab_tables_modifiees"} <= noms,
        "les deux alertes du TP existent",
    )


def check_14(c: Check) -> None:
    """Écritures du SDK."""
    orders = api(f"/tables/name/{fqn('raw', 'orders')}?fields=owners,tags")
    c.expect(bool(orders.get("description")), "raw.orders est documentée")
    c.expect(bool(orders.get("owners")), "raw.orders a un propriétaire")

    tiers = [t["tagFQN"] for t in orders.get("tags", []) if t["tagFQN"].startswith("Tier.")]
    c.expect(bool(tiers), f"raw.orders porte un niveau de criticité ({tiers})")


def check_15(c: Check) -> None:
    """Connecteur maison."""
    service = get("/services/databaseServices/name/omlab_fichiers")
    c.expect(service is not None, "le service omlab_fichiers existe")

    tables = get("/tables?limit=50&database=omlab_fichiers.exports")
    noms = {t["name"] for t in (tables or {}).get("data", [])}
    c.expect(
        {"objectifs_2026", "remises", "campagnes"} <= noms,
        f"les 3 CSV sont catalogués ({sorted(noms)})",
    )


def check_16(c: Check) -> None:
    """Contrat de données."""
    contrats = api("/dataContracts?limit=10")["data"]
    c.expect(
        any(x["name"] == "contrat_revenue_monthly" for x in contrats),
        "le contrat contrat_revenue_monthly existe",
    )


CHECKS = {
    "04": ("Ingestion des métadonnées", check_04),
    "05": ("Profiling", check_05),
    "06": ("Usage et lineage automatique", check_06),
    "07": ("Glossaire", check_07),
    "08": ("Classification et PII", check_08),
    "09": ("Équipes, rôles, politiques", check_09),
    "10": ("Qualité de données", check_10),
    "11": ("Lineage manuel", check_11),
    "12": ("Alertes", check_12),
    "14": ("SDK Python", check_14),
    "15": ("Connecteur maison", check_15),
    "16": ("Contrat de données", check_16),
}


def main() -> int:
    demandes = sys.argv[1:] or sorted(CHECKS)
    code = 0
    for numero in demandes:
        if numero not in CHECKS:
            print(f"Aucune vérification pour le chapitre {numero}")
            continue
        titre, fonction = CHECKS[numero]
        c = Check(f"Chapitre {numero} — {titre}")
        print(f"\n\033[1mChapitre {numero} — {titre}\033[0m")
        try:
            fonction(c)
        except Exception as exc:  # un TP non fait ne doit pas tout arrêter
            c.expect(False, f"vérification interrompue : {exc}")
        code |= c.report()
    return code


if __name__ == "__main__":
    sys.exit(main())
