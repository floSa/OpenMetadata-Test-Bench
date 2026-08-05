#!/usr/bin/env python3
"""Récupère un jeton JWT utilisable par les TP et l'écrit dans .env.

Deux jetons cohabitent dans OpenMetadata, et la confusion entre les deux
est la première cause de 401 :

  * le jeton de session d'un utilisateur humain, obtenu en se connectant
    avec e-mail + mot de passe. Durée de vie courte (1 h par défaut) ;
  * le jeton d'un *bot*, long (7 jours par défaut, ou illimité), pensé
    pour l'automatisation. C'est celui qu'utilisent les workflows.

Ce script se connecte en admin, puis va lire le jeton de l'`ingestion-bot`
et le range dans .env sous le nom OM_TOKEN. Aucune dépendance externe.

    ./omlab token
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

HOST = os.environ.get("OM_HOST", "http://localhost:8585")
ADMIN_USER = os.environ.get("OM_ADMIN_USER", "admin@open-metadata.org")
ADMIN_PASSWORD = os.environ.get("OM_ADMIN_PASSWORD", "admin")
BOT_NAME = os.environ.get("OM_BOT_NAME", "ingestion-bot")


def call(path: str, method: str = "GET", body: dict | None = None, token: str | None = None):
    url = f"{HOST}/api/v1{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        raise SystemExit(f"HTTP {exc.code} sur {method} {url}\n{detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"OpenMetadata est injoignable sur {HOST} ({exc.reason}).\n"
            "La stack est-elle démarrée ?  ./omlab status"
        ) from exc


def login() -> str:
    """Ouvre une session admin. Le mot de passe transite encodé en base64."""
    payload = {
        "email": ADMIN_USER,
        "password": base64.b64encode(ADMIN_PASSWORD.encode()).decode(),
    }
    return call("/users/login", method="POST", body=payload)["accessToken"]


def bot_token(admin_token: str) -> str:
    """Lit le JWT du bot d'ingestion."""
    bot = call(f"/bots/name/{BOT_NAME}", token=admin_token)
    bot_user_id = bot["botUser"]["id"]
    mechanism = call(f"/users/auth-mechanism/{bot_user_id}", token=admin_token)
    return mechanism["config"]["JWTToken"]


def write_env(token: str) -> None:
    """Met à jour OM_TOKEN dans .env sans écraser le reste du fichier."""
    lines: list[str] = []
    if ENV_FILE.exists():
        lines = [
            line for line in ENV_FILE.read_text().splitlines()
            if not re.match(r"^\s*OM_TOKEN\s*=", line)
        ]
    else:
        example = ROOT / ".env.example"
        if example.exists():
            lines = example.read_text().splitlines()
            lines = [line for line in lines if not re.match(r"^\s*OM_TOKEN\s*=", line)]
    lines.append(f"OM_TOKEN={token}")
    ENV_FILE.write_text("\n".join(lines) + "\n")


def main() -> int:
    admin_token = login()
    token = bot_token(admin_token)
    write_env(token)

    print(f"Jeton de {BOT_NAME} récupéré et écrit dans .env")
    print(f"  OM_TOKEN={token[:24]}…{token[-8:]}  ({len(token)} caractères)")
    print("\nÀ utiliser tel quel :")
    print(f'  curl -H "Authorization: Bearer $OM_TOKEN" {HOST}/api/v1/users/me')
    return 0


if __name__ == "__main__":
    sys.exit(main())
