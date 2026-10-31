#!/usr/bin/env python3
"""Vérifie que les TP d'un chapitre ont bien produit ce qu'ils devaient.

    ./omlab check          toutes les vérifications
    ./omlab check 04       seulement le chapitre 04

Ces contrôles interrogent l'API : ils constatent l'état réel du catalogue,
pas ce que les logs ont bien voulu afficher. Un chapitre non encore fait
apparaît en échec — c'est normal, c'est votre liste de courses.
"""

import base64
import sys
import urllib.parse

sys.path.insert(0, "/omlab")

from lib.om import Check, api, fqn, jeton_admin

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


def check_17(c: Check) -> None:
    """Le tour de la 2.x."""
    c.expect(get("/domains/name/Ventes") is not None, "le domaine Ventes existe")

    produit = get("/dataProducts/name/ca_mensuel/assets")
    assets = (produit or {}).get("data") or []
    c.expect(len(assets) == 2, f"le produit ca_mensuel contient les 2 tables ({len(assets)})")

    c.expect(get("/metrics/name/ca_mensuel_net") is not None, "la métrique ca_mensuel_net existe")
    c.expect(get("/announcements/name/refonte_orders") is not None, "l'annonce refonte_orders existe")

    taches = api("/tasks?limit=100")["data"]
    incidents = [t for t in taches if t["category"] == "Incident"]
    c.expect(len(incidents) >= 5, f"les incidents sont des tâches ({len(incidents)})")
    c.expect(
        any(t["name"] == "documenter_orders_amount" for t in taches),
        "la tâche documenter_orders_amount existe",
    )

    c.expect(get("/contextCenter/pages/name/lire_les_avoirs") is not None, "l'article lire_les_avoirs existe")
    c.expect(get("/apps/name/McpApplication") is not None, "le serveur MCP est installé")


def check_18(c: Check) -> None:
    """Collaborer sur une fiche."""
    admin = jeton_admin()
    proprietes = api("/metadata/types/name/table?fields=customProperties")["customProperties"]
    c.expect(any(p["name"] == "frequenceMaj" for p in proprietes), "la propriété frequenceMaj est déclarée sur le type table")

    orders = api(f"/tables/name/{fqn('raw', 'orders')}?fields=extension,tags")
    c.expect((orders.get("extension") or {}).get("frequenceMaj") == "quotidienne", "raw.orders porte la valeur de sa propriété")
    c.expect(any(t["tagFQN"] == "Tier.Tier1" for t in orders["tags"]), "raw.orders est en Tier1")

    taches = {t["name"]: t for t in api("/tasks?limit=200", token=admin)["data"]}
    demande = taches.get("decrire_customers_country", {})
    c.expect(demande.get("status") == "Approved", "la demande de description a été approuvée")
    colonnes = api(f"/tables/name/{fqn('raw', 'customers')}")["columns"]
    pays = next(x for x in colonnes if x["name"] == "country")
    c.expect("ISO" in (pays.get("description") or ""), "la réponse a écrit la description de la colonne")
    c.expect(get(f"/tables/name/{fqn('raw', 'table_ephemere')}?include=all") is None, "la table éphémère a bien été effacée")


def check_19(c: Check) -> None:
    """Import et export en masse."""
    panier = get("/glossaryTerms/name/Commerce.Panier")
    c.expect(panier is not None, "le terme Panier vient de l'import CSV")
    c.expect("Cart" in ((panier or {}).get("synonyms") or []), "ses synonymes ont été importés")
    colonnes = api(f"/tables/name/{fqn('raw', 'products')}")["columns"]
    nom = next(x for x in colonnes if x["name"] == "name")
    c.expect("Nom commercial" in (nom.get("description") or ""), "la description de raw.products.name vient de l'import CSV")


