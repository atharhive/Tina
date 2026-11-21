# Troubleshooting

Everything here was hit for real while building this. Error text is the node's, not a
paraphrase.

## "insufficient escrow for delivery: ... balance=0" right after a deposit

The deposit is on chain and `/v1/ledger/account` shows it, but `/engine/v1/ask` reads a
different index. Wait for the node's next epoch instead of depositing twice. Deposits to
the old Diamond (`0x3624EB01...`) do not carry over; the current one is
`0x72a70e949362670Bf8bceAd24eFC5b8f950aa08b`.

## 402 "settlement failure" on every paid ask

Platform-side and intermittent, tracked upstream in bounty issues #214 and #215. Retry
later; the client records a failed fact rather than charging for it.

## A load-bearing claim comes back `dead` every time

`SANCTIONS_SCREENING_MATCH_GENERAL` has one miner that returns
`Missing 'prompt' field` as a 400. Colony escalates the claim to two more miners
automatically; if all three fail, the verdict is HOLD with confidence 0. That is the
correct outcome, not something to work around.

## `matched: false` used to be reported as an empty answer

Fixed on 21 Nov, and it was the worst bug in the release: it turned a clean sanctions
screen into a gap and forced HOLD. `False` and `0` are answers. There is a test named
after this exact mistake.

## A body over 8 MiB returns 500 after payment

`TVL_LOOKUP_GENERAL` and `ASSET_RESERVE_ATTESTATION_GENERAL` both did this. The node
reports 500, the ask is not billed, and Colony records the failure with the price at 0.

## Filings and news disagree between miners

Expected. Different providers see different filing universes and news indices. The memo
shows both sides under a `contested` cluster and does not average them. An average here
would be a number no source said.

## Registry answers but another source cannot find the entity

`CORPORATE_REGISTRY_LOOKUP_GENERAL` answered for Maersk with CVR `22756214`, while other
miners returned nothing. A `single` cluster is the honest label; the memo says
"single source" rather than implying corroboration.

## The bundle says TAMPERED OR INCOMPLETE

Either the JSON was edited after the run, or a cluster has no purchase behind it. Both
are meant to fail: `scripts/verify_bundle.py` recomputes the sha256 over the canonical
payload and checks every cluster against the ledger.

## Wallet loads but every ask is refused

Check the caps. `--max-ask 0.05` refuses anything above five cents, and the default
per-run ceiling is $1.00. The refusal text names the cap that fired.

## Replaying an old run

The v2 evidence in `evidence/*.json` is still resolvable with
`scripts/verify_evidence.py`, which checks each signal hash against the node. The v3
bundles use `scripts/verify_bundle.py` instead, which needs no network at all.
