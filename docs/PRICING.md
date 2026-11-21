# Pricing

## Measured cost, not modelled cost

Every number here comes from a committed bundle in `evidence/`, priced at what the node
actually billed. A failed ask is not billed, so the totals are real.

| Decision | Claims bought | Asks | Paid | Cost |
|---|---|---|---|---|
| Counterparty terms (full) | 7 | 11 | 8 | **$0.08** |
| Counterparty terms (no escalation) | 7 | 7 | 6 | **$0.06** |
| Single claim spot check | 1 | 1-3 | 1-3 | **$0.01-0.03** |

The escalation premium is capped: at most two claims, at most two extra scouts each, so
the worst case is 7 + 4 = 11 asks. There is no path in this codebase that quietly becomes
21 asks.

## What a customer would pay

- **Per decision:** $2 for a full counterparty memo. That is a 25x gross margin on a
  measured $0.08 cost, and it undercuts a $40/seat report by an order of magnitude.
- **Standing book:** $150/month for up to 100 counterparties, nightly, with a capped
  budget of $1/night. The cap is the product: a customer should never be surprised by a
  swarm that got curious.
- **API:** $0.02 per claim returned, so a customer building their own memo pays for facts
  rather than for our prose.

## Why this is defensible at 1x

If the answer were free, verification would be pointless. It is not free: a wrong
sanctions screen costs a relationship, and a vendor report costs $40. Colony's margin
comes from buying facts cheaper than the customer can buy a report, not from reselling
three answers as one.

## Costs we deliberately do not hide

- The network bills $0.01 per ask on this node. If that becomes $0.03, the full decision
  becomes $0.24 and the $2 price still holds.
- Escalation is the only unbounded-looking variable, so it is capped in code and printed
  in every memo.
- A dead load-bearing claim can burn up to 3 asks and still return HOLD. That is the
  correct outcome, and it is still cheaper than a wrong ALLOW.