def check_20(c: Check) -> None:
    """La qualité avancée."""
    orders, customers = fqn("raw", "orders"), fqn("raw", "customers")
    externe = get(f"/dataQuality/testCases/name/{orders}.rapprochement_compta?fields=testCaseResult") or {}
    c.expect((externe.get("testCaseResult") or {}).get("testCaseStatus") == "Success", "le test externe a son verdict")

    periode = "startTs=0&endTs=99999999999999"
    table = api(f"/tables/{orders}/tableProfile?{periode}")["data"]
    metriques = {m["name"]: m["value"] for m in (table[0].get("customMetrics") or [])} if table else {}
    c.expect("commandes_annulees" in metriques, f"la métrique de table a une valeur ({metriques.get('commandes_annulees')})")
    colonne = api(f"/tables/{orders}.amount/columnProfile?{periode}")["data"]
    metriques = {m["name"]: m["value"] for m in (colonne[0].get("customMetrics") or [])} if colonne else {}
    c.expect("montant_des_avoirs" in metriques, f"la métrique de colonne a une valeur ({metriques.get('montant_des_avoirs')})")

    cas = f"{customers}.country.customers_pays_par_activite"
    segments = get(f"/dataQuality/testCases/dimensionResults/{cas}?dimensionName=is_active&{periode}") or {}
    valeurs = {s["dimensionValues"][0]["value"] for s in segments.get("data") or []}
    c.expect(len(valeurs) == 2, f"le test par segment connaît {len(valeurs)} valeurs de is_active")
    c.expect(get(f"/dataQuality/testCases/name/{customers}.table_row_count_between") is not None,
             "TestRunner a enregistré ses tests dans le catalogue")

    cas = f"{customers}.country.customers_pays_renseigne"
    etapes = api(f"/dataQuality/testCases/testCaseIncidentStatus?testCaseFQN={cas}&{periode}&latest=false&limit=50")["data"]
    c.expect(any(e["testCaseResolutionStatusType"] == "Resolved" for e in etapes), "un incident est allé jusqu'à Resolved")


def check_21(c: Check) -> None:
    """La gouvernance avancée."""
    admin = jeton_admin()
    terme = get("/glossaryTerms/name/Finance.MargeBrute") or {}
    c.expect(terme.get("entityStatus") == "Approved", "le terme MargeBrute a été approuvé par la relectrice")

    commande = api("/glossaryTerms/name/Commerce.Commande?fields=relatedTerms")
    c.expect(any(r["term"]["name"] == "Avoir" for r in commande["relatedTerms"]), "Commande est reliée à Avoir")
    c.expect(get("/glossaryTerms/name/Logistique.Transport.Livraison") is not None, "l'import SKOS a créé la hiérarchie Transport > Livraison")
    c.expect(get("/domains/name/Ventes.VentesEurope") is not None, "le sous-domaine VentesEurope existe")

    formulaires = api("/governance/intakeForms?limit=10", token=admin)["data"]
    c.expect(not formulaires, "aucun formulaire de démonstration ne reste actif")

    session = api("/users/login", method="POST", token="sans-objet", body={
        "email": "relectrice@omlab.example",
        "password": base64.b64encode(b"Relecture-2026!tuto").decode(),
    })["accessToken"]
    table = api(f"/tables/name/{fqn('raw', 'customers')}")
    colonnes = api(f"/tables/{table['id']}/sampleData", token=session)["sampleData"]["columns"]
    c.expect(any("[MASKED]" in x for x in colonnes), "les données sensibles sont masquées pour la relectrice")


def check_22(c: Check) -> None:
    """L'administration."""
    admin = jeton_admin()
    crm = get("/teams/name/Crm?fields=parents") or {}
    c.expect([p["name"] for p in crm.get("parents") or []] == ["Marketing"], "la hiérarchie va jusqu'à l'équipe Crm")
    persona = get("/personas/name/DataSteward?fields=users") or {}
    c.expect(bool(persona.get("users")), "le persona DataSteward a un utilisateur")
    c.expect(bool(api("/audit/logs?limit=1", token=admin)["data"]), "le journal d'audit contient des entrées")
    c.expect(get("/kpi/name/description_80_pourcent") is not None, "le KPI description_80_pourcent existe")
    alertes = {a["name"] for a in api("/events/subscriptions?limit=100", token=admin)["data"]}
    c.expect(not alertes & {"omlab_slack", "omlab_teams", "omlab_gchat", "omlab_aval"}, "les alertes de démonstration ont été retirées")


