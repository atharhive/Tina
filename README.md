# Colony

> A swarm that prices a question before it answers it.

Colony turns one hard question — *"is this counterparty safe for 60-day terms?"* — into
seven small claims, buys the cheapest Telegraph answer that can settle each one, and
prints a decision where **every sentence is either footnoted or absent**.

The default is one ask per claim. Extra scouts are bought only where the map is
contested or a load-bearing claim is unsettled. On a real run that came to **$0.08 for
eight purchases** — near the price of a single answer, not three times it.

---

## Why it looks like this

Telegraph ranks miners, so the network already gives you a good answer at 1x cost.
Buying three answers for every request is a tax, not verification.

Verification is worth paying for in exactly one place: where an extra purchase could
change the decision. So Colony spends the first dollar on **coverage** (one claim at a
time) and the second only on **the claim the verdict hinges on**.

| Run | Claims | Asks | Paid | Cost |
|---|---|---|---|---|
| Maersk, $0.25 budget | 7 | 11 | 8 | **$0.08** |

## The loop

```
plan      → seven claims, most load-bearing first, until the budget is committed
scout     → one claim, one miner, one structured fact, one receipt
map       → settled / contested / blind / dead, per claim
escalate  → 2 extra scouts, max 2 claims: only dead load-bearing or contested ones
verdict   → ALLOW / ALLOW WITH CONDITIONS / HOLD / BLOCK, from the map alone
memo      → footnotes, a receipt table, and a section listing what could not be verified
```

The queen reads the map, never a raw answer, so one confident scout cannot decide
anything on its own.

## What a decision looks like

```
# A.P. Moller-Maersk A/S

**Verdict: HOLD**  ·  confidence 0/100  ·  spent $0.0800 on 8 purchases

- sanctions could not be checked: no usable answer was bought
- registry reports the entity as active

## What the swarm bought

- **registry** (single) — legal_name: A.P. MØLLER - MÆRSK A/S; registration_id: 22756214; active: True [1]
- **sanctions** (dead) — nothing usable came back [2],[10],[11]
- **fx** (single) — converted_amount: 6,801.2739 [4]

## What we could not verify
- sanctions: no usable answer was returned, so nothing is asserted about it.

## Receipts
| # | claim | miner | price | signal |
|---|-------|-------|-------|--------|
| 1 | registry | PREFLIGHT Infrastructure Signals | $0.0100 | `0x36502787c0` |
```

That `HOLD` is the product working: the one claim that matters could not be bought, so
the answer is *do not proceed*, not a confident guess.

## Quickstart

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

# a funded test wallet (see docs/USAGE.md)
./.venv/bin/python -m colony.cli ask "Is this counterparty safe for 60-day terms?" \
  --company "A.P. Moller-Maersk A/S" --domain maersk.com --budget 0.25 \
  --bundle runs/maersk.json
```

Free, no wallet, no spend:

```bash
./.venv/bin/python -m colony.cli claims      # the seven claims and the intents behind them
./.venv/bin/python -m colony.cli ledger      # what has been bought, with receipts
./.venv/bin/python -m pytest tests -q        # 87 tests, offline
```

HTTP, if you want to call it from a treasury system:

```bash
./.venv/bin/python -m colony.api --port 8088
curl -s localhost:8088/ask -H 'content-type: application/json' \
  -d '{"company":"A.P. Moller-Maersk A/S","budget_usd":0.25}' | jq '.verdict, .budget'
```

## What it does not do

- It does not verify claims it could not buy. They appear under "what we could not verify".
- It does not average disagreements. Both sides are shown; neither is chosen.
- It does not run on mainnet, and it makes no claim about production pricing.
- It does not decide for you. `HOLD` means "a human should look", not "guilty".

## Mission

**Season II, Mission 03 — Institutional Markets.** The customer is a treasury or credit
team deciding whether to extend terms to a counterparty; the outcome is a decision they
can attach to a credit file, with the receipts behind it.

Evaluation material for the same intents lives in `truth/` and `evidence/`.

## Layout

```
colony/intents.py    the seven claims and how each maps to an intent
colony/scouts.py     one claim, one ask, one fact
colony/cluster.py    agreement, disagreement, blindness
colony/allocator.py  coverage first, escalation where it pays
colony/queen.py      the loop and the verdict rules
colony/memo.py       the footnoted document and the signed bundle
colony/ledger.py     append-only purchases
colony/policy.py     budget and caps
colony/cli.py        ask, watch, ledger, claims
colony/api.py        POST /ask
demo/index.html      one-page demo
evidence/            real runs, probes, receipts
truth/               evaluation material contributed back to the pool
```

MIT. See [docs/PRODUCT.md](docs/PRODUCT.md) for the customer and the cut list, and
[docs/DECISIONS.md](docs/DECISIONS.md) for why v2 was thrown away.
