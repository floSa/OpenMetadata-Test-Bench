#!/usr/bin/env python3
"""Récepteur de webhooks pour le chapitre 12 (alertes & notifications).

Un serveur HTTP minimal, sans dépendance, qui :
  * accepte tout POST sur /hook et journalise l'événement reçu ;
  * expose la liste des événements reçus sur GET /events (JSON) ;
  * expose une page lisible sur GET / .

Vu depuis le serveur OpenMetadata : http://omlab-webhook:8000/hook
Vu depuis votre navigateur         : http://localhost:8000/
"""

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000
MAX_EVENTS = 200

EVENTS: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    # On coupe le log par défaut (une ligne par requête, trop bruyant)
    def log_message(self, fmt, *args):  # noqa: A002
        pass

    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"_raw": raw}

        event = {
            "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "path": self.path,
            "payload": payload,
        }
        EVENTS.append(event)
        del EVENTS[:-MAX_EVENTS]

        # Résumé sur stdout : visible avec `./omlab logs omlab-webhook`
        summary = payload.get("eventType") or payload.get("entityType") or "événement"
        print(f"[{event['received_at']}] {self.path} <- {summary}", flush=True)

        self._json(200, {"status": "ok", "stored": len(EVENTS)})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/events"):
            self._json(200, {"count": len(EVENTS), "events": list(reversed(EVENTS))})
            return
        if self.path.startswith("/reset"):
            EVENTS.clear()
            self._json(200, {"status": "vidé"})
            return

        body = (
            "<!doctype html><meta charset='utf-8'>"
            "<title>omlab — webhook</title>"
            "<style>body{font-family:system-ui;margin:2rem;max-width:60rem}"
            "pre{background:#f4f4f5;padding:1rem;overflow:auto;border-radius:6px}</style>"
            f"<h1>Récepteur de webhooks omlab</h1>"
            f"<p><b>{len(EVENTS)}</b> événement(s) reçu(s).</p>"
            "<p>Dans OpenMetadata, pointez l'alerte vers "
            "<code>http://omlab-webhook:8000/hook</code>.</p>"
            "<p><a href='/events'>/events</a> (JSON) — "
            "<a href='/reset'>/reset</a> (vider)</p>"
            "<pre>" + json.dumps(list(reversed(EVENTS))[:5], indent=2, ensure_ascii=False) + "</pre>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"Récepteur de webhooks à l'écoute sur le port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
