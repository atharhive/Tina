# Missions and how each one is met

Season II judges a mission on whether a reviewer can **run it** with a new input,
**check** the result, **inspect** the real Telegraph request and its accounting,
**break it** with a reasonable failure case, and **reproduce it**. This page maps
that to what is in this repository.

| Workflow | Mission | Intents bought |
|---|---|---|
| `tina listing` | 01 Exchange | `LIQUIDITY_DEPTH_VERIFY_GENERAL`, `TOKEN_HOLDER_COUNT_GENERAL`, `WASH_TRADING_DETECTION_GENERAL` |
| `tina stablecoin` | 02 Stablecoin | `CRYPTO_PRICE_USD`, `ASSET_RESERVE_ATTESTATION_GENERAL`, `SANCTIONS_SCREENING_MATCH_GENERAL` |
| `tina yield` | 13 Asset Management | `CRYPTO_YIELD_RATE_GENERAL`, `TVL_LOOKUP_GENERAL` |

Each workflow is its own command, its own scoring rule, its own failure mode and its
own committed evidence, so three missions here are three working results rather than
one action with three labels.

## Mission 01 - Exchange

A listing desk has to answer "would this market hurt us if we listed it" with
evidence, not vibes.

- **Run it:** `tina listing --token <erc20> --pool <address> --chain <chain> --size-usd <n>`
- **Check it:** risk score out of 100 plus the reasons; `PASS` under 30, `REJECT` at 60.
  Liquidity is compared to the order size, holders to a distribution floor, wash share
  to a threshold.
- **Inspect it:** every ask carries `cost_usd`, `receipt_hash` and `signal_hash`.
  `scripts/verify_evidence.py` resolves each hash back to the node.
- **Break it:** pass a token with no holders data, or a pool with no route. The run
  records the failure, the verdict cannot be PASS on one source.
- **Reproduce it:** `pytest tests -q`, then the same command with your own token.

Evidence: `evidence/listing-20261119T071626Z.*`

## Mission 02 - Stablecoin

A treasury team holding a stablecoin needs peg health and counterparty risk in one
answer, and needs to know when either is unmeasured.

- **Run it:** `tina stablecoin --symbol USDC --asset USDC --issuer Circle`
- **Check it:** peg deviation in basis points, reserve attestation presence, sanctions
  match. A sanctions hit is fatal regardless of everything else.
- **Inspect it:** receipts and signal hashes per intent, as above.
- **Break it:** ask about an asset with no attestation; the verdict says the reserve is
  unmeasured instead of assuming it is fine.
- **Reproduce it:** swap `--symbol` / `--issuer` for another issuer.

Evidence: `evidence/stablecoin-20261119T071634Z.*`

## Mission 13 - Asset Management

A yield desk needs to know whether an advertised APY is plausible at the size it wants
to deploy, and the answer depends on two different intents agreeing.

- **Run it:** `tina yield --project aave-v3 --symbol USDC --chain ethereum`
- **Check it:** supply APY in basis points against a plausibility band, TVL against a
  size floor.
- **Inspect it:** as above.
- **Break it:** ask for a protocol whose APY no miner returns. Only one miner supplied
  `supply_apy` on the devnode, so this workflow deliberately returns `REVIEW`: one
  reading is a single opinion, and the memo says exactly that.
- **Reproduce it:** the same command; the run JSON keeps the failed asks with the
  node's own error text.

Evidence: `evidence/yield-20261119T071831Z.*`

## What is deliberately not claimed

- No mainnet usage, no production pricing, no claims about volumes Tina has not seen.
- No claim that agreement equals correctness. Three miners can share one upstream.
- No claim that a `PASS` means an asset is safe; it means the bought evidence did not
  cross a threshold.
- The devnode was still indexing fresh escrow deposits while these runs were made;
  the affected runs say so with the node's error text rather than being retried until
  they looked clean.
