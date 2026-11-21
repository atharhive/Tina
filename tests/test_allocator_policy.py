"""Allocator and policy tests: coverage first, then depth only where it pays."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from colony.allocator import allocate, escalation_plan  # noqa: E402
from colony.cluster import cluster  # noqa: E402
from colony.intents import CLAIMS, BY_ID  # noqa: E402
from colony.policy import Budget, BudgetExceeded  # noqa: E402
from colony.scouts import Fact  # noqa: E402


def fact(claim_id, miner, fields, ok=True, price=0.01, error=None):
    return Fact(claim_id=claim_id, intent="X", params={}, miner=miner, miner_id=miner,
                fields=fields, price_usd=price, ok=ok, error=error)


# ------------------------------------------------------------------ budget
def test_budget_charges_and_tracks_remaining():
    b = Budget(total_usd=0.10)
    b.charge(0.03)
    b.charge(0.02)
    assert b.spent_usd == 0.05
    assert b.remaining == 0.05
    assert b.purchases == 2


def test_budget_refuses_an_ask_over_the_per_ask_cap():
    b = Budget(total_usd=1.0, max_per_ask=0.02)
    with pytest.raises(BudgetExceeded):
        b.charge(0.05)


def test_budget_refuses_to_go_past_the_total():
    b = Budget(total_usd=0.02)
    b.charge(0.01)
    with pytest.raises(BudgetExceeded):
        b.charge(0.02)


# --------------------------------------------------------------- allocation
def test_allocation_buys_one_ask_per_claim_while_money_lasts():
    plan = allocate(CLAIMS, Budget(total_usd=0.03))
    assert len(plan) == 3
    assert all(a.miners == 1 for a in plan)


def test_allocation_spends_load_bearing_claims_first():
    plan = allocate(CLAIMS, Budget(total_usd=0.02))
    assert [a.claim.id for a in plan] == ["sanctions", "registry"]


def test_allocation_with_a_full_budget_covers_every_claim_once():
    plan = allocate(CLAIMS, Budget(total_usd=1.0))
    assert len(plan) == len(CLAIMS)
    assert sum(a.miners for a in plan) == len(CLAIMS)


# --------------------------------------------------------------- escalation
def test_single_source_is_not_worth_escalating_for_a_non_load_bearing_claim():
    clusters = cluster([fact("news", "a", {"result_count": 4})])
    plan = escalation_plan(["news"], clusters, Budget(total_usd=1.0))
    assert plan == []


def test_a_dead_load_bearing_claim_is_escalated():
    clusters = cluster([fact("sanctions", "a", {}, ok=False, error="500")])
    plan = escalation_plan(["sanctions"], clusters, Budget(total_usd=1.0))
    assert [a.claim.id for a in plan] == ["sanctions"]
    assert plan[0].miners == 2


def test_disagreement_earns_escalation_even_when_not_load_bearing():
    clusters = cluster([fact("news", "a", {"result_count": 4}), fact("news", "b", {"result_count": 0})])
    plan = escalation_plan(["news"], clusters, Budget(total_usd=1.0))
    assert plan and plan[0].claim.id == "news"


def test_escalation_is_capped_and_stops_when_the_budget_is_gone():
    clusters = cluster([
        fact("sanctions", "a", {}, ok=False, error="500"),
        fact("registry", "a", {}, ok=False, error="500"),
        fact("news", "a", {"result_count": 4}),
    ])
    capped = escalation_plan(["sanctions", "registry", "news"], clusters, Budget(total_usd=1.0), max_claims=2)
    assert len(capped) == 2
    broke = escalation_plan(["sanctions"], clusters, Budget(total_usd=0.0))
    assert broke == []


def test_escalation_respects_the_remaining_budget():
    clusters = cluster([fact("sanctions", "a", {}, ok=False, error="500")])
    plan = escalation_plan(["sanctions"], clusters, Budget(total_usd=0.03, spent_usd=0.02))
    assert plan[0].miners == 1
