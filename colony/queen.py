"""The queen: plan, scout, cluster, escalate, judge.

She reads the cluster map, never a raw answer, so one confident scout cannot decide
anything on its own. Escalation is spent only where the map is contested or blind,
which is what keeps a run near 1x the cost of the answer instead of 3x.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .allocator import Assignment, allocate, escalation_plan
from .client import TelegraphClient
from .cluster import Cluster, cluster, contested
from .intents import CLAIMS, Claim, Inputs
from .ledger import Ledger
from .policy import Budget, BudgetExceeded
from .scouts import Fact, scout

def _charge(budget: Budget, price: float) -> None:
    """Record a purchase against the budget; a run that runs out simply stops buying."""
    try:
        budget.charge(price)
    except BudgetExceeded:
        pass


VERDICT_RANK = {"ALLOW": 0, "ALLOW WITH CONDITIONS": 1, "HOLD": 2, "BLOCK": 3}


@dataclass
class Answer:
    question: str
    inputs: Inputs
    clusters: dict[str, Cluster]
    budget: Budget
    ledger: Ledger
    verdict: dict[str, Any] = field(default_factory=dict)
    escalations: list[Assignment] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "company": self.inputs.company,
            "verdict": self.verdict,
            "budget": self.budget.as_dict(),
            "ledger": self.ledger.as_dict(),
            "escalations": [e.as_dict() for e in self.escalations],
            "clusters": {cid: c.as_dict() for cid, c in self.clusters.items()},
        }


def _flag(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in {"true", "yes", "y", "1"}:
            return True
        if low in {"false", "no", "n", "0"}:
            return False
    return None


def judge(clusters: dict[str, Cluster], claims: tuple[Claim, ...] = CLAIMS) -> dict[str, Any]:
    """Decide from the cluster map alone."""
    reasons: list[str] = []
    verdict = "ALLOW"

    def bump(level: str) -> None:
        nonlocal verdict
        if VERDICT_RANK[level] > VERDICT_RANK[verdict]:
            verdict = level

    sanctions = clusters.get("sanctions")
    registry = clusters.get("registry")

    if sanctions is None or sanctions.state in {"dead", "blind"}:
        bump("HOLD")
        reasons.append("sanctions could not be checked: no usable answer was bought")
    elif sanctions.state in {"contested", "single"}:
        bump("ALLOW WITH CONDITIONS")
        reasons.append("sanctions came from a single source; treat it as unconfirmed")
    else:
        hits = [_flag(f.fields.get("matched")) for f in sanctions.solid]
        if any(h is True for h in hits):
            bump("BLOCK")
            reasons.append("sanctions match reported")
        elif all(h is False for h in hits):
            reasons.append("no sanctions match reported by the sources that answered")

    if registry is None or registry.state in {"dead", "blind"}:
        bump("HOLD")
        reasons.append("legal entity could not be verified in the registry")
    else:
        actives = [_flag(f.fields.get("active")) for f in registry.solid]
        if actives and all(a is False for a in actives):
            bump("BLOCK")
            reasons.append("registry reports the entity as inactive")
        elif any(a is True for a in actives):
            reasons.append("registry reports the entity as active")

    for claim in claims:
        cluster_ = clusters.get(claim.id)
        if cluster_ is None:
            continue
        if cluster_.state == "blind":
            bump("ALLOW WITH CONDITIONS")
            reasons.append(f"{claim.id}: every scout returned an empty answer")
        elif cluster_.state == "dead":
            bump("ALLOW WITH CONDITIONS")
            reasons.append(f"{claim.id}: every ask for it failed")
        elif cluster_.state == "contested":
            bump("ALLOW WITH CONDITIONS")
            busy = [name for name in (cluster_.solid[0].fields if cluster_.solid else {}) if (cluster_.agreement(name) or 1) < 1]
            reasons.append(f"{claim.id}: sources disagree on {', '.join(busy) or 'values'}")

    load_bearing = [c for c in claims if c.load_bearing]
    settled_lb = sum(1 for c in load_bearing if c.id in clusters and clusters[c.id].state == "settled")
    confidence = round(100 * settled_lb / max(1, len(load_bearing)))
    if confidence < 100 and VERDICT_RANK[verdict] < VERDICT_RANK["ALLOW WITH CONDITIONS"]:
        bump("ALLOW WITH CONDITIONS")

    return {"verdict": verdict, "confidence": confidence, "reasons": reasons}


def run(
    client: TelegraphClient,
    question: str,
    inputs: Inputs,
    budget: Budget,
    ledger: Ledger | None = None,
    claims: tuple[Claim, ...] = CLAIMS,
    escalate: bool = True,
    observer=None,
) -> Answer:
    """The whole loop: coverage, map, escalation, verdict.

    `observer` is called with every fact as it lands, so a caller can watch the swarm
    work instead of waiting for the memo. It never changes what is bought.
    """
    ledger = ledger or Ledger()
    answer = Answer(question=question, inputs=inputs, clusters={}, budget=budget, ledger=ledger)

    for assignment in allocate(claims, budget):
        for fact in scout(client, assignment.claim, inputs, miners=assignment.miners):
            ledger.record(fact)
            answer.clusters.setdefault(assignment.claim.id, Cluster(claim_id=assignment.claim.id)).facts.append(fact)
            if fact.price_usd:
                _charge(budget, fact.price_usd)
            if observer:
                observer(fact)

    if escalate:
        for assignment in escalation_plan(contested(answer.clusters), answer.clusters, budget):
            used = {f.miner_id for f in answer.clusters[assignment.claim.id].facts}
            fresh: list[Fact] = []
            pool = client.miners_for(assignment.claim.intent, limit=6)
            for miner in pool:
                if len(fresh) >= assignment.miners:
                    break
                if miner["id"] in used:
                    continue
                fresh.extend(scout(client, assignment.claim, inputs, miner_id=miner["id"]))
            for fact in fresh:
                ledger.record(fact)
                answer.clusters[assignment.claim.id].facts.append(fact)
                if fact.price_usd:
                    _charge(budget, fact.price_usd)
                if observer:
                    observer(fact)
            answer.escalations.append(assignment)

    answer.verdict = judge(answer.clusters, claims)
    return answer
