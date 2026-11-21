# Product

## Customer

A treasury, credit or vendor-risk team at a company that sells on terms. They approve
or refuse counterparties weekly. Today the work is: a PDF report, a sanctions check
someone runs by hand, and a judgement call that is never written down.

## Job

**Before we extend 60-day terms, decide allow / hold / block, with evidence that
survives an audit.**

## Outcome they pay for

1. A decision they can attach to the credit file, with a receipt per claim.
2. An explicit list of what could not be verified, so the residual risk is visible
   rather than implied.
3. A cost per decision low enough to run on every counterparty, not just the big ones.

## What changed from v2

v2 bought the same question from three miners every time. That is 3× the cost for a
service Telegraph already provides through ranking, and the founder was right to call
it commercially weak. v3 keeps independent verification, but makes it an exception with
a trigger rather than the default:

- **Coverage first:** one ask per claim, cheapest adequate miner.
- **Escalation last:** at most two claims get extra scouts, and only if they are
  contested, or load-bearing and unsettled.
- **Measured:** every run reports purchases, spend and the escalation list, so the
  claim "near 1× cost" is checkable rather than asserted.

## The cut list for this release

In: seven claims, budgeted buying, contested/blind handling, footnoted memo, signed
bundle, append-only ledger, CLI, one HTTP endpoint, one demo page, 87 tests.

Out: accounts, auth, multi-tenant storage, PDF ingestion, dashboards, mainnet, a queue,
retries across restarts, and any claim type beyond the seven.

## Success criteria

- A stranger can run one decision for under 30 cents and verify every receipt.
- Every verdict can be traced to the cluster map, and every map cell to a purchase.
- A run that cannot buy a load-bearing claim returns HOLD, never ALLOW.
- Cost per decision stays within 15% of the number of claims (i.e. ~1.1×, not 3×).
