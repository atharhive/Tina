# Missions

Colony is one product with one customer, but the claims it buys come from several
Season II missions. That is deliberate: a credit decision that cannot see the market or
the currency is half a decision.

## Primary: Mission 03 - Institutional Markets

**Question:** is this counterparty safe for 60-day terms?
**Customer:** treasury, credit and vendor-risk teams.
**Claims:** sanctions, registry, filings, identity, news.
**Evidence:** `evidence/colony-maersk-20261121.md`, a live run with 8 paid receipts.

## Supporting claims

| Claim | Mission | Intent |
|---|---|---|
| sanctions | 03 Institutional Markets | `SANCTIONS_SCREENING_MATCH_GENERAL` |
| registry | 03 Institutional Markets | `CORPORATE_REGISTRY_LOOKUP_GENERAL` |
| filings | 03 Institutional Markets | `REGULATORY_FILING_MONITOR_GENERAL` |
| identity | 03 Institutional Markets | `B2B_IDENTITY_ENRICHMENT_GENERAL` |
| news | 03 Institutional Markets | `NEWS_SEARCH_GENERAL` |
| macro | 04 Macro & Rates | `MACRO_ECONOMIC_INDICATOR_GENERAL` |
| fx | 05 FX & Payments | `CURRENCY_EXCHANGE_CONVERT` |

Macro and FX are in the registry because a 60-day term in a foreign currency carries
two risks the counterparty check does not see: the home market and the settlement
currency. Counting them as separate products would have been three half-products.

## Evaluator contributions

`truth/` holds the truth sources that were contributed back to the pool for
`CRYPTO_PRICE_USD` and `CURRENCY_EXCHANGE_CONVERT`, uploaded with
`truth/upload_truth_source.py`. They were verified eligible in the live snapshot
(epoch 16: 99 rows / 7 submitters, 68 rows / 6 submitters).

## What was not built

The v2 workflows - `listing`, `stablecoin`, `yield`, `mining` - are gone. They were four
products with four customers and one shared trick. Their evidence remains in
`evidence/` and their code in git history; the mission mapping for them is in
`docs/ARCHIVE-v2.md`.
