"""Allocator: turn a budget into a scout plan, then decide where to spend more.

Coverage first, then depth. A run with a small budget buys one ask per claim in
priority order and stops when the money runs out. A contested claim is the only
thing that earns a second and third ask, because that is the only place an extra
purchase changes the answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from .intents import Claim, Inputs
from .policy import Budget

DEFAULT_PRICE = 0.01


@dataclass
class Assignment:
    claim: Claim
    miners: int
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {"claim": self.claim.id, "miners": self.miners, "reason": self.reason}


def allocate(claims: tuple[Claim, ...] | list[Claim], budget: Budget, price_hint: float = DEFAULT_PRICE) -> list[Assignment]:
    """One ask per claim, most load-bearing first, until the budget is committed."""
    ordered = sorted(claims, key=lambda c: (not c.load_bearing, c.priority, c.id))
    out: list[Assignment] = []
    committed = 0.0
    for claim in ordered:
        if committed + price_hint > budget.total_usd:
            break
        out.append(Assignment(claim=claim, miners=1, reason="coverage"))
        committed += price_hint
    return out


def escalation_plan(contested_ids: list[str], clusters, budget: Budget, price_hint: float = DEFAULT_PRICE, extra: int = 2, max_claims: int = 2) -> list[Assignment]:
    """Spend more only where it changes the answer.

    A claim earns extra scouts when it is load-bearing and unsettled, or when two
    sources already disagree. Being single-sourced is not enough: that is the normal
    state of a cheap run, and paying 3x for it is the mistake this product exists to
    avoid.
    """
    from .intents import BY_ID

    out: list[Assignment] = []
    for cid in contested_ids:
        if len(out) >= max_claims:
            break
        claim = BY_ID.get(cid)
        if claim is None:
            continue
        state = clusters[cid].state
        worth_it = (claim.load_bearing and state != "settled") or state == "contested"
        if not worth_it:
            continue
        room = int(budget.remaining // price_hint)
        if room <= 0:
            break
        take = min(extra, room)
        out.append(Assignment(claim=claim, miners=take, reason=f"escalation:{state}"))
    return out
