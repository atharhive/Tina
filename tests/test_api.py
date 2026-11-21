"""API tests: the HTTP surface, exercised over a real socket with a fake miner."""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from colony.api import make_handler  # noqa: E402

ANSWERS = {
    "SANCTIONS_SCREENING_MATCH_GENERAL": {"matched": False, "match_score": 0},
    "CORPORATE_REGISTRY_LOOKUP_GENERAL": {"legal_name": "ACME A/S", "registration_id": "1", "active": True},
}


class FakeClient:
    """Enough of TelegraphClient for the API path: listed miners and paid answers."""

    def miners_for(self, intent, limit=5):
        return [{"id": "1", "slug": "fake-miner", "name": "Fake", "rank": 1, "price_usd": 0.01, "requests_served": 1}]

    def ask(self, intent, params, miner_id=None, check_caps=True):
        from colony.client import AskResult

        fields = ANSWERS.get(intent, {})
        return AskResult(
            intent=intent, params=params, miner_id="1", miner_name="Fake", status=200,
            result=fields, receipt={"receipt_hash": "0xabc", "rail": "escrow"},
            price_usd=0.01, rail="escrow", elapsed_ms=5, signal_hash="0xdead",
        )


def start(tmp_path: Path):
    handler = make_handler(FakeClient(), tmp_path / "ledger.jsonl")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def call(base, path, body=None):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read())


def test_health(tmp_path):
    httpd, base = start(tmp_path)
    try:
        code, body = call(base, "/health")
        assert code == 200 and body["service"] == "colony"
    finally:
        httpd.shutdown()


def test_ask_returns_a_bundle_with_a_verdict_and_memo(tmp_path):
    httpd, base = start(tmp_path)
    try:
        code, body = call(base, "/ask", {"company": "Acme A/S", "budget_usd": 0.05})
        assert code == 200
        assert body["verdict"]["verdict"] in {"ALLOW", "ALLOW WITH CONDITIONS", "HOLD", "BLOCK"}
        assert body["memo"].startswith("# Acme A/S")
        assert body["bundle_sha256"]
    finally:
        httpd.shutdown()


def test_ask_requires_a_company(tmp_path):
    httpd, base = start(tmp_path)
    try:
        with urllib.request.urlopen(
            urllib.request.Request(base + "/ask", data=b"{}", headers={"Content-Type": "application/json"}, method="POST"),
            timeout=30,
        ):
            assert False, "should have raised"
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    finally:
        httpd.shutdown()


def test_budget_cap_is_enforced_at_the_edge(tmp_path):
    httpd, base = start(tmp_path)
    try:
        req = urllib.request.Request(base + "/ask", data=json.dumps({"company": "Acme", "budget_usd": 5}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=30)
            assert False, "should have been refused"
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
    finally:
        httpd.shutdown()


def test_unknown_route_is_404(tmp_path):
    httpd, base = start(tmp_path)
    try:
        try:
            call(base, "/nope", {})
            assert False
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        httpd.shutdown()
