"""Client tests against a fake transport: no network, no wallet funds, no spend."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from core.client import (  # noqa: E402
    PaymentRefused,
    SpendLog,
    TelegraphClient,
    _receipt,
    _usd,
)

# A public test key (Hardhat account #1). It holds nothing and signs nothing real.
TEST_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"

CHALLENGE = {
    "error": "payment required",
    "accepts": [
        {
            "scheme": "escrow",
            "price": "$0.01",
            "network": "eip155:11155111",
            "payTo": "0x72a70e949362670Bf8bceAd24eFC5b8f950aa08b",
            "extra": {"message": "Telegraph Escrow Payment\n\nWallet: {from}\nNonce: {nonce}\nValid After: {validAfter}\nValid Before: {validBefore}"},
        }
    ],
}


def receipt_header(**payload) -> str:
    return base64.b64encode(json.dumps(payload or {"status": "success", "rail": "escrow"}).encode()).decode()


class FakeTransport(TelegraphClient):
    """Replaces the two HTTP methods; everything else is the real client."""

    def __init__(self, responses, **kwargs):
        kwargs.setdefault("spend_log", SpendLog(path=kwargs.pop("spend_path")))
        super().__init__(TEST_KEY, **kwargs)
        self.responses = list(responses)
        self.calls = []

    def _post(self, path, payload, headers=None):
        self.calls.append((path, payload, headers))
        status, hdrs, body = self.responses.pop(0)
        return status, hdrs, json.dumps(body).encode() if not isinstance(body, bytes) else body, 5

    def _get(self, path):
        return {"intents": [], "miners": []}


def client(tmp_path, responses, **kwargs):
    return FakeTransport(responses, spend_path=tmp_path / "spend.json", **kwargs)


# ------------------------------------------------------------------ price parsing
@pytest.mark.parametrize(
    "raw,expected",
    [("$0.01", 0.01), ("10000", 0.01), (10000, 0.01), ("$1.50", 1.5), (0.25, 0.25), ("", 0.0), (None, 0.0), (True, 0.0)],
)
def test_usd_parses_every_shape_the_node_uses(raw, expected):
    assert _usd(raw) == pytest.approx(expected)


# ----------------------------------------------------------------------- receipt
def test_receipt_header_is_read_case_insensitively():
    parsed = _receipt({"X-Payment-Response": receipt_header(receipt_hash="0xabc")})
    assert parsed is not None and parsed["receipt_hash"] == "0xabc"
    assert _receipt({"x-payment-response": receipt_header()})["rail"] == "escrow"
    assert _receipt({}) is None


# -------------------------------------------------------------------- paid success
def test_ask_pays_from_escrow_and_keeps_evidence(tmp_path):
    c = client(
        tmp_path,
        [
            (402, {}, CHALLENGE),
            (
                200,
                {"X-Payment-Response": receipt_header(receipt_hash="0xdead")},
                {
                    "miner_id": "32005",
                    "miner_name": "Bitstamp Spot Price",
                    "result": {"price_usd": 63697.31},
                    "cost_usd": 0.01,
                    "signal_hash": "0x34f6",
                    "delivery": "specialist",
                },
            ),
        ],
    )
    result = c.ask("CRYPTO_PRICE_USD", {"symbol": "BTC"})
    assert result.ok
    assert result.result["price_usd"] == 63697.31
    assert result.receipt is not None and result.receipt["receipt_hash"] == "0xdead"
    assert result.signal_hash == "0x34f6"
    assert result.price_usd == 0.01
    assert result.rail == "escrow"
    # the second request carried a signed escrow envelope, and no key material
    payment = base64.b64decode(c.calls[1][2]["X-PAYMENT"]).decode()
    assert '"scheme": "escrow"' in payment
    assert c.run_spent == 0.01
    assert json.loads((tmp_path / "spend.json").read_text())  # a day was recorded


# ------------------------------------------------------------------------ refusals
def test_refused_escrow_raises_and_charges_nothing(tmp_path):
    refusal = dict(CHALLENGE, reason="insufficient escrow for delivery: balance=0 μUSDC")
    c = client(tmp_path, [(402, {}, CHALLENGE), (402, {}, refusal)])
    with pytest.raises(PaymentRefused) as exc:
        c.ask("CRYPTO_PRICE_USD", {"symbol": "BTC"})
    assert "insufficient escrow" in str(exc.value)
    assert c.run_spent == 0.0


def test_per_ask_cap_refuses_before_signing(tmp_path):
    c = client(tmp_path, [(402, {}, CHALLENGE)], max_usd_per_ask=0.001)
    with pytest.raises(PaymentRefused) as exc:
        c.ask("CRYPTO_PRICE_USD", {"symbol": "BTC"})
    assert "per-ask cap" in str(exc.value)
    assert len(c.calls) == 1  # only the challenge was fetched


def test_per_run_cap_refuses_the_second_ask(tmp_path):
    ok_answer = (200, {"X-Payment-Response": receipt_header()}, {"result": {}, "cost_usd": 0.01})
    c = client(tmp_path, [(402, {}, CHALLENGE), ok_answer, (402, {}, CHALLENGE)], max_usd_per_run=0.015)
    c.ask("CRYPTO_PRICE_USD", {"symbol": "BTC"})
    with pytest.raises(PaymentRefused) as exc:
        c.ask("CRYPTO_PRICE_USD", {"symbol": "ETH"})
    assert "per-run cap" in str(exc.value)


def test_dry_run_prices_without_paying(tmp_path):
    c = client(tmp_path, [(402, {}, CHALLENGE)], dry_run=True)
    with pytest.raises(PaymentRefused) as exc:
        c.ask("CRYPTO_PRICE_USD", {"symbol": "BTC"})
    assert "dry run" in str(exc.value)
    assert len(c.calls) == 1
    assert c.run_spent == 0.0


def test_quote_reports_escrow_price_without_signing(tmp_path):
    c = client(tmp_path, [(402, {}, CHALLENGE)])
    quote = c.quote("CRYPTO_PRICE_USD", {"symbol": "BTC"})
    assert quote["escrow_available"] is True
    assert quote["escrow_price_usd"] == 0.01
    assert quote["other_rails"] == []
    assert len(c.calls) == 1


def test_spend_log_tracks_days_and_rounds(tmp_path):
    log = SpendLog(path=tmp_path / "spend.json")
    log.add(0.01)
    log.add(0.02)
    assert log.today() == pytest.approx(0.03)
    assert list(log.history()) == [log.history().popitem()[0]]
