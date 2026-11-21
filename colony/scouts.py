"""Scouts: one claim, one ask, one structured fact.

A scout is deliberately dumb. It knows one claim, it asks one miner, and it returns
what came back without interpreting it. Interpretation is the queen's job, and only
after every scout has reported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .client import PaymentRefused, TelegraphClient, TelegraphError
from .intents import Claim, Inputs


@dataclass
class Fact:
    """What one scout brought back, with everything needed to audit it."""

    claim_id: str
    intent: str
    params: dict[str, Any]
    miner: str
    miner_id: str
    fields: dict[str, Any] = field(default_factory=dict)
    price_usd: float = 0.0
    receipt: dict[str, Any] | None = None
    signal_hash: str | None = None
    ok: bool = False
    error: str | None = None

    @property
    def empty(self) -> bool:
        """Answered, but every field we asked for came back blank.

        False and 0 are answers, not blanks: "no sanctions match" and "zero filings"
        are findings. Treating them as empty would turn a clean screen into a gap,
        which is the most dangerous mistake this product can make.
        """
        blank = (None, "", [], {})
        return self.ok and not any(v not in blank for v in self.fields.values())

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "intent": self.intent,
            "params": self.params,
            "miner": self.miner,
            "miner_id": self.miner_id,
            "fields": self.fields,
            "price_usd": self.price_usd,
            "receipt": self.receipt,
            "signal_hash": self.signal_hash,
            "ok": self.ok,
            "empty": self.empty,
            "error": self.error,
        }


def scout(
    client: TelegraphClient,
    claim: Claim,
    inputs: Inputs,
    miner_id: str | None = None,
    miners: int = 1,
) -> list[Fact]:
    """Run one claim against one miner (or the node's routed choice)."""
    params = claim.build(inputs)
    targets: list[dict[str, Any] | None]
    if miner_id:
        targets = [{"id": miner_id, "slug": f"miner-{miner_id}"}]
    elif miners <= 0:
        targets = [None]
    else:
        try:
            pool: list[dict[str, Any] | None] = list(client.miners_for(claim.intent, limit=miners))
        except TelegraphError:
            pool = []
        targets = pool or [None]

    facts: list[Fact] = []
    for target in targets:
        try:
            result = client.ask(claim.intent, params, miner_id=(target or {}).get("id"))
        except PaymentRefused as exc:
            facts.append(
                Fact(
                    claim_id=claim.id,
                    intent=claim.intent,
                    params=params,
                    miner=target.get("slug", "routed") if target else "routed",
                    miner_id=(target or {}).get("id", ""),
                    ok=False,
                    error=str(exc),
                )
            )
            break
        except TelegraphError as exc:
            facts.append(
                Fact(
                    claim_id=claim.id,
                    intent=claim.intent,
                    params=params,
                    miner=(target or {}).get("slug", "routed"),
                    miner_id=(target or {}).get("id", ""),
                    ok=False,
                    error=str(exc),
                )
            )
            continue

        payload = result.result if isinstance(result.result, dict) else {}
        facts.append(
            Fact(
                claim_id=claim.id,
                intent=claim.intent,
                params=params,
                miner=result.miner_name or (target or {}).get("slug", "routed"),
                miner_id=str(result.miner_id or ""),
                fields={name: payload.get(name) for name in claim.fields},
                price_usd=result.price_usd,
                receipt=result.receipt,
                signal_hash=result.signal_hash,
                ok=result.ok,
            )
        )
    return facts
