"""The claim registry: what a counterparty question decomposes into.

A colony does not ask one big question. It asks a fixed set of small claims, each
of which one Telegraph intent can settle. That mapping is the product's spine: if a
claim has no intent, the colony cannot buy it, and the memo has to say so instead
of inventing an answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Inputs:
    """Everything a question needs to become concrete asks."""

    company: str
    jurisdiction: str = "Denmark"
    domain: str | None = None
    country: str | None = None
    year: int | None = None
    fx_from: str = "USD"
    fx_to: str = "DKK"
    fx_amount: float = 1000.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "domain", self.domain or "")
        object.__setattr__(self, "country", self.country or self.jurisdiction)
        object.__setattr__(self, "year", self.year or 2025)


@dataclass(frozen=True)
class Claim:
    """One question a single intent can settle."""

    id: str
    question: str
    intent: str
    params: dict[str, Any]
    fields: tuple[str, ...]
    load_bearing: bool = False
    priority: int = 50
    notes: str = ""

    def build(self, inputs: Inputs) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in self.params.items():
            if isinstance(value, str) and value.startswith("{"):
                name = value.strip("{}")
                out[key] = getattr(inputs, name)
            elif value == "$company":
                out[key] = inputs.company
            elif value == "$domain":
                out[key] = inputs.domain
            else:
                out[key] = value
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "intent": self.intent,
            "fields": list(self.fields),
            "load_bearing": self.load_bearing,
            "notes": self.notes,
        }


# The seven claims a terms decision actually needs. Order is rough priority.
CLAIMS: tuple[Claim, ...] = (
    Claim(
        id="sanctions",
        question="Is the entity on a sanctions list?",
        intent="SANCTIONS_SCREENING_MATCH_GENERAL",
        params={"name": "$company"},
        fields=("matched", "match_score"),
        load_bearing=True,
        notes="A false negative here is the failure that ends a relationship.",
            priority=10,
),
    Claim(
        id="registry",
        question="Is the legal entity real, active, and correctly named?",
        intent="CORPORATE_REGISTRY_LOOKUP_GENERAL",
        params={"company": "$company", "jurisdiction": "{jurisdiction}"},
        fields=("legal_name", "registration_id", "active"),
        load_bearing=True,
        notes="Registration id is the join key for every other check.",
            priority=20,
),
    Claim(
        id="filings",
        question="Has it filed what it should have filed recently?",
        intent="REGULATORY_FILING_MONITOR_GENERAL",
        params={"entity": "$company", "period": "last 12 months"},
        fields=("filing_count",),
        notes="Different jurisdictions see different filing universes; disagreement is normal here.",
            priority=30,
),
    Claim(
        id="identity",
        question="Does the operating profile match what it claims to be?",
        intent="B2B_IDENTITY_ENRICHMENT_GENERAL",
        params={"company": "$domain"},
        fields=("company", "employee_count", "industry", "headquarters"),
        notes="Empty fields are a finding, not a failure: the swarm says it is blind here.",
            priority=40,
),
    Claim(
        id="news",
        question="Is there adverse coverage in the last period?",
        intent="NEWS_SEARCH_GENERAL",
        params={"query": "$company sanctions investigation"},
        fields=("result_count", "sources"),
            priority=50,
),
    Claim(
        id="macro",
        question="Is the home market stable enough for 60-day terms?",
        intent="MACRO_ECONOMIC_INDICATOR_GENERAL",
        params={"indicator": "unemployment rate", "country": "{country}", "year": "{year}"},
        fields=("rate_pct",),
            priority=60,
),
    Claim(
        id="fx",
        question="What is the settlement risk in the contract currency?",
        intent="CURRENCY_EXCHANGE_CONVERT",
        params={"from_currency": "{fx_from}", "to_currency": "{fx_to}", "amount": "{fx_amount}"},
        fields=("converted_amount",),
            priority=70,
),
)

BY_ID = {claim.id: claim for claim in CLAIMS}


@dataclass
class Plan:
    """Which claims to buy, and in what order, for a given budget."""

    inputs: Inputs
    claims: list[Claim] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"company": self.inputs.company, "claims": [c.as_dict() for c in self.claims]}
