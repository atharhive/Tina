"""Claim registry tests: templates resolve, and a missing input fails loudly."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from colony.intents import BY_ID, CLAIMS, Inputs  # noqa: E402


def test_registry_has_seven_claims_with_two_load_bearing():
    assert len(CLAIMS) == 7
    assert [c.id for c in CLAIMS if c.load_bearing] == ["sanctions", "registry"]


def test_sanctions_claim_resolves_the_company():
    claim = BY_ID["sanctions"]
    assert claim.build(Inputs(company="Acme A/S")) == {"name": "Acme A/S"}


def test_registry_claim_fills_jurisdiction():
    claim = BY_ID["registry"]
    params = claim.build(Inputs(company="Acme A/S", jurisdiction="Denmark"))
    assert params == {"company": "Acme A/S", "jurisdiction": "Denmark"}


def test_fx_claim_uses_defaults_and_overrides():
    claim = BY_ID["fx"]
    default = claim.build(Inputs(company="Acme"))
    assert default["from_currency"] == "USD" and default["to_currency"] == "DKK"
    custom = claim.build(Inputs(company="Acme", fx_from="EUR", fx_to="SEK", fx_amount=500))
    assert custom == {"from_currency": "EUR", "to_currency": "SEK", "amount": 500}


def test_macro_defaults_country_to_jurisdiction():
    inputs = Inputs(company="Acme", jurisdiction="Norway")
    assert BY_ID["macro"].build(inputs)["country"] == "Norway"


def test_identity_claim_uses_the_domain_not_the_name():
    params = BY_ID["identity"].build(Inputs(company="Acme A/S", domain="acme.com"))
    assert params == {"company": "acme.com"}


def test_a_missing_placeholder_fails_loudly():
    from colony.intents import Claim

    broken = Claim(id="x", question="q", intent="I", params={"company": "{nope}"}, fields=("a",))
    with pytest.raises(AttributeError):
        broken.build(Inputs(company="Acme"))
