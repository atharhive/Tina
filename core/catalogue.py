"""Read-only views of the network: what an intent costs and who actually serves it.

These calls are free. They never sign and never pay, so they are safe to run before
deciding whether a workflow is worth buying.
"""

from __future__ import annotations

from typing import Any

from .client import TelegraphClient
from .flows import INTENTS


def intents(client: TelegraphClient, search: str | None = None) -> list[dict[str, Any]]:
    rows = client.intents()
    needle = (search or "").upper()
    if needle:
        rows = [r for r in rows if needle in str(r.get("intent_name", ""))]
    return sorted(rows, key=lambda r: str(r.get("intent_name", "")))


def miners(client: TelegraphClient, intent: str, limit: int = 10) -> list[dict[str, Any]]:
    return client.miners_for(intent, limit=limit)


def health(client: TelegraphClient, intent: str) -> dict[str, Any]:
    """How buyable an intent looks right now, from free calls only."""
    try:
        meta = client.intent_meta(intent)
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return {"intent": intent, "error": f"intent metadata unavailable: {exc}"}

    pool = client.miners_for(intent, limit=25)
    ranked = [m for m in pool if m.get("rank") is not None]
    prices = [m["price_usd"] for m in pool if m.get("price_usd")]
    return {
        "intent": intent,
        "class": meta.get("class"),
        "miners_registered": meta.get("miner_count"),
        "miners_ranked": len(ranked),
        "best_rank": ranked[0]["rank"] if ranked else None,
        "cheapest_usd": min(prices) if prices else None,
        "priciest_usd": max(prices) if prices else None,
        "fields": [f.get("name") for f in (meta.get("response") or {}).get("fields", [])],
        "note": "a registered miner is not a ranked one; only ranked miners are routed by default",
    }


def plan(client: TelegraphClient, workflow: str, inputs: dict[str, Any], miners: int) -> dict[str, Any]:
    """Free cost estimate for a workflow: one payment challenge per intent."""
    rows: list[dict[str, Any]] = []
    total = 0.0
    for spec in INTENTS[workflow]:
        intent = spec["intent"]
        params = {upstream: inputs.get(cli_name, "") for upstream, cli_name in spec["params"].items()}
        try:
            quote = client.quote(intent, params)
            price = quote.get("escrow_price_usd") or 0.0
            rows.append(
                {
                    "intent": intent,
                    "params": params,
                    "price_usd": price,
                    "escrow_available": quote.get("escrow_available"),
                    "other_rails": quote.get("other_rails"),
                }
            )
            total += price * miners
        except Exception as exc:  # noqa: BLE001 - a quote failure is a finding, not a crash
            rows.append({"intent": intent, "params": params, "error": str(exc)})
    return {"workflow": workflow, "miners_per_intent": miners, "asks": rows, "projected_usd": round(total, 4)}


def workflow_health(client: TelegraphClient, workflow: str) -> dict[str, Any]:
    """Health of every intent a workflow depends on, so thin supply shows before spending."""
    return {
        "workflow": workflow,
        "intents": [health(client, spec["intent"]) for spec in INTENTS[workflow]],
    }