def check_23(c: Check) -> None:
    """Au-delà de Postgres."""
    topic = get("/topics/name/" + urllib.parse.quote('omlab_kafka."commandes.creees"')) or {}
    c.expect((topic.get("messageSchema") or {}).get("schemaType") == "Avro", "le topic commandes.creees a son schéma Avro")
    conteneur = get("/containers/name/omlab_s3.omlab-lac.stocks?fields=dataModel") or {}
    nb = len((conteneur.get("dataModel") or {}).get("columns") or [])
    c.expect(nb == 2, f"le conteneur stocks a {nb} colonnes")
    modele = get("/mlmodels/name/omlab_mlflow.prevision_ventes") or {}
    c.expect(any(h["name"] == "fenetre_mois" for h in modele.get("mlHyperParameters") or []), "le modèle prevision_ventes a son hyperparamètre")
    tableaux = api("/dashboards?service=omlab_metabase&limit=50")["data"] if get("/services/dashboardServices/name/omlab_metabase") else []
    c.expect(any(d.get("displayName") == "Ventes" for d in tableaux), "le tableau de bord Ventes est catalogué")
    dags = api("/pipelines?service=omlab_airflow&limit=1")["paging"]["total"] if get("/services/pipelineServices/name/omlab_airflow") else 0
    c.expect(dags > 0, "les DAG d'Airflow sont catalogués")
    index = api("/searchIndexes?service=omlab_elastic&limit=1")["paging"]["total"] if get("/services/searchServices/name/omlab_elastic") else 0
    c.expect(index > 0, "Elasticsearch a des index catalogués")
    routes = api("/apiEndpoints?service=omlab_api&limit=5")["data"] if get("/services/apiServices/name/omlab_api") else []
    c.expect(bool(routes), "la route de l'API est cataloguée")

    modele_dbt = fqn("analytics_dbt", "ventes_par_pays")
    table = get(f"/tables/name/{modele_dbt}?fields=dataModel") or {}
    amont = get(f"/lineage/table/name/{modele_dbt}?upstreamDepth=1&downstreamDepth=0") or {}
    noms = {n["name"] for n in amont.get("nodes") or []}
    c.expect("dbt" in (table.get("description") or "") and {"orders", "customers"} <= noms, "le modèle dbt a son lineage et sa description")
    test = get(f"/dataQuality/testCases/name/{modele_dbt}.nb_commandes.not_null_ventes_par_pays_nb_commandes?fields=testCaseResult") or {}
    c.expect((test.get("testCaseResult") or {}).get("testCaseStatus") == "Success", "le test dbt a un résultat")
    amont = api(f"/lineage/table/name/{fqn('analytics', 'fct_orders')}?upstreamDepth=1&downstreamDepth=0")
    c.expect("products" in {n["name"] for n in amont["nodes"]}, "OpenLineage a ajouté products en amont de fct_orders")


def check_24(c: Check) -> None:
    """Standards ouverts et agents."""
    admin = jeton_admin()
    contrats = api("/dataContracts?limit=50&fields=entity", token=admin)["data"]
    contrat = next((x for x in contrats if x["name"] == "contrat_products"), {})
    c.expect((contrat.get("entity") or {}).get("name") == "products", "le contrat ODCS est rattaché à raw.products")
    nb = len(contrat.get("schema") or [])
    c.expect(nb == 2, f"il promet {nb} colonnes")
    memoires = api("/contextCenter/memories?limit=20", token=admin)["data"]
    c.expect(any(m["name"] == "ca_hors_avoirs" for m in memoires), "la mémoire ca_hors_avoirs existe")


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
    "17": ("Le tour complet de la 2.x", check_17),
    "18": ("Collaborer sur une fiche", check_18),
    "19": ("Import et export en masse", check_19),
    "20": ("La qualité avancée", check_20),
    "21": ("La gouvernance avancée", check_21),
    "22": ("L'administration", check_22),
    "23": ("Au-delà de Postgres", check_23),
    "24": ("Standards ouverts et agents", check_24),
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
