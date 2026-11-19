"""The three Tina workflows: what gets bought, how answers agree, what the verdict is.

Every workflow buys the same question from several independent miners. One
miner's answer is an opinion; agreement between miners that do not share a
provider is closer to a measurement. The scoring functions below are pure so
they can be unit-tested without the network.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Callable

from .client import AskResult, PaymentRefused, TelegraphClient, TelegraphError


# --------------------------------------------------------------------------- agreement
def median(values: list[Any]) -> float | None:
    clean = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return statistics.median(clean) if clean else None


def spread_pct(values: list[Any]) -> float | None:
    clean = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(clean) < 2:
        return None
    mid = statistics.median(clean)
    if mid == 0:
        return None
    return round((max(clean) - min(clean)) / abs(mid) * 100, 2)


@dataclass
class FieldRead:
    name: str
    values: list[Any]
    median: float | None = None
    spread_pct: float | None = None
    mode: Any = None
    agreement: float | None = None
    missing: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "values": self.values,
            "median": self.median,
            "spread_pct": self.spread_pct,
            "mode": self.mode,
            "agreement": self.agreement,
            "missing": self.missing,
        }


@dataclass
class Observation:
    """What the network said about one intent, across miners."""

    intent: str
    params: dict[str, Any]
    samples: list[AskResult] = field(default_factory=list)
    cost_usd: float = 0.0
    error: str | None = None

    @property
    def answered(self) -> list[AskResult]:
        return [s for s in self.samples if s.ok]

    @property
    def missing(self) -> list[AskResult]:
        return [s for s in self.samples if not s.ok]

    @property
    def healthy(self) -> bool:
        return len(self.answered) >= 2

    def field(self, name: str) -> FieldRead:
        values = []
        answered = self.answered
        for s in answered:
            result = s.result if isinstance(s.result, dict) else {}
            if name in result:
                values.append(result[name])
        numeric = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        text = [str(v) for v in values]
        mode = statistics.mode(text) if text else None
        return FieldRead(
            name=name,
            values=values,
            median=median(numeric),
            spread_pct=spread_pct(numeric),
            mode=mode,
            agreement=round(text.count(mode) / len(text), 3) if text and mode is not None else None,
            missing=len(answered) - len(values),
        )
    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "params": self.params,
            "asked": len(self.samples),
            "answered": len(self.answered),
            "cost_usd": round(self.cost_usd, 6),
            "error": self.error,
            "answers": [s.as_dict() for s in self.samples],
        }


# ----------------------------------------------------------------------------- verdicts
def score_listing(
    holders: float | None,
    liquidity_usd: float | None,
    trade_usd: float,
    wash_pct: float | None,
    wash_verdict: str | None,
    agreement: dict[str, float | None],
    missing: dict[str, int] | None = None,
    thin: bool = False,
) -> dict[str, Any]:
    """Score a token listing request from 0 (safe) to 100 (do not list)."""
    risk = 0.0
    reasons: list[str] = []
    risk += _evidence_penalty(missing, thin, reasons)

    if holders is None:
        risk += 20
        reasons.append("holder count unavailable: cannot size the holder base")
    elif holders < 500:
        risk += 35
        reasons.append(f"only {int(holders)} holders: distribution is too thin to trust")
    elif holders < 5000:
        risk += 15
        reasons.append(f"{int(holders)} holders: small base, expect volatility")

    if liquidity_usd is None:
        risk += 20
        reasons.append("liquidity unavailable: slippage on a real order is unmeasured")
    else:
        cover = liquidity_usd / max(trade_usd, 1.0)
        if cover < 5:
            risk += 35
            reasons.append(f"${liquidity_usd:,.0f} liquidity covers the ${trade_usd:,.0f} order {cover:.1f}x")
        elif cover < 20:
            risk += 15
            reasons.append(f"liquidity covers the order {cover:.0f}x: exit would move the price")

    if wash_pct is None:
        risk += 5
        reasons.append("wash-trading share not reported")
    elif wash_pct >= 25:
        risk += 30
        reasons.append(f"{wash_pct:.1f}% of volume looks like wash trading")
    elif wash_pct >= 10:
        risk += 15
        reasons.append(f"{wash_pct:.1f}% of volume looks like wash trading")

    if (wash_verdict or "").lower() in {"suspicious", "likely", "yes", "high"}:
        risk += 20
        reasons.append(f"miner verdict on volume authenticity: {wash_verdict}")

    for name, value in agreement.items():
        if value is not None and value < 1.0:
            risk += 10
            reasons.append(f"miners disagree on {name} (agreement {value:.0%})")

    risk = max(0.0, min(100.0, risk))
    return {"risk_score": round(risk, 1), "verdict": _band(risk), "reasons": reasons}


def score_stablecoin(
    price_usd: float | None,
    reserve: float | None,
    sanctioned: bool | None,
    agreement: dict[str, float | None],
    missing: dict[str, int] | None = None,
    thin: bool = False,
) -> dict[str, Any]:
    """Score a stablecoin/treasury exposure from 0 (safe) to 100 (avoid)."""
    risk = 0.0
    reasons: list[str] = []
    risk += _evidence_penalty(missing, thin, reasons)

    if price_usd is None:
        risk += 40
        reasons.append("no price available: peg health unknown")
    else:
        dev_bps = abs(price_usd - 1.0) * 10_000
        if dev_bps > 100:
            risk += 55
            reasons.append(f"peg is off by {dev_bps:.0f} bps (${price_usd:.4f})")
        elif dev_bps > 25:
            risk += 20
            reasons.append(f"peg is off by {dev_bps:.0f} bps (${price_usd:.4f})")

    if reserve is None:
        risk += 15
        reasons.append("no reserve attestation returned for this asset")
    elif reserve <= 0:
        risk += 35
        reasons.append("attested reserve is zero")
    else:
        reasons.append(f"attested reserve reported: {reserve:,.0f} units")

    if sanctioned is True:
        risk += 40
        reasons.append("issuer matches a sanctions list")
    elif sanctioned is False:
        reasons.append("issuer does not match a sanctions list")

    for name, value in agreement.items():
        if value is not None and value < 1.0:
            risk += 10
            reasons.append(f"miners disagree on {name} (agreement {value:.0%})")

    risk = max(0.0, min(100.0, risk))
    return {"risk_score": round(risk, 1), "verdict": _band(risk), "reasons": reasons}


def score_yield(
    apy_bps: float | None,
    tvl_usd: float | None,
    has_yield_data: bool,
    agreement: dict[str, float | None],
    missing: dict[str, int] | None = None,
    thin: bool = False,
) -> dict[str, Any]:
    """Score a yield opportunity from 0 (sane) to 100 (implausible)."""
    risk = 0.0
    reasons: list[str] = []
    risk += _evidence_penalty(missing, thin, reasons)

    if not has_yield_data or apy_bps is None:
        risk += 30
        reasons.append("no supply APY returned: nothing to verify")
    else:
        if apy_bps > 2500:
            risk += 45
            reasons.append(f"{apy_bps/100:.1f}% APY is far above the market for this asset")
        elif apy_bps > 1200:
            risk += 25
            reasons.append(f"{apy_bps/100:.1f}% APY needs the emissions assumption checked")
        if apy_bps < 0:
            risk += 20
            reasons.append("negative APY reported: check for a lockup or a penalty")

    if tvl_usd is None:
        risk += 20
        reasons.append("TVL unavailable: cannot judge exit depth")
    elif tvl_usd < 1_000_000:
        risk += 35
        reasons.append(f"TVL ${tvl_usd:,.0f} is too small for an institutional position")
    elif tvl_usd < 25_000_000:
        risk += 15
        reasons.append(f"TVL ${tvl_usd:,.0f}: thin for size")

    for name, value in agreement.items():
        if value is not None and value < 1.0:
            risk += 10
            reasons.append(f"miners disagree on {name} (agreement {value:.0%})")

    risk = max(0.0, min(100.0, risk))
    return {"risk_score": round(risk, 1), "verdict": _band(risk), "reasons": reasons}


def _thin(observations: list[Observation]) -> bool:
    """True when the run has no corroboration on its main signal, or nothing on a required one."""
    if not observations:
        return True
    return len(observations[0].answered) < 2 or any(len(o.answered) == 0 for o in observations)


def _evidence_penalty(missing: dict[str, int] | None, thin: bool, reasons: list[str]) -> float:
    """Risk added when the evidence itself is thin: silent fields, one source."""
    risk = 0.0
    if thin:
        risk += 35
        reasons.append("only one miner answered: no corroboration, so this is a single opinion")
    for name, count in (missing or {}).items():
        if count:
            risk += 10 * min(count, 2)
            reasons.append(f"{count} answering miner(s) returned no {name}: the evidence is thinner than it looks")
    return risk


def _band(risk: float) -> str:
    if risk >= 60:
        return "REJECT"
    if risk >= 30:
        return "REVIEW"
    return "PASS"


# ------------------------------------------------------------------------------ buying
class Desk:
    """Buys the intelligence each workflow needs, from several miners per intent."""

    def __init__(self, client: TelegraphClient, miners_per_intent: int = 3) -> None:
        self.client = client
        self.miners_per_intent = max(1, miners_per_intent)

    def observe(
        self,
        intent: str,
        params: dict[str, Any],
        miners: int | None = None,
        on_event: Callable[[str], None] | None = None,
    ) -> Observation:
        want = self.miners_per_intent if miners is None else max(1, miners)
        obs = Observation(intent=intent, params=params)
        try:
            pool = self.client.miners_for(intent, limit=want)
        except TelegraphError as exc:
            obs.error = f"could not list miners: {exc}"
            return obs
        if not pool:
            obs.error = "no active miner serves this intent"
            return obs

        for miner in pool[:want]:
            try:
                res = self.client.ask(intent, params, miner_id=miner["id"])
            except PaymentRefused as exc:
                obs.error = str(exc)
                break
            except TelegraphError as exc:
                res = AskResult(
                    intent=intent,
                    params=params,
                    miner_id=miner["id"],
                    miner_name=miner["name"],
                    status=0,
                    result=None,
                    receipt=None,
                    price_usd=0.0,
                    rail=None,
                    elapsed_ms=0,
                    error=str(exc),
                )
            obs.samples.append(res)
            obs.cost_usd = round(obs.cost_usd + res.price_usd, 6)
            if on_event:
                state = "ok" if res.ok else f"failed: {res.error}"
                on_event(f"  {intent} -> miner {miner['slug']} ({miner['id']}): {state}")
        return obs


# ------------------------------------------------------------------------------ flows
def listing_check(
    desk: Desk,
    token: str,
    pool: str,
    chain: str,
    trade_usd: float,
    on_event: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    observations = [
        desk.observe("LIQUIDITY_DEPTH_VERIFY_GENERAL", {"pool": pool, "chain": chain}, on_event=on_event),
        desk.observe("TOKEN_HOLDER_COUNT_GENERAL", {"token": token, "chain": chain}, on_event=on_event),
        desk.observe("WASH_TRADING_DETECTION_GENERAL", {"subject": token}, miners=2, on_event=on_event),
    ]
    liquidity = observations[0].field("liquidity_usd")
    holders = observations[1].field("holders_count")
    wash_pct = observations[2].field("wash_volume_pct")
    wash_verdict = observations[2].field("verdict")
    agreement = {
        "liquidity_usd": liquidity.agreement,
        "holders_count": holders.agreement,
        "wash_volume_pct": wash_pct.agreement,
    }
    verdict = score_listing(
        holders=holders.median,
        liquidity_usd=liquidity.median,
        trade_usd=trade_usd,
        wash_pct=wash_pct.median,
        wash_verdict=wash_verdict.mode,
        agreement=agreement,
        missing={
            "liquidity_usd": liquidity.missing,
            "holders_count": holders.missing,
            "wash_volume_pct": wash_pct.missing,
        },
        thin=_thin(observations) or len(liquidity.values) < 2,
    )
    return {
        "workflow": "listing",
        "mission": "Mission 01 Exchange",
        "input": {"token": token, "pool": pool, "chain": chain, "trade_usd": trade_usd},
        "verdict": verdict,
        "observations": [o.as_dict() for o in observations],
        "cost_usd": round(sum(o.cost_usd for o in observations), 6),
        "gaps": [o.error for o in observations if o.error],
    }


def stablecoin_check(
    desk: Desk,
    asset_symbol: str,
    asset_id: str,
    issuer: str,
    on_event: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    observations = [
        desk.observe("CRYPTO_PRICE_USD", {"symbol": asset_symbol}, on_event=on_event),
        desk.observe("ASSET_RESERVE_ATTESTATION_GENERAL", {"asset": asset_id}, on_event=on_event),
        desk.observe("SANCTIONS_SCREENING_MATCH_GENERAL", {"name": issuer}, miners=2, on_event=on_event),
    ]
    price = observations[0].field("price_usd")
    reserve = observations[1].field("attested_reserve")
    sanctioned = observations[2].field("matched")
    agreement = {
        "price_usd": price.agreement,
        "attested_reserve": reserve.agreement,
        "matched": sanctioned.agreement,
    }
    verdict = score_stablecoin(
        price_usd=price.median,
        reserve=reserve.median,
        sanctioned=(str(sanctioned.mode).lower() == "true") if sanctioned.mode is not None else None,
        agreement=agreement,
        missing={
            "price_usd": price.missing,
            "attested_reserve": reserve.missing,
            "sanctions_match": sanctioned.missing,
        },
        thin=_thin(observations) or len(price.values) < 2,
    )
    return {
        "workflow": "stablecoin",
        "mission": "Mission 02 Stablecoin",
        "input": {"symbol": asset_symbol, "asset": asset_id, "issuer": issuer},
        "verdict": verdict,
        "observations": [o.as_dict() for o in observations],
        "cost_usd": round(sum(o.cost_usd for o in observations), 6),
        "gaps": [o.error for o in observations if o.error],
    }


def yield_check(
    desk: Desk,
    project: str,
    symbol: str,
    chain: str,
    on_event: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    observations = [
        desk.observe("CRYPTO_YIELD_RATE_GENERAL", {"project": project, "symbol": symbol, "chain": chain}, on_event=on_event),
        desk.observe("TVL_LOOKUP_GENERAL", {"protocol": project}, on_event=on_event),
    ]
    apy = observations[0].field("supply_apy")
    tvl = observations[1].field("tvl_usd")
    verdict = score_yield(
        apy_bps=apy.median,
        tvl_usd=tvl.median,
        has_yield_data=bool(observations[0].answered),
        agreement={"supply_apy": apy.agreement, "tvl_usd": tvl.agreement},
        missing={"supply_apy": apy.missing, "tvl_usd": tvl.missing},
        thin=_thin(observations) or len(apy.values) < 2,
    )
    return {
        "workflow": "yield",
        "mission": "Mission 13 Asset Management",
        "input": {"project": project, "symbol": symbol, "chain": chain},
        "verdict": verdict,
        "observations": [o.as_dict() for o in observations],
        "cost_usd": round(sum(o.cost_usd for o in observations), 6),
        "gaps": [o.error for o in observations if o.error],
    }


def miners_for(desk: Desk) -> int:
    return desk.miners_per_intent
