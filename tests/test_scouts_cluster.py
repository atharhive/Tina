"""Scout and cluster tests: what counts as an answer, and when sources disagree."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from colony.cluster import cluster, contested  # noqa: E402
from colony.scouts import Fact  # noqa: E402


def fact(claim_id, miner, fields, ok=True, price=0.01, error=None):
    return Fact(
        claim_id=claim_id,
        intent="X",
        params={},
        miner=miner,
        miner_id=miner,
        fields=fields,
        price_usd=price,
        ok=ok,
        error=error,
    )


def test_false_and_zero_are_answers_not_blanks():
    assert fact("sanctions", "a", {"matched": False, "match_score": 0}).empty is False
    assert fact("filings", "a", {"filing_count": 0}).empty is False
    assert fact("identity", "a", {"employee_count": None, "industry": ""}).empty is True


def test_state_settled_when_sources_agree():
    c = cluster([fact("sanctions", "a", {"matched": False}), fact("sanctions", "b", {"matched": False})])["sanctions"]
    assert c.state == "settled"


def test_state_contested_when_sources_disagree():
    c = cluster([fact("sanctions", "a", {"matched": False}), fact("sanctions", "b", {"matched": True})])["sanctions"]
    assert c.state == "contested"


def test_state_single_when_only_one_source_answered():
    c = cluster([fact("registry", "a", {"active": True}), fact("registry", "b", {}, ok=False, error="boom")])["registry"]
    assert c.state == "single"
    assert len(c.failed) == 1


def test_state_blind_when_answers_are_empty_but_dead_when_none():
    blind = cluster([fact("identity", "a", {"employee_count": None})])["identity"]
    dead = cluster([fact("identity", "a", {}, ok=False, error="500")])["identity"]
    assert blind.state == "blind"
    assert dead.state == "dead"


def test_contested_includes_dead_claims_so_they_get_escalated():
    clusters = cluster([fact("sanctions", "a", {}, ok=False, error="500")])
    assert contested(clusters) == ["sanctions"]


def test_agreement_is_a_ratio_not_a_boolean():
    c = cluster([
        fact("news", "a", {"result_count": 4}),
        fact("news", "b", {"result_count": 4}),
        fact("news", "c", {"result_count": 0}),
    ])["news"]
    assert c.agreement("result_count") == 0.667


def test_cost_is_summed_per_cluster():
    c = cluster([fact("fx", "a", {}, price=0.01), fact("fx", "b", {}, price=0.02)])["fx"]
    assert c.cost_usd == 0.03
