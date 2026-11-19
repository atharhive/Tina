"""Telegraph HTTP client with escrow payment, spend caps and receipts.

Paid calls go through the node's `escrow` scheme: the node answers 402 with a
message template, Tina signs that message with EIP-191 (personal_sign) and
resends the same body with an `X-PAYMENT` envelope. Escrow is billed only when
the answer is delivered, so a failed ask costs nothing.

Nothing here trusts the network: every paid call returns its receipt header,
the price charged and the raw response, and the caller keeps all three.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct

USER_AGENT = "tina/2.0 (+https://github.com/atharhive/Tina)"
DEFAULT_NODE = "https://devnode.telegraphprotocol.com"
SPEND_LOG = Path(os.environ.get("TINA_HOME", Path.home() / ".tina")) / "spend.json"


class TelegraphError(RuntimeError):
    """Base error for anything the network or the payment path reports."""


class PaymentRefused(TelegraphError):
    """The node refused payment (fund the escrow, or the rail is down)."""


class MinerFailed(TelegraphError):
    """The ask was paid for or attempted but no answer came back."""


@dataclass
class AskResult:
    intent: str
    params: dict[str, Any]
    miner_id: str | None
    miner_name: str | None
    status: int
    result: Any
    receipt: dict[str, Any] | None
    price_usd: float
    rail: str | None
    elapsed_ms: int
    request_id: str = ""
    error: str | None = None
    signal_hash: str | None = None
    delivery: str | None = None
    field_status: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "params": self.params,
            "miner_id": self.miner_id,
            "miner_name": self.miner_name,
            "status": self.status,
            "result": self.result,
            "receipt": self.receipt,
            "signal_hash": self.signal_hash,
            "delivery": self.delivery,
            "field_status": self.field_status,
            "price_usd": self.price_usd,
            "rail": self.rail,
            "elapsed_ms": self.elapsed_ms,
            "request_id": self.request_id,
            "error": self.error,
        }


@dataclass
class SpendLog:
    """Per-UTC-day spend tracker; the benchmark every reviewer can check."""

    path: Path = field(default_factory=lambda: SPEND_LOG)
    _state: dict[str, float] | None = None

    def _load(self) -> dict[str, float]:
        if self._state is not None:
            return self._state
        try:
            loaded = json.loads(self.path.read_text())
            self._state = {str(k): float(v) for k, v in loaded.items()} if isinstance(loaded, dict) else {}
        except Exception:  # noqa: BLE001 - a missing or broken log starts empty
            self._state = {}
        return self._state

    def today(self) -> float:
        key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return float(self._load().get(key, 0.0))

    def history(self) -> dict[str, float]:
        """Every day the log has seen, oldest first."""
        return dict(sorted(self._load().items()))

    def add(self, usd: float) -> None:
        state = self._load()
        key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state[key] = round(float(state.get(key, 0.0)) + usd, 6)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2, sort_keys=True))
        try:
            self.path.chmod(0o600)
        except OSError:
            pass


class TelegraphClient:
    def __init__(
        self,
        wallet_key: str,
        node: str = DEFAULT_NODE,
        max_usd_per_ask: float = 0.05,
        max_usd_per_run: float = 0.20,
        max_usd_per_day: float = 1.00,
        timeout: int = 120,
        dry_run: bool = False,
    ) -> None:
        self.node = node.rstrip("/")
        self.account = Account.from_key(wallet_key)
        self.max_usd_per_ask = max_usd_per_ask
        self.max_usd_per_run = max_usd_per_run
        self.max_usd_per_day = max_usd_per_day
        self.timeout = timeout
        self.dry_run = dry_run
        self.spend = SpendLog()
        self.run_spent = 0.0
        self.spent_today = self.spend.today()

    # ---------------------------------------------------------------- transport
    def _post(self, path: str, payload: dict[str, Any], headers: dict[str, str] | None = None):
        h = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": USER_AGENT}
        if headers:
            h.update(headers)
        req = urllib.request.Request(
            f"{self.node}{path}",
            data=json.dumps(payload).encode(),
            headers=h,
            method="POST",
        )
        started = time.time()
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
            return resp.status, dict(resp.headers), resp.read(), int((time.time() - started) * 1000)
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read(), int((time.time() - started) * 1000)
        except urllib.error.URLError as exc:
            raise TelegraphError(f"network error calling {path}: {exc.reason}") from exc

    def _get(self, path: str) -> Any:
        req = urllib.request.Request(f"{self.node}{path}", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read())

    # ------------------------------------------------------------------ metadata
    def intents(self) -> list[dict[str, Any]]:
        return self._get("/engine/v1/intents").get("intents", [])

    def intent_meta(self, intent: str) -> dict[str, Any]:
        return self._get(f"/engine/v1/intents/{intent}")

    def signal(self, signal_hash: str) -> dict[str, Any]:
        """A delivery record by hash: who was paid, for which intent, and when.

        This is the node's own copy of an answer Tina paid for, so a reviewer can
        check a memo claim without trusting the memo.
        """
        if not signal_hash.startswith("0x"):
            signal_hash = "0x" + signal_hash
        return self._get(f"/engine/v1/signal/{signal_hash}")

    def miners_for(self, intent: str, limit: int = 5) -> list[dict[str, Any]]:
        """Best-ranked live miners for an intent, with id, slug, price and rank."""
        rows = self._get(f"/api/miners?intent={intent}&limit=200")
        out = []
        for m in rows:
            score = next((s for s in (m.get("scores") or []) if s.get("intent_id") == intent), None)
            if m.get("activation_status") not in ("active", None):
                continue
            out.append(
                {
                    "id": str(m.get("id")),
                    "slug": m.get("slug"),
                    "name": m.get("name"),
                    "rank": (score or {}).get("rank"),
                    "price_usd": (m.get("min_price_usdc") or 0) / 1e6,
                    "requests_served": m.get("total_requests_served") or 0,
                }
            )
        out.sort(key=lambda m: (m["rank"] if m["rank"] is not None else 10**6, -(m["requests_served"] or 0)))
        return out[:limit]

    # ------------------------------------------------------------------- payment
    def quote(self, intent: str, params: dict[str, Any], miner_id: str | None = None) -> dict[str, Any]:
        """Fetch the 402 challenge without paying. Returns prices per rail."""
        path = f"/engine/v1/ask/{miner_id}" if miner_id else "/engine/v1/ask"
        status, _headers, body, _ms = self._post(path, {"intent": intent, "params": params})
        if status != 402:
            raise TelegraphError(f"expected a payment challenge, got HTTP {status}: {body[:200]!r}")
        challenge = json.loads(body)
        accepts = challenge.get("accepts", [])
        escrow = next((a for a in accepts if a.get("scheme") == "escrow"), None)
        return {
            "intent": intent,
            "params": params,
            "miner_id": miner_id,
            "escrow_price_usd": _usd(escrow.get("price")) if escrow else None,
            "escrow_available": escrow is not None,
            "other_rails": [a.get("scheme") for a in accepts if a.get("scheme") != "escrow"],
            "challenge": challenge if dry_run_ok() else None,
        }

    def _escrow_header(self, accept: dict[str, Any], price_usd: float) -> str:
        now = int(time.time())
        auth = {
            "from": self.account.address,
            "to": accept["payTo"],
            "value": str(int(round(price_usd * 1_000_000))),
            "validAfter": str(now - 10),
            "validBefore": str(now + 55),  # the node accepts at most a 2 minute window
            "nonce": "0x" + secrets.token_hex(32),
        }
        template = (accept.get("extra") or {}).get("message")
        if not template:
            raise PaymentRefused("the escrow challenge carried no message to sign")
        message = (
            template.replace("{from}", auth["from"].lower())
            .replace("{nonce}", auth["nonce"])
            .replace("{validAfter}", auth["validAfter"])
            .replace("{validBefore}", auth["validBefore"])
        )
        signature = self.account.sign_message(encode_defunct(text=message)).signature
        sig_hex = signature.hex() if isinstance(signature, (bytes, bytearray)) else str(signature)
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex
        envelope = {
            "x402Version": 2,
            "scheme": "escrow",
            "network": accept["network"],
            "payload": {"signature": sig_hex, "authorization": auth},
        }
        return base64.b64encode(json.dumps(envelope).encode()).decode()

    def _reserve(self, price: float) -> None:
        if price > self.max_usd_per_ask:
            raise PaymentRefused(
                f"ask costs ${price:.2f}, over the ${self.max_usd_per_ask:.2f} per-ask cap. Nothing was paid."
            )
        if self.run_spent + price > self.max_usd_per_run:
            raise PaymentRefused(
                f"this run has spent ${self.run_spent:.2f}; another ${price:.2f} passes the "
                f"${self.max_usd_per_run:.2f} per-run cap. Nothing was paid."
            )
        if self.spent_today + price > self.max_usd_per_day:
            raise PaymentRefused(
                f"today's asks cost ${self.spent_today:.2f}; another ${price:.2f} passes the "
                f"${self.max_usd_per_day:.2f} daily cap. Nothing was paid."
            )

    # ----------------------------------------------------------------------- ask
    def ask(
        self,
        intent: str,
        params: dict[str, Any],
        miner_id: str | None = None,
        check_caps: bool = True,
    ) -> AskResult:
        payload = {"intent": intent, "params": params}
        path = f"/engine/v1/ask/{miner_id}" if miner_id else "/engine/v1/ask"

        status, headers, body, ms = self._post(path, payload)
        if status == 200:
            data = json.loads(body)
            return AskResult(
                intent=intent,
                params=params,
                miner_id=str(data.get("miner_id") or miner_id or ""),
                miner_name=data.get("miner_name"),
                status=status,
                result=data.get("result"),
                receipt=_receipt(headers),
                price_usd=float(data.get("cost_usd") or 0.0),
                rail=None,
                elapsed_ms=ms,
                signal_hash=data.get("signal_hash"),
                delivery=data.get("delivery"),
                field_status=data.get("field_status"),
            )
        if status != 402:
            raise MinerFailed(f"HTTP {status} from {path}: {body[:300].decode(errors='replace')}")

        challenge = json.loads(body)
        accept = next((a for a in challenge.get("accepts", []) if a.get("scheme") == "escrow"), None)
        if not accept:
            raise PaymentRefused(
                "the node offered no escrow option for this ask (it may be x402-only right now, and the "
                "public x402 facilitator is failing; see bounties#214)"
            )
        price = _usd(accept.get("price"))
        if self.dry_run:
            raise PaymentRefused(f"dry run: this ask quotes ${price:.2f} and was not paid")
        if check_caps:
            self._reserve(price)

        headers2 = {"X-PAYMENT": self._escrow_header(accept, price)}
        status2, headers2_out, body2, ms2 = self._post(path, payload, headers2)
        receipt = _receipt(headers2_out)

        if status2 == 200:
            data = json.loads(body2)
            charged = float(data.get("cost_usd") or price)
            self.run_spent = round(self.run_spent + charged, 6)
            self.spent_today = round(self.spent_today + charged, 6)
            self.spend.add(charged)
            return AskResult(
                intent=intent,
                params=params,
                miner_id=str(data.get("miner_id") or miner_id or ""),
                miner_name=data.get("miner_name"),
                status=status2,
                result=data.get("result"),
                receipt=receipt,
                price_usd=charged,
                rail="escrow",
                elapsed_ms=ms + ms2,
                signal_hash=data.get("signal_hash"),
                delivery=data.get("delivery"),
                field_status=data.get("field_status"),
            )

        # Escrow bills only a delivered answer, so nothing was charged here.
        detail = _error_text(body2)
        if status2 == 402:
            raise PaymentRefused(f"escrow refused this ask: {detail}", )
        raise MinerFailed(f"HTTP {status2} after payment: {detail}")


def _usd(price: Any) -> float:
    """Challenge prices arrive as '$0.01' or as micro-USDC ('10000')."""
    if isinstance(price, (int, float)):
        return float(price) / 1e6 if price > 100 else float(price)
    text = str(price or "$0").strip().lstrip("$")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _receipt(headers: dict[str, str]) -> dict[str, Any] | None:
    for name, raw in headers.items():
        if name.lower() in ("x-payment-response", "payment-response") and raw:
            try:
                return json.loads(base64.b64decode(raw).decode())
            except Exception:  # noqa: BLE001 - keep the raw header rather than lose it
                return {"raw": raw}
    return None


def _get_ci(headers: dict[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def _error_text(body: bytes) -> str:
    text = body.decode(errors="replace")
    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return text[:300]
    return str(data.get("reason") or data.get("error") or text)[:300]


def dry_run_ok() -> bool:
    return os.environ.get("TINA_KEEP_CHALLENGE") == "1"
