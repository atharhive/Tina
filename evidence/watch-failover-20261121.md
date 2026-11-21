# Watch mode, before and after failover

Two runs of the same command over the same book, 21 Nov 2026, devnode, escrow rail.

```
colony watch --book book.json --budget 0.12
```

## Before failover (17:44 UTC)

| Company | Verdict | Spent |
|---|---|---|
| A.P. Moller-Maersk A/S | HOLD | $0.04 |
| Novo Nordisk A/S | HOLD | $0.04 |

Both held for the same reason: `kimutai-sanctions-screener` was the top-ranked miner for
`SANCTIONS_SCREENING_MATCH_GENERAL` and returned a 400 (`Missing 'prompt' field`). In
coverage-only mode there is no second round, so a broken provider was indistinguishable
from a bad counterparty, and the whole book read as risky.

## After failover (17:55 UTC)

| Company | Verdict | Spent |
|---|---|---|
| A.P. Moller-Maersk A/S | ALLOW WITH CONDITIONS | $0.05 |
| Novo Nordisk A/S | ALLOW WITH CONDITIONS | $0.05 |

The same broken miner was tried first, failed, and the scout moved to the next ranked
provider, which answered `ChainSight` for $0.01. Five paid asks per company.

```
17:54:54  sanctions  ChainSight  $0.01  ok
17:54:59  registry   PREFLIGHT   $0.01  ok
17:55:02  filings    PREFLIGHT   $0.01  ok
17:55:05  identity   Brandfetch  $0.01  ok
17:55:23  news       ChainSight  $0.01  ok
```

ALLOW WITH CONDITIONS rather than ALLOW is correct: registry, filings and identity are
each single-sourced in a coverage-only run, and the memo says so.

## The rule this pins

A failure is a provider problem, not a money problem. The failed ask is not billed, so
trying the next ranked miner costs nothing and is the difference between a dead claim and
an answered one. A refused payment is different: it stops the claim immediately, because
asking somebody else will not fix an empty escrow.

Both behaviours are pinned in `tests/test_scout_failover.py`.
