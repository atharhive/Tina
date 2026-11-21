"""Queen and memo tests: the decision rules, and the honesty of the document."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from colony.cluster import cluster  # noqa: E402
from colony.intents import Inputs  # noqa: E402
from colony.ledger import Ledger  # noqa: E402
from colony.memo import bundle, footnotes, render  # noqa: E402
from colony.policy import Budget  # noqa: E402
from colony.queen import Answer, judge  # noqa: E402
from colony.scouts import Fact  # noqa: E402


def fact(claim_id, miner, fields, ok=True, price=0.01, error=None):
    return Fact(claim_id=claim_id, intent="X", params={}, miner=miner, miner_id=miner,
                fields=fields, price_usd=price, ok=ok, error=error)


def clusters(*facts):
    return cluster(list(facts))


# ------------------------------------------------------------------- verdicts
def test_clean_screen_allows():
    v = judge(clusters(
        fact("sanctions", "a", {"matched": False}),
        fact("sanctions", "b", {"matched": False}),
        fact("registry", "a", {"active": True}),
        fact("registry", "b", {"active": True}),
    ))
    assert v["verdict"] == "ALLOW"
    assert v["confidence"] == 100


def test_sanctions_hit_blocks():
    v = judge(clusters(
        fact("sanctions", "a", {"matched": True}),
        fact("sanctions", "b", {"matched": True}),
        fact("registry", "a", {"active": True}),
    ))
    assert v["verdict"] == "BLOCK"


def test_unchecked_sanctions_is_a_hold_not_an_allow():
    v = judge(clusters(
        fact("sanctions", "a", {}, ok=False, error="500"),
        fact("registry", "a", {"active": True}),
    ))
    assert v["verdict"] == "HOLD"
    assert any("could not be checked" in r for r in v["reasons"])


def test_inactive_entity_blocks():
    v = judge(clusters(
        fact("sanctions", "a", {"matched": False}),
        fact("registry", "a", {"active": False}),
    ))
    assert v["verdict"] == "BLOCK"


def test_single_source_sanctions_conditions_rather_than_allowing():
    v = judge(clusters(
        fact("sanctions", "a", {"matched": False}),
        fact("registry", "a", {"active": True}),
        fact("registry", "b", {"active": True}),
    ))
    assert v["verdict"] == "ALLOW WITH CONDITIONS"
    assert "single source" in " ".join(v["reasons"])


def test_disagreement_on_a_secondary_claim_conditions():
    v = judge(clusters(
        fact("sanctions", "a", {"matched": False}),
        fact("sanctions", "b", {"matched": False}),
        fact("registry", "a", {"active": True}),
        fact("registry", "b", {"active": True}),
        fact("news", "a", {"result_count": 4}),
        fact("news", "b", {"result_count": 0}),
    ))
    assert v["verdict"] == "ALLOW WITH CONDITIONS"
    assert any("news" in r for r in v["reasons"])


def test_confidence_counts_only_settled_load_bearing_claims():
    v = judge(clusters(
        fact("sanctions", "a", {"matched": False}),
        fact("sanctions", "b", {"matched": False}),
        fact("registry", "a", {"active": True}),
    ))
    assert v["confidence"] == 50


# ---------------------------------------------------------------------- memo
def answer_with(**kwargs):
    a = Answer(
        question="q",
        inputs=Inputs(company="Acme A/S"),
        clusters=clusters(
            fact("sanctions", "zk-sanctions", {"matched": False}),
            fact("registry", "a1-preflight", {"legal_name": "ACME A/S", "active": True}),
            fact("identity", "brandfetch", {"employee_count": None}),
        ),
        budget=Budget(total_usd=0.25),
        ledger=Ledger(),
    )
    for f in [f for c in a.clusters.values() for f in c.facts]:
        a.ledger.record(f)
    a.verdict = kwargs.get("verdict") or judge(a.clusters)
    return a


def test_memo_footnotes_every_purchase():
    a = answer_with()
    notes = footnotes(a)
    assert len(notes) == 3
    memo = render(a)
    assert "[1]" in memo and "[3]" in memo


def test_memo_says_what_it_could_not_verify():
    memo = render(answer_with())
    assert "What we could not verify" in memo
    assert "identity" in memo


def test_bundle_hash_changes_with_the_evidence():
    a = answer_with()
    first = bundle(a)["bundle_sha256"]
    a.clusters["sanctions"].facts[0].fields["matched"] = True
    second = bundle(a)["bundle_sha256"]
    assert first != second


def test_bundle_carries_the_memo_and_every_receipt():
    b = bundle(answer_with())
    assert b["memo"].startswith("# Acme A/S")
    assert b["ledger"]["purchases"] == 3
    assert b["escalations"] == []
