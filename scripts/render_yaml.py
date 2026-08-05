#!/usr/bin/env python3
"""Remplace les ${VARIABLES} d'un YAML de workflow par les valeurs du .env.

Pourquoi ? Parce qu'un YAML d'ingestion contient un jeton et un mot de passe.
On veut pouvoir versionner les fichiers de TP sans y écrire de secret : ils
contiennent des placeholders, et ce script produit la version « rendue » dans
tmp/, ignorée par git.

    python3 scripts/render_yaml.py tp/04-ingestion/metadata.yaml
    -> écrit tmp/04-ingestion__metadata.yaml et affiche ce chemin

Appelé automatiquement par `./omlab ingest|profile|test|usage`.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / "tmp"

PLACEHOLDER = re.compile(r"\$\{([A-Z0-9_]+)\}")


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        raise SystemExit(
            "Aucun fichier .env.\n"
            "  cp .env.example .env  puis  ./omlab token"
        )
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ[key.strip()] = value.strip()


def render(source: Path) -> Path:
    load_env()
    text = source.read_text()

    missing: set[str] = set()

    def substitute(match: re.Match[str]) -> str:
        name = match.group(1)
        value = os.environ.get(name, "")
        if not value:
            missing.add(name)
        return value

    rendered = PLACEHOLDER.sub(substitute, text)

    if missing:
        raise SystemExit(
            "Variables absentes ou vides dans .env : " + ", ".join(sorted(missing))
            + "\nSi OM_TOKEN est en cause :  ./omlab token"
        )

    TMP.mkdir(exist_ok=True)
    relative = source.relative_to(ROOT) if source.is_absolute() else source
    target = TMP / str(relative).replace("/", "__").replace("tp__", "")
    target.write_text(rendered)
    return target.relative_to(ROOT)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: render_yaml.py <fichier.yaml>")
    path = Path(sys.argv[1])
    if not path.is_absolute():
        path = ROOT / path
    print(render(path))
