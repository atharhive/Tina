"""Observer tests: a live run can be watched, and watching never changes what is bought."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from colony.client import AskResult, TelegraphError  # noqa: E402
from colony.intents import Inputs  # noqa: E402
from colony.ledger import Ledger  # noqa: E402
from colony.policy import Budget  # noqa: E402
from colony.queen import run  # noqa: E402


class FakeClient:
    def __init__(self, answers: int = 3):
        self.answers = answers
        self.calls = 0

    def miners_for(self, intent, limit=5):
        return [{"id": f"m{self.calls}", "slug": f"miner-{self.calls}"}]

    def ask(self, intent, params, miner_id=None, check_caps=True):
        self.calls += 1
        if self.calls % 3 == 0:
            raise TelegraphError("provider broke")
        return AskResult(
            intent=intent, params=params, miner_id=str(miner_id or "1"), miner_name="fake",
            status=200, result={"matched": False, "active": True, "filing_count": 0,
                                "employee_count": 10, "result_count": 1, "rate_pct": 5.5,
                                "converted_amount": 6800.0},
            receipt={"receipt_hash": "0x1"}, price_usd=0.01, rail="escrow", elapsed_ms=3,
            signal_hash="0xdead",
        )


def test_observer_sees_every_purchase_as_it_lands():
    seen = []
    run(FakeClient(), "q", Inputs(company="Acme"), Budget(total_usd=0.10), ledger=Ledger(),
        escalate=False, observer=seen.append)
    assert len(seen) == len({f.claim_id for f in seen}) == 7


def test_observing_does_not_change_what_is_bought():
    plain = run(FakeClient(), "q", Inputs(company="Acme"), Budget(total_usd=0.10), ledger=Ledger(), escalate=False)
    watched = run(FakeClient(), "q", Inputs(company="Acme"), Budget(total_usd=0.10), ledger=Ledger(),
                  escalate=False, observer=lambda f: None)
    assert plain.budget.spent_usd == watched.budget.spent_usd
    assert {c for c in plain.clusters} == {c for c in watched.clusters}
