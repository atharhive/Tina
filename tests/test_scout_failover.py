"""Failover tests: a broken miner must not become a blind claim.

A failed ask is not billed, so trying the next ranked provider costs nothing and is the
difference between a dead claim and an answered one. This file pins that behaviour, and
pins the one case where it must not happen: a refused payment.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from colony.client import AskResult, PaymentRefused, TelegraphError  # noqa: E402
from colony.intents import BY_ID, Inputs  # noqa: E402
from colony.scouts import scout  # noqa: E402


class ScriptedClient:
    """Answers by miner id, or raises the exception the script says."""

    def __init__(self, script: dict[str, object], pool=("a", "b", "c")):
        self.script = script
        self.pool = pool
        self.asked: list[str] = []

    def miners_for(self, intent, limit=5):
        return [{"id": m, "slug": f"miner-{m}"} for m in self.pool][:limit]

    def ask(self, intent, params, miner_id=None, check_caps=True):
        self.asked.append(str(miner_id))
        outcome = self.script.get(str(miner_id), TelegraphError("no script"))
        if isinstance(outcome, Exception):
            raise outcome
        return AskResult(
            intent=intent, params=params, miner_id=str(miner_id), miner_name=f"miner-{miner_id}",
            status=200, result=outcome, receipt={"receipt_hash": "0x1"},
            price_usd=0.01, rail="escrow", elapsed_ms=4, signal_hash="0xdead",
        )


def test_a_broken_miner_fails_over_to_the_next_ranked_one():
    client = ScriptedClient({"a": TelegraphError("HTTP 500 after payment"), "b": {"matched": False, "match_score": 0}})
    facts = scout(client, BY_ID["sanctions"], Inputs(company="Acme"))
    assert [f.ok for f in facts] == [False, True]
    assert facts[1].miner == "miner-b"
    assert facts[1].fields["matched"] is False
    assert facts[0].price_usd == 0.0


def test_failover_stops_once_the_requested_number_of_answers_land():
    client = ScriptedClient({m: {"matched": False} for m in ("a", "b", "c")})
    facts = scout(client, BY_ID["sanctions"], Inputs(company="Acme"), miners=2)
    assert len(facts) == 2
    assert client.asked == ["a", "b"]


def test_a_refused_payment_stops_the_claim_instead_of_retrying():
    client = ScriptedClient({"a": PaymentRefused("insufficient escrow"), "b": {"matched": False}})
    facts = scout(client, BY_ID["sanctions"], Inputs(company="Acme"))
    assert len(facts) == 1
    assert facts[0].ok is False
    assert "insufficient escrow" in (facts[0].error or "")
    assert client.asked == ["a"]


def test_when_every_candidate_fails_the_claim_is_dead_not_invented():
    client = ScriptedClient({m: TelegraphError("boom") for m in ("a", "b", "c")})
    facts = scout(client, BY_ID["sanctions"], Inputs(company="Acme"))
    assert len(facts) == 3
    assert not any(f.ok for f in facts)


def test_retries_are_bounded_so_a_cheap_run_stays_cheap():
    client = ScriptedClient({m: TelegraphError("boom") for m in ("a", "b", "c", "d", "e")}, pool=("a", "b", "c", "d", "e"))
    facts = scout(client, BY_ID["sanctions"], Inputs(company="Acme"), retries=1)
    assert len(facts) == 2


def test_an_explicit_miner_is_not_replaced():
    client = ScriptedClient({"a": {"matched": False}, "b": {"matched": False}})
    facts = scout(client, BY_ID["sanctions"], Inputs(company="Acme"), miner_id="b")
    assert client.asked == ["b"]
    assert facts[0].miner == "miner-b"
