"""Report tests: the memo and the run index are evidence, so they are tested too."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.report import render_memo, write_run  # noqa: E402


def sample(verdict="PASS", gaps=None, cost=0.03):
    return {
        "workflow": "listing",
        "mission": "Mission 01 Exchange",
        "input": {"token": "0xabc", "pool": "0xdef", "chain": "base", "trade_usd": 25000.0},
        "verdict": {"verdict": verdict, "risk_score": 15.0, "reasons": ["deep liquidity"]},
        "observations": [
            {
                "intent": "LIQUIDITY_DEPTH_VERIFY_GENERAL",
                "params": {"pool": "0xdef", "chain": "base"},
                "asked": 3,
                "answered": 2,
                "cost_usd": cost,
                "error": None,
                "answers": [
                    {
                        "intent": "LIQUIDITY_DEPTH_VERIFY_GENERAL",
                        "params": {},
                        "miner_id": "7373",
                        "miner_name": "VerifyWire",
                        "status": 200,
                        "result": {"liquidity_usd": 24000000},
                        "receipt": {"receipt_hash": "0xaaa", "rail": "escrow"},
                        "signal_hash": "0xbbb",
                        "price_usd": 0.01,
                    }
                ],
            }
        ],
        "cost_usd": cost,
        "gaps": gaps or [],
    }


def test_memo_states_the_decision_and_the_cost():
    memo = render_memo(sample())
    assert "**PASS**" in memo
    assert "Cost of this outcome: $0.0300" in memo
    assert "signal hash: `0xbbb`" in memo
    assert "deep liquidity" in memo


def test_reject_verdict_is_written_plainly():
    memo = render_memo(sample(verdict="REJECT"))
    assert "**REJECT**" in memo


def test_gaps_are_kept_out_of_the_verdict_but_not_hidden():
    report = sample(gaps=["CRYPTO_YIELD_RATE_GENERAL: 3 of 5 asked answered without supply_apy"])
    memo = render_memo(report)
    assert report["verdict"]["verdict"] == "PASS"  # the flow decided that, the memo does not rewrite it
    assert "answered without supply_apy" in json.dumps(report)


def test_write_run_creates_run_memo_verdict_and_index(tmp_path: Path):
    paths = write_run(sample(), tmp_path)
    assert paths["run"].exists() and paths["memo"].exists() and paths["verdict"].exists()
    saved = json.loads(paths["run"].read_text())
    assert saved["generated_at"] and saved["run_id"].startswith("listing-")
    index = json.loads((tmp_path / "index.json").read_text())
    assert len(index) == 1
    assert index[0]["workflow"] == "listing"
    assert index[0]["verdict"] == "PASS"
    assert index[0]["cost_usd"] == 0.03


def test_index_keeps_appending_and_is_capped(tmp_path: Path):
    for _ in range(3):
        write_run(sample(), tmp_path)
    index = json.loads((tmp_path / "index.json").read_text())
    assert len(index) == 3


def test_verdict_file_is_small_and_self_contained(tmp_path: Path):
    paths = write_run(sample(), tmp_path)
    decision = json.loads(paths["verdict"].read_text())
    assert set(decision) == {"run_id", "workflow", "mission", "input", "verdict", "cost_usd", "gaps"}
