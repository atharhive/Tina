# Usage

## Install

```bash
git clone https://github.com/atharhive/colony && cd colony
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m pytest tests -q     # offline, no wallet, no spend
```

## A wallet

Colony signs one EIP-191 message per ask, so it needs a key and an escrow balance, not
a gas-funded wallet. It reads `~/.telegraph/wallet.json` or `TELEGRAPH_PRIVATE_KEY`.

```bash
npx -y @telegraphprotocol/telegraph-protocol-mcp setup     # creates the wallet
./.venv/bin/python scripts/fund_testnet.py mint 3          # test USDC, open mint
./.venv/bin/python scripts/fund_testnet.py deposit 2.5     # into the escrow balance
curl -s https://devnode.telegraphprotocol.com/v1/ledger/account/<address>
```

`available` in that last response is what asks may spend. The ledger shows the deposit
immediately; the ask path may not see it until the node's indexer catches up, and Colony
prints the refusal verbatim instead of pretending it paid.

## Buy a decision

```bash
./.venv/bin/python -m colony.cli ask "Is this counterparty safe for 60-day terms?" \
  --company "A.P. Moller-Maersk A/S" --domain maersk.com \
  --jurisdiction Denmark --budget 0.25 \
  --bundle runs/maersk.json
```

What happens, in order:

1. `allocate` picks the seven claims, load-bearing first, until the budget is committed.
2. Each claim gets one ask to the cheapest adequate ranked miner.
3. Facts are clustered into settled / contested / blind / dead.
4. At most two claims get up to two extra scouts: dead load-bearing, or contested.
5. The verdict is computed from the map alone.
6. The memo prints, with footnotes and a receipt table.
7. `--bundle` writes the JSON a third party can verify.

## Flags that matter

| Flag | Default | Why |
|---|---|---|
| `--budget` | 0.25 | total spend for the run |
| `--max-ask` | 0.05 | refuses any single ask above this |
| `--max-run` | 1.00 | hard client-side ceiling for one command |
| `--max-day` | 2.00 | per-UTC-day ceiling |
| `--no-escalate` | off | one ask per claim, no second round |
| `--bundle PATH` | none | write the verifiable JSON |
| `--json` | off | print the bundle to stdout |

## Free commands

```bash
./.venv/bin/python -m colony.cli claims        # the seven claims and their intents
./.venv/bin/python -m colony.cli ledger        # purchases so far, with receipts
./.venv/bin/python scripts/verify_bundle.py evidence/colony-maersk-20261121.json
```

## A book of counterparties

```bash
cat > book.json <<'JSON'
{"companies": [
  {"name": "A.P. Moller-Maersk A/S", "domain": "maersk.com", "jurisdiction": "Denmark"},
  {"name": "Novo Nordisk A/S", "domain": "novonordisk.com", "jurisdiction": "Denmark"}
]}
JSON
./.venv/bin/python -m colony.cli watch --book book.json --budget 0.20
```

Watch spends the budget across the book, coverage only, no escalation. It is the nightly
mode: cheap, wide, and explicit about what it did not buy.

## HTTP

```bash
./.venv/bin/python -m colony.api --port 8088
curl -s localhost:8088/ask -H 'content-type: application/json' \
  -d '{"company":"A.P. Moller-Maersk A/S","budget_usd":0.25}' | jq '.verdict'
```

`budget_usd` above 1.00 is refused at the edge. There is no auth in this release, so bind
to localhost.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | the decision was made (ALLOW, ALLOW WITH CONDITIONS, HOLD) |
| 2 | BLOCK - the decision was made and it is a refusal |
| 3 | payment refused or budget cap hit |
| 4 | network or wallet error |
