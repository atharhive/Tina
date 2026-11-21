"""The memo: a decision where every sentence is footnoted or absent.

The rule the renderer enforces: a claim appears in the body only if a scout bought
it. Anything else lands in "What we could not verify" - which is the section that
makes the document trustworthy rather than promotional.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .cluster import Cluster
from .queen import Answer


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    if isinstance(value, list):
        return ", ".join(str(v) for v in value[:3]) + ("…" if len(value) > 3 else "")
    return str(value)


def footnotes(answer: Answer) -> list[dict[str, Any]]:
    """One footnote per purchase, in the order the money was spent."""
    out = []
    for entry in answer.ledger.entries:
        out.append(
            {
                "index": len(out) + 1,
                "claim": entry["claim"],
                "intent": entry["intent"],
                "miner": entry["miner"],
                "price_usd": entry["price_usd"],
                "signal_hash": entry.get("signal_hash"),
                "ok": entry["ok"],
            }
        )
    return out


def render(answer: Answer) -> str:
    v = answer.verdict
    notes = footnotes(answer)
    by_claim: dict[str, list[dict[str, Any]]] = {}
    for note in notes:
        by_claim.setdefault(note["claim"], []).append(note)

    lines: list[str] = []
    lines.append(f"# {answer.inputs.company}")
    lines.append("")
    lines.append(f"**Verdict: {v['verdict']}**  ·  confidence {v['confidence']}/100  ·  spent ${answer.budget.spent_usd:.4f} on {answer.budget.purchases} purchases")
    lines.append("")
    if v["reasons"]:
        for reason in v["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")

    lines.append("## What the swarm bought")
    lines.append("")
    for claim_id, cluster_ in answer.clusters.items():
        state = cluster_.state
        cites = by_claim.get(claim_id, [])
        marks = ",".join(f"[{c['index']}]" for c in cites) if cites else "no citation"
        if cluster_.solid:
            fact = cluster_.solid[0]
            values = "; ".join(f"{k}: {_fmt(val)}" for k, val in fact.fields.items() if val not in (None, "", []))
            lines.append(f"- **{claim_id}** ({state}) — {values or 'answered with empty fields'} {marks}")
        else:
            lines.append(f"- **{claim_id}** ({state}) — nothing usable came back {marks}")
    lines.append("")

    blind = [cid for cid, c in answer.clusters.items() if c.state in {"blind", "dead"}]
    contested_ids = [cid for cid, c in answer.clusters.items() if c.state == "contested"]
    lines.append("## What we could not verify")
    if not blind and not contested_ids:
        lines.append("")
        lines.append("Nothing was left unverified in the claims this budget covered.")
    else:
        for cid in blind:
            lines.append(f"- {cid}: no usable answer was returned, so nothing is asserted about it.")
        for cid in contested_ids:
            lines.append(f"- {cid}: sources disagreed, so both sides are shown and no side is chosen.")
    lines.append("")

    lines.append("## Receipts")
    lines.append("")
    lines.append("| # | claim | miner | price | signal |")
    lines.append("|---|-------|-------|-------|--------|")
    for note in notes:
        signal_ = (note["signal_hash"] or "—")[:12]
        lines.append(f"| {note['index']} | {note['claim']} | {note['miner']} | ${note['price_usd']:.4f} | `{signal_}` |")
    lines.append("")

    lines.append("## Cost")
    lines.append("")
    lines.append(f"- asks made: {len(answer.ledger.entries)} (answered: {sum(1 for e in answer.ledger.entries if e['ok'])})")
    lines.append(f"- purchases billed: {answer.budget.purchases}")
    lines.append(f"- spent: ${answer.budget.spent_usd:.4f} of ${answer.budget.total_usd:.2f} budget")
    if answer.escalations:
        lines.append(f"- escalated: {', '.join(e.claim.id for e in answer.escalations)}")
    else:
        lines.append("- escalated: nothing (no claim was contested)")
    lines.append("")
    return "\n".join(lines)


def bundle(answer: Answer) -> dict[str, Any]:
    """A signed-ready artifact: the memo, the map, the ledger, and one hash over them."""
    payload = {
        "company": answer.inputs.company,
        "question": answer.question,
        "verdict": answer.verdict,
        "clusters": {cid: c.as_dict() for cid, c in answer.clusters.items()},
        "ledger": answer.ledger.as_dict(),
        "budget": answer.budget.as_dict(),
        "escalations": [e.as_dict() for e in answer.escalations],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["bundle_sha256"] = hashlib.sha256(canonical).hexdigest()
    payload["memo"] = render(answer)
    return payload
