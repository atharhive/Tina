"""Ledger: every purchase the colony makes, append-only, with its receipt.

This is the artifact a customer's auditor reads. It is deliberately boring: one
line per purchase, nothing rewritten, totals computed rather than stored twice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Ledger:
    path: Path | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)

    def record(self, fact) -> None:
        entry = {
            "at": datetime.now(timezone.utc).isoformat(),
            "claim": fact.claim_id,
            "intent": fact.intent,
            "miner": fact.miner,
            "miner_id": fact.miner_id,
            "price_usd": round(float(fact.price_usd or 0.0), 6),
            "ok": bool(fact.ok),
            "signal_hash": fact.signal_hash,
            "receipt": fact.receipt,
        }
        self.entries.append(entry)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as fh:
                fh.write(json.dumps(entry) + "\n")

    @property
    def spent_usd(self) -> float:
        return round(sum(e["price_usd"] for e in self.entries), 6)

    @property
    def by_intent(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for entry in self.entries:
            out[entry["intent"]] = round(out.get(entry["intent"], 0.0) + entry["price_usd"], 6)
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "purchases": len(self.entries),
            "spent_usd": self.spent_usd,
            "by_intent": self.by_intent,
            "entries": self.entries,
        }
