# Usage, with real output

These transcripts are from the devnode on 19 November 2026, with the wallet address
shortened. Nothing here is edited except the trimming marked `...`.

## Look before you spend

```console
$ ./.venv/bin/python cli.py health yield
wallet 0xb2b7...2147
node   https://devnode.telegraphprotocol.com
CRYPTO_YIELD_RATE_GENERAL              ranked=23/26  price=0.01-0.01 fields=[supply_apy]
TVL_LOOKUP_GENERAL                     ranked=21/21  price=0.01-0.01 fields=[protocol_or_chain, tvl_usd, chain_tvl_usd, as_of]
```

`ranked=23/26` means 26 miners are registered for the intent but 23 have a ranking,
and only ranked miners get routed. `tina miners` lists them individually:

```console
$ ./.venv/bin/python cli.py miners CRYPTO_YIELD_RATE_GENERAL --limit 4
 rank        id  slug                                price  requests
    3    141008  cyield-llama-chain                 0.0100  4
    5    795372  zk-yield-core                      0.0100  4
    5    141009  cyield-stable                      0.0100  0
    6    141002  cyield-llama-eth                   0.0100  1
```

## Price a run

```console
$ ./.venv/bin/python cli.py quote listing --token 0x4200...0006 --pool 0xd0b5...f224 --chain base
LIQUIDITY_DEPTH_VERIFY_GENERAL         $0.01/ask x 3 miners  escrow=True
TOKEN_HOLDER_COUNT_GENERAL             $0.01/ask x 3 miners  escrow=True
WASH_TRADING_DETECTION_GENERAL         $0.01/ask x 3 miners  escrow=True

projected cost for this run: $0.0900 USDC
```

`quote` fetches the payment challenge and never signs it.

## Run a listing check

```console
$ ./.venv/bin/python cli.py listing --token 0x4200...0006 --pool 0xd0b5...f224 --chain base --size-usd 25000
wallet 0xb2b7...2147
node   https://devnode.telegraphprotocol.com
  LIQUIDITY_DEPTH_VERIFY_GENERAL -> miner verifywire-liquidity-depth (7373): ok
  LIQUIDITY_DEPTH_VERIFY_GENERAL -> miner zk-liq-verified (77081): ok
  LIQUIDITY_DEPTH_VERIFY_GENERAL -> miner txlens (9002): ok
  TOKEN_HOLDER_COUNT_GENERAL -> miner chainsight-oracle (302): failed: HTTP 503 from /engine/v1/ask/302: {"error":"could not route this question now, try again later"}
  TOKEN_HOLDER_COUNT_GENERAL -> miner chainwire-holder-count (7302): ok
  TOKEN_HOLDER_COUNT_GENERAL -> miner zk-holders-fresh (73606): ok
  WASH_TRADING_DETECTION_GENERAL -> miner verifywire-wash-trading (7378): failed: HTTP 500 after payment: upstream call failed: status 502: evidence_unavailable
  WASH_TRADING_DETECTION_GENERAL -> miner wash-dex-pair (80003): ok

verdict : PASS (risk 15.0/100)
  - 1 answering miner(s) returned no wash_volume_pct: the evidence is thinner than it looks
  - wash-trading share not reported
cost    : $0.0600 USDC
evidence: runs/listing-20261119T071626Z.md
run     : runs/listing-20261119T071626Z.json
```

Three miners agreed on liquidity to the cent (`$24,873,363.78` twice, `$24,873,355`
once), so that number is corroborated. The wash-trading share was not reported by
one miner and therefore is not claimed: the risk score goes up instead of the answer
being invented.

## Check the evidence

```console
$ ./.venv/bin/python scripts/verify_evidence.py evidence/listing-20261119T071626Z.json
intent                                 miner                   amount  result
LIQUIDITY_DEPTH_VERIFY_GENERAL         verifywire-liquidity-d    0.01  ok
LIQUIDITY_DEPTH_VERIFY_GENERAL         zk-liq-verified           0.01  ok
LIQUIDITY_DEPTH_VERIFY_GENERAL         txlens                    0.01  ok
TOKEN_HOLDER_COUNT_GENERAL             chainwire-holder-count    0.01  ok
TOKEN_HOLDER_COUNT_GENERAL             zk-holders-fresh          0.01  ok
WASH_TRADING_DETECTION_GENERAL         wash-dex-pair             0.01  ok

6 signals checked, 0 mismatched, 0 answers with no signal hash
```

Each row is a hash the node itself resolves to a payer, a miner and an intent.

## Check one signal by hand

```console
$ ./.venv/bin/python cli.py signal 0x8e60...ca0d
signal_hash     0x8e605b822bddf31dcf029472a7ca60b56d7ddf61e8b0ad3d66d1e3621dd0ca0d
kind            direct_result
wallet_address  0xb2b73753bc5396f5ebb34b0ea099abccfc6f2147
miner_slug      zk-yield-core
intent_id       CRYPTO_YIELD_RATE_GENERAL
created_at      2026-11-19T07:12:00.107516Z
```

## What the caps have charged

```console
$ ./.venv/bin/python cli.py spend
2026-11-19  $0.4000
today  $0.4000 of $1.00 daily cap
```

## Replay a memo

```console
$ ./.venv/bin/python cli.py replay evidence/yield-20261119T071831Z.json --write
memo written to evidence/yield-20261119T071831Z.replayed.md
replay: REVIEW (risk 45.0/100), cost $0.0400, 2 intents
```

Replay reads the saved run and re-renders the memo. It buys nothing and cannot
change a verdict that was already recorded.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | the run finished: PASS or REVIEW |
| 2 | the run finished: REJECT (a successful run with a negative answer) |
| 3 | payment refused, nothing charged |
| 4 | network, wallet or node error |
