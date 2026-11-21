# Evidence index

For a reviewer who has five minutes. Everything here is committed and reproducible.

## The run

| Artifact | What it proves |
|---|---|
| `evidence/colony-maersk-20261121.md` | the memo as printed: verdict HOLD, reasons, footnotes, receipt table |
| `evidence/colony-maersk-20261121.json` | every fact, every receipt, the cluster map, the budget, and a sha256 |

Verify it yourself, offline:

```
python scripts/verify_bundle.py evidence/colony-maersk-20261121.json
```

Expected output:

```
ok  hash ok: cee82b5a8e9e4e4b
ok  ledger: 11 entries cover 7 claims
ok  receipts: 8 present, 3 asks failed
VERIFIED
```

Now change one fact in the JSON and run it again. It prints TAMPERED. That is the whole
argument for the product in two commands.

## The domain probe

`evidence/domain-probe-20261120.summary.json` is the 16-ask probe that decided the
mission: registry, sanctions, macro and FX answered; identity enrichment returned empty
fields; filings and news disagreed between sources. The disagreement is why the product
has a `contested` state instead of an average.

## The v2 evidence

`evidence/listing-*`, `stablecoin-*`, `yield-*`, `mining-*` are the earlier workflows,
kept because they are real runs with real receipts. They are explained in
`docs/ARCHIVE-v2.md`. Their signal hashes still resolve with
`scripts/verify_evidence.py`.

## The tests

```
python -m pytest tests -q      # 46 passed, offline, no wallet, no network
```

The three tests worth reading: `test_scouts_cluster.py` pins that `false` and `0` are
answers rather than blanks; `test_allocator_policy.py` pins that a single-sourced
secondary claim is not escalated; `test_queen_memo.py` pins that an unchecked load-bearing
claim produces HOLD, never ALLOW.
