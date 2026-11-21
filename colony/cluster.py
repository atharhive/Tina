"""Clusters: where scouts agree, disagree, or came back empty.

The cluster map is the only thing the queen reads. It never reads raw answers
directly, so a single confident scout cannot move the decision on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .scouts import Fact


@dataclass
class Cluster:
    claim_id: str
    facts: list[Fact] = field(default_factory=list)

    @property
    def answered(self) -> list[Fact]:
        return [f for f in self.facts if f.ok]

    @property
    def empty(self) -> list[Fact]:
        return [f for f in self.answered if f.empty]

    @property
    def failed(self) -> list[Fact]:
        return [f for f in self.facts if not f.ok]

    @property
    def solid(self) -> list[Fact]:
        return [f for f in self.answered if not f.empty]

    def values(self, name: str) -> list[Any]:
        return [f.fields.get(name) for f in self.solid if f.fields.get(name) not in (None, "", [])]

    def agreement(self, name: str) -> float | None:
        vals = self.values(name)
        if not vals:
            return None
        text = [str(v) for v in vals]
        top = max(set(text), key=text.count)
        return round(text.count(top) / len(text), 3)

    @property
    def state(self) -> str:
        """settled, contested, blind or dead."""
        solid = self.solid
        if not solid:
            if self.answered and self.empty:
                return "blind"
            return "dead"
        if len(solid) == 1:
            return "single"
        agreements = [a for name in solid[0].fields for a in [self.agreement(name)] if a is not None]
        if agreements and min(agreements) < 1.0:
            return "contested"
        return "settled"

    @property
    def cost_usd(self) -> float:
        return round(sum(f.price_usd for f in self.facts), 6)

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "state": self.state,
            "scouts": len(self.facts),
            "solid": len(self.solid),
            "empty": len(self.empty),
            "failed": len(self.failed),
            "cost_usd": self.cost_usd,
            "agreement": {name: self.agreement(name) for name in (self.solid[0].fields if self.solid else {})},
            "facts": [f.as_dict() for f in self.facts],
        }


def cluster(facts: list[Fact]) -> dict[str, Cluster]:
    """Group facts by claim, preserving the registry order the caller used."""
    out: dict[str, Cluster] = {}
    for fact in facts:
        out.setdefault(fact.claim_id, Cluster(claim_id=fact.claim_id)).facts.append(fact)
    return out


def contested(clusters: dict[str, Cluster]) -> list[str]:
    """Claims the queen should escalate: contested, single-sourced or blind."""
    return [cid for cid, c in clusters.items() if c.state in {"contested", "single", "blind", "dead"}]
