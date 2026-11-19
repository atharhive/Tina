# Troubleshooting

Every entry here is something Tina hit on the devnode between 19 and 20 November
2026, with the exact error text. If you paste a failure into an issue, include the
error string: these are distinguishable, and they have different fixes.

## `insufficient escrow for delivery: unbilled=0 μUSDC + price=10000 μUSDC > balance=0 μUSDC`

You just funded escrow and the node still says zero.

Check the ledger first:

```bash
curl -s https://devnode.telegraphprotocol.com/v1/ledger/account/<address> | \
  python3 -m json.tool | grep -E 'available|deposited|balance'
```

If `available` is non-zero, the deposit landed and the ask path is behind. On the
devnode a fresh deposit stayed invisible to `/engine/v1/ask` for roughly half an
hour while the ledger already showed it; asks succeed afterwards with no change on
your side. Retry, and do not deposit twice.

If `available` is still zero, the deposit went to the wrong Diamond. `/v1/ask`
settles to `0x72a70e949362670Bf8bceAd24eFC5b8f950aa08b`. Balances deposited to the
older `0x3624EB012B5E998BB57B6bE6C9Cfc9c4bc5eb99b` do not carry over.

## `settlement failed: settle request failed: ... context deadline exceeded`

That is the x402 `exact` rail, and it is the facilitator, not your signature. Both
Base Sepolia and Ethereum Sepolia were failing this way for every caller. Use the
`escrow` scheme instead: same envelope, `scheme: "escrow"`, no facilitator. Tina
only ever pays from escrow for exactly this reason.

## `403 Error 1010: Access denied` from Cloudflare

Your HTTP client's User-Agent is banned. Python's default `Python-urllib/3.x` is
refused outright. Send a real one:

```python
headers={"User-Agent": "tina/2.0 (+https://github.com/atharhive/Tina)"}
```

## `upstream call failed: response body exceeds 8388608 byte limit`

The miner's upstream returned more than 8 MiB. The node reports it as HTTP 500
after payment, and escrow is not billed. Nothing to fix on your side; pick another
miner for that intent. It was consistently `TVL_LOOKUP_GENERAL` and
`ASSET_RESERVE_ATTESTATION_GENERAL` on the devnode.

## `no_compatible_miner: no request built for a miner serving <INTENT> carries the resolved input`

The node could not build a request for the miner it picked: the miner's declared
parameters do not accept the input. Free failure, no charge. Retry, or use another
miner for that intent. `tina miners <INTENT>` shows who is available.

## A miner answers 200 but the field you asked for is missing

The answer is off-schema (for example a chain list returned for
`CRYPTO_YIELD_RATE_GENERAL`, which asks for `supply_apy`). Tina records the field as
missing and adds risk; it does not fall back to a guess. If this happens on every
miner for an intent, the intent is unscoreable in practice and the verdict is
REVIEW, not PASS.

## `signal not found`

`/engine/v1/signal/<hash>` only serves hashes the node still holds. Signals from
older runs can be dropped. A hash that resolved when the run was made can 404
later, so check the hash at the time you rely on it:

```bash
./.venv/bin/python cli.py signal <hash>
```

## `tina` exits 3 and prints `payment refused`

Nothing was charged. Read the reason on the line: a per-ask, per-run or per-day cap
(`--max-ask`, `--max-run`, `--max-day`) refused before signing, or the node refused
the payment. `tina spend` shows what the caps have actually been charged.

## Tests fail with `ModuleNotFoundError: eth_account`

The venv is not active. Use the interpreter directly:

```bash
./.venv/bin/python -m pytest tests -q
```
