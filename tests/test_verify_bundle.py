"""Bundle verification tests: the checker must catch edits, not just agree."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from colony.intents import Inputs  # noqa: E402
from colony.cluster import cluster  # noqa: E402
from colony.ledger import Ledger  # noqa: E402
from colony.memo import bundle  # noqa: E402
from colony.policy import Budget  # noqa: E402
from colony.queen import Answer, judge  # noqa: E402
from colony.scouts import Fact  # noqa: E402
from scripts.verify_bundle import canonical_hash, verify  # noqa: E402


def make_bundle() -> dict:
    facts = [
        Fact(claim_id="sanctions", intent="S", params={}, miner="a", miner_id="1",
             fields={"matched": False}, price_usd=0.01, receipt={"receipt_hash": "0x1"}, ok=True),
        Fact(claim_id="registry", intent="R", params={}, miner="b", miner_id="2",
             fields={"active": True}, price_usd=0.01, receipt={"receipt_hash": "0x2"}, ok=True),
    ]
    a = Answer(question="q", inputs=Inputs(company="Acme"), clusters=cluster(facts),
               budget=Budget(total_usd=0.05), ledger=Ledger())
    for f in facts:
        a.ledger.record(f)
        a.budget.charge(f.price_usd)
    a.verdict = judge(a.clusters)
    return bundle(a)


def test_a_fresh_bundle_verifies():
    ok, notes = verify(make_bundle())
    assert ok, notes


def test_editing_a_fact_breaks_the_hash():
    b = make_bundle()
    b["clusters"]["sanctions"]["facts"][0]["fields"]["matched"] = True
    ok, notes = verify(b)
    assert not ok
    assert any("hash mismatch" in n for n in notes)


def test_a_cluster_without_a_purchase_is_caught():
    b = make_bundle()
    b["clusters"]["news"] = {"state": "settled", "facts": [], "scouts": 0}
    b["bundle_sha256"] = canonical_hash(b)
    ok, notes = verify(b)
    assert not ok
    assert any("news" in n for n in notes)


def test_a_budget_that_does_not_match_the_receipts_is_caught():
    b = make_bundle()
    b["budget"]["spent_usd"] = 0.99
    b["bundle_sha256"] = canonical_hash(b)
    ok, notes = verify(b)
    assert not ok
    assert any("budget mismatch" in n for n in notes)
