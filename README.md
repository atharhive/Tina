# Tina

> Corroborated due diligence, bought one answer at a time on Telegraph.

Tina is a small, auditable desk that **buys the same question from several
independent Telegraph miners** and turns their answers into a decision a human can
check: list the token, review the issuer, or walk away.

One miner's answer is an opinion backed by nobody. Tina's product is the
**agreement**: it pays every miner separately, stores every receipt, and reports
where they disagree. Disagreement is the signal a single-model tool cannot give you.

Testnet only. Real money is never involved: the token is the Sepolia test USDC and
every ask is paid from a Telegraph escrow balance.

---

## What it does

Three workflows, each a different question, each with a numeric verdict:

| Command | Buys | Decision |
|---|---|---|
| `tina listing` | liquidity depth, holder count, wash-trading verdict | list / review / reject a token |
| `tina stablecoin` | spot price, reserve attestation, sanctions screen | peg and counterparty health |
| `tina yield` | supply APY, protocol TVL | is this yield plausible at this size |

Each run prints a risk score out of 100 with its reasons, then writes a memo plus
the raw answers and receipts.

---

## Install

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Fund a test wallet (Sepolia, testnet only)

Tina signs one EIP-191 message per ask, so it needs a key and an escrow balance,
not a gas-funded wallet.

```bash
# 1. A wallet. The Telegraph MCP CLI creates one and prints the address.
npx -y @telegraphprotocol/telegraph-protocol-mcp setup

# 2. Test USDC (the Sepolia test token has an open mint, no faucet queue):
./.venv/bin/python scripts/fund_testnet.py mint 3

# 3. Deposit into the escrow balance of the node's Diamond, then read it back:
./.venv/bin/python scripts/fund_testnet.py deposit 2.5
curl -s https://devnode.telegraphprotocol.com/v1/ledger/account/<your address>
```

`available` in that last response is what asks may spend. The ledger shows a
deposit immediately; the ask path may not see it until the node's next epoch
(3 hours), so Tina reports the refusal verbatim instead of pretending it paid.

## Run

```bash
./.venv/bin/python cli.py quote yield --project aave-v3     # price it, pay nothing
./.venv/bin/python cli.py yield --project aave-v3 --symbol USDC --chain ethereum
./.venv/bin/python cli.py stablecoin --symbol USDC --asset USDC --issuer Circle
./.venv/bin/python cli.py listing --token 0x... --pool 0x... --chain base --size-usd 25000
```

Every paid run:

- prints what each miner charged and whether it answered;
- refuses an ask over `--max-ask`, a run over `--max-run`, a day over `--max-day`;
- writes `runs/<workflow>-<timestamp>.json` (all answers, receipts, prices),
  `runs/<workflow>-<timestamp>.md` (the memo) and a small `.verdict.json`.

Exit codes: `0` pass/review, `2` reject, `3` payment refused, `4` network or
wallet error. A reject is a successful run.

## Evidence a reviewer can check

```
runs/yield-20261119T093012Z.md             memo: verdict, reasons, cost, receipts
runs/yield-20261119T093012Z.json           every ask: miner id, params, result, receipt
runs/yield-20261119T093012Z.verdict.json   the decision alone
```

Each ask in the JSON carries its `result`, the `price_usd` actually charged and the
node's `X-PAYMENT-RESPONSE` receipt, so every claim in the memo traces to a paid
call. `~/.tina/spend.json` holds the per-UTC-day spend the caps enforce.

`evidence/` in this repo holds three real runs committed as they were produced:
one per workflow, with their receipts and signal hashes. Nothing in them was
edited after the run.

## Cost per outcome

One ask costs $0.01 on this node. A workflow buys 2-3 intents across 2-3 miners:

- `yield`: 2 intents x 3 miners = 6 asks = **$0.06** per decision
- `stablecoin`: 3 intents x 2-3 miners = **$0.06-$0.09**
- `listing`: 3 intents x 2-3 miners = **$0.08-$0.10**

A failed ask is never billed, so the printed cost is what the node charged.

## Failure handling

- **A miner fails:** the answer is recorded as failed, the workflow continues, and
  the memo lists the gap. Two good answers are still a result; one is not, and the
  memo says so.
- **Escrow refuses:** the run stops before spending anything else and prints the
  node's exact reason.
- **Miners disagree:** disagreement adds risk instead of being averaged away.
- **Nothing answers:** the verdict cannot be PASS. Missing data is never good news.

## What Tina does not do

- It does not claim settlement. It reports the receipt the node returned.
- It does not treat agreement as truth. Several miners can share one bad source;
  agreement measures consistency, not correctness.
- It does not run on mainnet and makes no claim about production pricing.
- It does not hide the escrow indexing delay: every run that hit it says so, in the
  evidence, with the node's own error text.

## Evaluation material

`truth/` holds the truth sources Tina's own workflows depend on, uploaded to the
evaluation pool instead of kept private:

- `truth-coinbase-spot.yaml` - `CRYPTO_PRICE_USD` from Coinbase's keyless rates API
- `truth-frankfurter-ecb.yaml` - `CURRENCY_EXCHANGE_CONVERT` from ECB reference rates

```bash
./.venv/bin/python truth/upload_truth_source.py truth/truth-coinbase-spot.yaml CRYPTO_PRICE_USD
```

## Tests

```bash
./.venv/bin/python -m pytest tests -q
```

14 tests, no network, no wallet, no spend: scoring thresholds, agreement counting,
memo contents, and the failure path where one miner dies mid-run.

## Layout

```
cli.py                   argument parsing and exit codes
core/client.py           node client: escrow payment, caps, receipts
core/flows.py            the three workflows and their pure scoring rules
core/report.py           run evidence and memos
core/wallet.py           key loading, never logged
scripts/fund_testnet.py  test USDC mint and escrow deposit
truth/                   truth sources, and the signed uploader
tests/                   unit tests
```

## What the network did in these runs (19 Nov 2026, devnode)

Recorded from the committed evidence, not editorialised:

- **Escrow rail works.** 20 paid asks across the three runs settled from escrow, each
  with a `receipt_hash` and a `signal_hash` in the run JSON.
- **A fresh deposit is invisible to `/engine/v1/ask` for a while.** After funding,
  `/v1/ledger/account` shows the balance immediately but asks return
  `insufficient escrow for delivery: ... balance=0`; it clears once the node's
  indexer catches up. Tina surfaces that refusal verbatim.
- **`CRYPTO_YIELD_RATE_GENERAL` is thinly supplied.** Of 5 miners asked, 1 returned
  `supply_apy`; two others answered with unrelated payloads. The yield workflow
  therefore returns REVIEW, not PASS: one reading is not corroboration.
- **Two miners return upstream bodies over the 8 MiB limit** (`TVL_LOOKUP_GENERAL`
  and `ASSET_RESERVE_ATTESTATION_GENERAL`), which the node reports as a 500 after
  payment. They were not billed.
- **One miner answers a judgment intent with a 400** (`SANCTIONS_SCREENING_MATCH`:
  `Missing 'prompt' field`), so that intent had a single source in the run.

## Missions

- **01 Exchange** - `tina listing`
- **02 Stablecoin** - `tina stablecoin`
- **13 Asset Management** - `tina yield`

MIT. See [LICENSE](LICENSE).
