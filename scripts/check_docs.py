#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.12.*"
# dependencies = ["playwright==1.58.0"]
# ///
"""Vérifie la documentation : README.md et cours/*.md.

    ./omlab check-docs

Quatre contrôles, qui n'ont pas besoin du laboratoire :

  * aucun schéma en dessin ASCII : ils s'écrivent en Mermaid ;
  * tous les liens relatifs et toutes les images pointent vers un fichier réel ;
  * aucune capture de cours/img n'est orpheline : chacune sert à un chapitre ;
  * chaque bloc Mermaid passe l'analyseur officiel, dans un vrai navigateur :
    un bloc invalide s'affiche en erreur sur GitHub, sans autre avertissement.

Mermaid étant chargé depuis un CDN, ce dernier contrôle demande un accès réseau.
"""

import re
import sys
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"

DESSIN = re.compile(r"[┌┐└┘│├┤┬┴┼▶▼►]|──")
LIEN = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)[^)]*\)")
BLOC = re.compile(r"^```mermaid\n(.*?)^```", re.S | re.M)


def verifier_fichier(chemin: Path) -> list[str]:
    erreurs = []
    texte = chemin.read_text()
    for numero, ligne in enumerate(texte.splitlines(), 1):
        if DESSIN.search(ligne):
            erreurs.append(f"{chemin.name}:{numero} dessin ASCII : {ligne.strip()[:50]}")
    for cible in LIEN.findall(texte):
        if cible.startswith(("http://", "https://", "#", "mailto:")):
            continue
        fichier = unquote(cible.split("#")[0])
        if fichier and not (chemin.parent / fichier).exists():
            erreurs.append(f"{chemin.name} lien mort : {cible}")
    return erreurs


def verifier_captures(fichiers: list[Path]) -> list[str]:
    textes = "".join(f.read_text() for f in fichiers)
    return [f"capture orpheline : {c.name}" for c in sorted((ROOT / "cours" / "img").glob("*.png")) if c.name not in textes]


def verifier_mermaid(fichiers: list[Path]) -> tuple[int, list[str]]:
    blocs = [(f.name, b) for f in fichiers for b in BLOC.findall(f.read_text())]
    erreurs = []
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        page = navigateur.new_page()
        page.goto("about:blank")
        page.add_script_tag(url=MERMAID)
        for nom, bloc in blocs:
            message = page.evaluate(
                "async (t) => { try { await mermaid.parse(t); return null }"
                " catch (e) { return String(e.message || e) } }",
                bloc,
            )
            if message:
                erreurs.append(f"{nom} Mermaid invalide : {message.splitlines()[0]}")
        navigateur.close()
    return len(blocs), erreurs


def main() -> int:
    fichiers = [ROOT / "README.md", *sorted((ROOT / "cours").glob("*.md"))]
    erreurs = [e for f in fichiers for e in verifier_fichier(f)]
    erreurs += verifier_captures(fichiers)
    nombre, erreurs_mermaid = verifier_mermaid(fichiers)
    erreurs += erreurs_mermaid
    for erreur in erreurs:
        print(f"  ÉCHEC {erreur}")
    print(f"{len(fichiers)} fichiers, {nombre} blocs Mermaid, {len(erreurs)} erreur(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
