"""Boîte à outils partagée par tous les scripts des TP.

Deux façons de parler à OpenMetadata coexistent dans ce tutoriel, et c'est
volontaire — les chapitres 13 et 14 expliquent quand choisir l'une ou l'autre :

  * ``client()``  → le SDK Python officiel : objets typés, validation Pydantic,
    idéal pour écrire du code robuste.
  * ``api()``     → un client HTTP minimal : utile pour voir *exactement* ce qui
    circule sur le réseau, et pour les endpoints que le SDK n'expose pas.

Usage typique dans un TP :

    import sys; sys.path.insert(0, "/omlab")
    from lib.om import client, api, SERVICE

    om = client()
    table = om.get_by_name(entity=Table, fqn=f"{SERVICE}.omlab.raw.customers")
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
def _load_env() -> None:
    """Charge .env sans dépendance externe (python-dotenv n'est pas garanti)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()


def _in_container() -> bool:
    """Sommes-nous dans le conteneur d'ingestion, ou sur la machine hôte ?"""
    return Path("/omlab").exists() and Path("/opt/airflow").exists()


#: URL du serveur, résolue selon l'endroit d'où l'on tourne.
HOST: str = (
    os.environ.get("OM_HOST_INTERNAL", "http://openmetadata-server:8585")
    if _in_container()
    else os.environ.get("OM_HOST", "http://localhost:8585")
)

TOKEN: str = os.environ.get("OM_TOKEN", "")

#: Nom du service de base de données créé par les TP.
SERVICE: str = os.environ.get("OMLAB_SERVICE_NAME", "omlab_postgres")

#: Nom pleinement qualifié (FQN) de la base dans OpenMetadata.
DB_FQN: str = f"{SERVICE}.omlab"


def fqn(schema: str, table: str | None = None) -> str:
    """Construit un FQN OpenMetadata : service.base.schéma[.table]."""
    return f"{DB_FQN}.{schema}" + (f".{table}" if table else "")


def _require_token() -> str:
    if not TOKEN:
        raise SystemExit(
            "OM_TOKEN est vide.\n"
            "Lancez d'abord :  ./omlab token"
        )
    return TOKEN


# ---------------------------------------------------------------------
# SDK officiel
# ---------------------------------------------------------------------
def client():
    """Renvoie un client ``OpenMetadata`` prêt à l'emploi (SDK officiel)."""
    from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
        AuthProvider,
        OpenMetadataConnection,
    )
    from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
        OpenMetadataJWTClientConfig,
    )
    from metadata.ingestion.ometa.ometa_api import OpenMetadata

    config = OpenMetadataConnection(
        # Attention : le SDK attend l'URL de l'API, donc suffixée par /api
        hostPort=f"{HOST}/api",
        authProvider=AuthProvider.openmetadata,
        securityConfig=OpenMetadataJWTClientConfig(jwtToken=_require_token()),
    )
    om = OpenMetadata(config)
    if not om.health_check():
        raise SystemExit(f"Le serveur {HOST} ne répond pas correctement.")
    return om


# ---------------------------------------------------------------------
# Client HTTP brut
# ---------------------------------------------------------------------
def api(
    path: str,
    method: str = "GET",
    body: Any = None,
    content_type: str = "application/json",
    token: str | None = None,
) -> Any:
    """Appelle l'API REST directement. ``path`` est relatif à /api/v1.

        api("/tables?limit=5")
        api(f"/tables/{id}", method="PATCH",
            body=[{"op": "add", "path": "/description", "value": "..."}],
            content_type="application/json-patch+json")
    """
    url = f"{HOST}/api/v1/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", content_type)
    req.add_header("Authorization", f"Bearer {token or _require_token()}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:600]
        raise SystemExit(f"HTTP {exc.code} sur {method} {url}\n{detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"{HOST} injoignable ({exc.reason}). La stack tourne-t-elle ?") from exc


def texte(path: str, method: str = "GET", corps: str | None = None, token: str | None = None) -> str:
    """Comme ``api()``, pour les routes d'import et d'export : le corps est du CSV, pas du JSON."""
    url = f"{HOST}/api/v1/{path.lstrip('/')}"
    req = urllib.request.Request(url, data=corps.encode() if corps is not None else None, method=method)
    # Sur ces routes, un GET déclaré en text/plain reçoit un 415.
    req.add_header("Content-Type", "text/plain" if corps is not None else "application/json")
    req.add_header("Authorization", f"Bearer {token or _require_token()}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:600]
        raise SystemExit(f"HTTP {exc.code} sur {method} {url}\n{detail}") from exc


def jeton_admin() -> str:
    """Ouvre une session admin, pour les rares écritures interdites à l'ingestion-bot."""
    utilisateur = os.environ.get("OM_ADMIN_USER", "admin@open-metadata.org")
    mot_de_passe = os.environ.get("OM_ADMIN_PASSWORD", "admin")
    corps = {"email": utilisateur, "password": base64.b64encode(mot_de_passe.encode()).decode()}
    return api("/users/login", method="POST", body=corps, token="sans-objet")["accessToken"]


# ---------------------------------------------------------------------
# Aides à l'affichage, pour que les TP restent lisibles
# ---------------------------------------------------------------------
def show(obj: Any, title: str | None = None) -> None:
    """Affiche un objet (dict, liste ou entité Pydantic) en JSON lisible."""
    if title:
        print(f"\n--- {title} ---")
    if hasattr(obj, "model_dump_json"):
        print(json.dumps(json.loads(obj.model_dump_json(exclude_none=True)), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


class Check:
    """Petit collecteur d'assertions, utilisé par les scripts check_NN.py.

        c = Check("Chapitre 04 — ingestion de métadonnées")
        c.expect(len(tables) >= 7, f"7 tables attendues, {len(tables)} trouvées")
        sys.exit(c.report())
    """

    def __init__(self, title: str) -> None:
        self.title = title
        self.failures: list[str] = []
        self.passed = 0

    def expect(self, condition: bool, message: str) -> bool:
        if condition:
            self.passed += 1
            print(f"  \033[32mOK\033[0m   {message}")
        else:
            self.failures.append(message)
            print(f"  \033[31mKO\033[0m   {message}")
        return condition

    def report(self) -> int:
        total = self.passed + len(self.failures)
        if self.failures:
            print(f"\n\033[31m{self.title} : {self.passed}/{total} — échec\033[0m")
            for failure in self.failures:
                print(f"  - {failure}")
            return 1
        print(f"\n\033[32m{self.title} : {total}/{total} — tout est bon\033[0m")
        return 0
