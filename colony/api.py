"""HTTP surface: POST /ask, so a treasury system can call this instead of a human.

Deliberately dependency-free (stdlib only). The server owns no state except an
append-only ledger, so a restart loses nothing that matters.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .intents import Inputs
from .memo import bundle
from .policy import Budget
from .queen import run


def make_handler(client, ledger_path: Path) -> type[BaseHTTPRequestHandler]:
    from .ledger import Ledger

    class Handler(BaseHTTPRequestHandler):
        server_version = "colony/3.0"

        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - stdlib naming
            if urlparse(self.path).path == "/health":
                self._send(200, {"ok": True, "service": "colony"})
                return
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 - stdlib naming
            if urlparse(self.path).path != "/ask":
                self._send(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._send(400, {"error": "body must be JSON"})
                return

            company = body.get("company")
            if not company:
                self._send(400, {"error": "company is required"})
                return
            budget_usd = float(body.get("budget_usd", 0.25))
            if budget_usd > 1.0:
                self._send(400, {"error": "budget_usd may not exceed 1.00 in this release"})
                return

            inputs = Inputs(
                company=company,
                jurisdiction=body.get("jurisdiction", "Denmark"),
                domain=body.get("domain"),
                country=body.get("country"),
                year=int(body.get("year", 2025)),
            )
            answer = run(
                client,
                body.get("question", f"Is {company} safe for 60-day terms?"),
                inputs,
                Budget(total_usd=budget_usd, max_per_ask=0.05),
                ledger=Ledger(path=ledger_path),
                escalate=bool(body.get("escalate", True)),
            )
            self._send(200, bundle(answer))

    return Handler


def _main() -> int:  # pragma: no cover - exercised by hand
    import argparse

    from .client import TelegraphClient
    from .wallet import load_wallet

    ap = argparse.ArgumentParser(prog="colony.api")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8088)
    ap.add_argument("--ledger", default="runs/api-ledger.jsonl")
    ap.add_argument("--node", default="https://devnode.telegraphprotocol.com")
    args = ap.parse_args()

    wallet = load_wallet()
    client = TelegraphClient(wallet.key, node=args.node, max_usd_per_ask=0.05, max_usd_per_run=1.0)
    serve(client, args.host, args.port, Path(args.ledger))
    return 0


def serve(client, host: str = "127.0.0.1", port: int = 8088, ledger_path: Path | None = None) -> None:
    handler = make_handler(client, ledger_path or Path("runs/api-ledger.jsonl"))
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"colony api on http://{host}:{port}  (POST /ask, GET /health)")
    httpd.serve_forever()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
