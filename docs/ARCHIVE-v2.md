# Archive: v2 (Tina)

v2 is gone from the codebase and lives in git history before commit `d7bc3dc`. This page
exists so the evidence in `evidence/` still makes sense.

## What v2 did

Four fixed workflows, each buying the same intent from three miners and scoring their
agreement:

| Workflow | Mission | Intents |
|---|---|---|
| `listing` | 01 Exchange | `LIQUIDITY_DEPTH_VERIFY_GENERAL`, `TOKEN_HOLDER_COUNT_GENERAL`, `WASH_TRADING_DETECTION_GENERAL` |
| `stablecoin` | 02 Stablecoin | `CRYPTO_PRICE_USD`, `ASSET_RESERVE_ATTESTATION_GENERAL`, `SANCTIONS_SCREENING_MATCH_GENERAL` |
| `yield` | 13 Asset Management | `CRYPTO_YIELD_RATE_GENERAL`, `TVL_LOOKUP_GENERAL` |
| `mining` | 12 Mining & Power | grid power price, `BITCOIN_HASHRATE` |

## Why it was retired

Every workflow bought three answers to one question. That is three times the cost for a
consistency score, on a network whose ranking layer already exists to pick the best
provider. The founder's critique was correct and the fix was structural, not cosmetic.

## Results worth keeping

- **listing**, 19 Nov: 8 asks, 6 answered, $0.06. WETH/USDC Base liquidity
  $24,873,363.78 from all three miners, holders 5,245,995. Verdict PASS.
- **stablecoin**, 19 Nov: peg and reserve checks, sanctions single-sourced due to a
  miner returning 400. Verdict REVIEW.
- **yield**, 19 Nov: 5 miners asked, 1 returned `supply_apy`. Verdict REVIEW, because one
  reading is not corroboration. This run is the reason v3 distinguishes `single` from
  `settled`.
- **mining**, 19 Nov: CAISO NP15 at $55.84/MWh, 1 PH at 25 J/TH, margin $14.38/day,
  break-even $79.81/MWh. Also exposed the zone-mismatch bug: a European day-ahead price
  was being scored against a California zone.

## What survived into v3

`client.py` (escrow signing, payment challenges, receipts, caps) and `wallet.py` were
carried over unchanged, because the network-facing part was never the problem. The
scoring, workflows and report writer were replaced by claims, scouts, clusters and the
memo.
