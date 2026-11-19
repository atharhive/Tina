"""Unit tests for Tina's scoring and evidence rules. No network, no wallet, no spend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.client import AskResult  # noqa: E402
from core.flows import (  # noqa: E402
    Desk,
    Observation,
    median,
    score_listing,
    score_stablecoin,
    score_yield,
    spread_pct,
)
from core.report import render_memo, write_run  # noqa: E402


def answer(intent, miner_id, result, price=0.01, status=200, error=None):
    return AskResult(
        intent=intent,
        params={},
        miner_id=miner_id,
        miner_name=f"miner-{miner_id}",
        status=status,
        result=result,
        receipt={"status": "success", "rail": "escrow"},
        price_usd=price,
        rail="escrow",
        elapsed_ms=120,
        error=error,
    )


# ------------------------------------------------------------------ statistics
def test_median_and_spread():
    assert median([1, 2, 3]) == 2
    assert median([10.0, 12.0]) == 11.0
    assert median([]) is None
    assert spread_pct([100, 110]) == 9.52
    assert spread_pct([5]) is None
    assert spread_pct([0, 0]) is None


def test_observation_agreement_counts_only_answered():
    obs = Observation("X", {})
    obs.samples = [
        answer("X", "1", {"holders_count": 1000}),
        answer("X", "2", {"holders_count": 1000}),
        answer("X", "3", {"holders_count": 5000}),
        answer("X", "4", None, status=500, error="miner down"),
    ]
    field = obs.field("holders_count")
    assert field.median == 1000
    assert field.agreement == round(2 / 3, 3)
    assert len(obs.missing) == 1
    assert obs.healthy is True


def test_observation_unhealthy_when_one_answer():
    obs = Observation("X", {})
    obs.samples = [answer("X", "1", {"tvl_usd": 5})]
    assert obs.healthy is False


# --------------------------------------------------------------------- listing
def test_listing_rejects_thin_unknown_market():
    out = score_listing(holders=120, liquidity_usd=40_000, trade_usd=25_000, wash_pct=31, wash_verdict="suspicious", agreement={})
    assert out["verdict"] == "REJECT"
    assert out["risk_score"] >= 60


def test_listing_passes_deep_market():
    out = score_listing(holders=180_000, liquidity_usd=9_000_000, trade_usd=25_000, wash_pct=3, wash_verdict="clean", agreement={"liquidity_usd": 1.0})
    assert out["verdict"] == "PASS"
    assert out["risk_score"] < 30


def test_listing_flags_disagreement():
    agree = score_listing(holders=90_000, liquidity_usd=5_000_000, trade_usd=10_000, wash_pct=2, wash_verdict="clean", agreement={})
    disagree = score_listing(holders=90_000, liquidity_usd=5_000_000, trade_usd=10_000, wash_pct=2, wash_verdict="clean", agreement={"liquidity_usd": 0.5})
    assert disagree["risk_score"] > agree["risk_score"]


# ------------------------------------------------------------------ stablecoin
def test_stablecoin_pegged_and_attested():
    out = score_stablecoin(price_usd=0.9999, reserve=1.2e9, sanctioned=False, agreement={"price_usd": 1.0})
    assert out["verdict"] == "PASS"


def test_stablecoin_depeg_rejected():
    out = score_stablecoin(price_usd=0.94, reserve=None, sanctioned=False, agreement={})
    assert out["verdict"] == "REJECT"
    assert any("peg" in r for r in out["reasons"])


def test_stablecoin_sanctions_is_fatal():
    out = score_stablecoin(price_usd=1.0, reserve=1e9, sanctioned=True, agreement={})
    assert out["risk_score"] >= 40


# ----------------------------------------------------------------------- yield
def test_yield_implausible_apy_with_small_tvl():
    out = score_yield(apy_bps=4800, tvl_usd=250_000, has_yield_data=True, agreement={})
    assert out["verdict"] == "REJECT"


def test_yield_sane_bps_high_tvl():
    out = score_yield(apy_bps=420, tvl_usd=900_000_000, has_yield_data=True, agreement={"supply_apy": 1.0})
    assert out["verdict"] == "PASS"


def test_yield_missing_data_is_not_silent():
    out = score_yield(apy_bps=None, tvl_usd=None, has_yield_data=False, agreement={})
    assert out["verdict"] != "PASS"
    assert any("nothing to verify" in r for r in out["reasons"])


def test_missing_field_counts_against_the_verdict():
    clean = score_yield(apy_bps=420, tvl_usd=900_000_000, has_yield_data=True, agreement={})
    partly = score_yield(
        apy_bps=420,
        tvl_usd=900_000_000,
        has_yield_data=True,
        agreement={},
        missing={"supply_apy": 1},
    )
    assert partly["risk_score"] > clean["risk_score"]
    assert any("supply_apy" in r for r in partly["reasons"])


def test_single_source_cannot_pass():
    out = score_yield(apy_bps=420, tvl_usd=900_000_000, has_yield_data=True, agreement={}, thin=True)
    assert out["verdict"] != "PASS"
    assert any("one miner" in r for r in out["reasons"])


def test_float_noise_is_not_disagreement():
    obs = Observation("X", {})
    obs.samples = [
        answer("X", "1", {"liquidity_usd": 24873363.78}),
        answer("X", "2", {"liquidity_usd": 24873363.78}),
        answer("X", "3", {"liquidity_usd": 24873355}),
    ]
    assert obs.field("liquidity_usd").agreement == 1.0


def test_field_missing_is_counted_on_the_observation():
    obs = Observation("X", {})
    obs.samples = [
        answer("X", "1", {"supply_apy": 400}),
        answer("X", "2", {"chains": [{"tvl": 1}]}),
    ]
    field = obs.field("supply_apy")
    assert field.missing == 1
    assert field.median == 400


# -------------------------------------------------------------------- evidence
def test_memo_contains_cost_receipt_and_limits(tmp_path: Path):
    report = {
        "workflow": "yield",
        "mission": "Mission 13 Asset Management",
        "input": {"project": "aave-v3", "symbol": "USDC", "chain": "ethereum"},
        "verdict": {"verdict": "PASS", "risk_score": 8.0, "reasons": ["APY within range"]},
        "cost_usd": 0.06,
        "observations": [
            {
                "intent": "CRYPTO_YIELD_RATE_GENERAL",
                "params": {"project": "aave-v3"},
                "asked": 3,
                "answered": 3,
                "cost_usd": 0.03,
                "error": None,
                "answers": [answer("CRYPTO_YIELD_RATE_GENERAL", "1", {"supply_apy": 420}).as_dict()],
            }
        ],
        "gaps": [],
    }
    memo = render_memo(report)
    assert "Cost of this outcome: $0.0600" in memo
    assert "receipt" in memo
    assert "Limits of this memo" in memo
    paths = write_run(report, tmp_path)
    assert paths["memo"].exists() and paths["run"].exists()
    saved = json.loads(paths["run"].read_text())
    assert saved["run_id"].startswith("yield-")
    assert saved["verdict"]["verdict"] == "PASS"


# ------------------------------------------------------------------ failure path
class _FakeClient:
    """Stands in for TelegraphClient: no network, deterministic failure."""

    def __init__(self, fail_on=None):
        self.fail_on = fail_on
        self.calls = []

    def miners_for(self, intent, limit=5):
        return [{"id": f"{i}", "slug": f"m{i}", "name": f"Miner {i}", "rank": i, "price_usd": 0.01} for i in range(1, limit + 1)]

    def ask(self, intent, params, miner_id=None, check_caps=True):
        self.calls.append((intent, miner_id))
        from core.client import MinerFailed

        if self.fail_on and miner_id in self.fail_on:
            raise MinerFailed("miner timed out")
        return answer(intent, miner_id, {"tvl_usd": 1_000_000})


def test_desk_keeps_going_when_one_miner_fails():
    desk = Desk(_FakeClient(fail_on={"2"}), miners_per_intent=3)  # type: ignore[arg-type]
    obs = desk.observe("TVL_LOOKUP_GENERAL", {"protocol": "x"})
    assert len(obs.samples) == 3
    assert len(obs.answered) == 2
    assert obs.error is None
    assert obs.missing[0].error == "miner timed out"
