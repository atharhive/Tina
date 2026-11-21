# Season II submission pack

Everything below is ready to paste into the official form. Every number comes from a
committed artifact: the run in `evidence/colony-maersk-20261121.md`, the probe in
`evidence/domain-probe-20261120.summary.json`, or the test suite.

---

## Entry 1 - Apps & Agents

**Project name:** Colony
**Track:** Apps & Agents
**Mission:** 03 Institutional Markets
**GitHub username that starred the bounties repo:** `atharhive`
**Repository:** https://github.com/atharhive/colony

### Short public summary

Colony answers one commercial question - *is this counterparty safe for 60-day payment
terms?* - by decomposing it into seven small claims, buying the cheapest Telegraph
answer that can settle each one, and printing a decision where every sentence is either
footnoted or absent.

The default is one ask per claim. Extra scouts are bought only where two sources already
disagree, or where a load-bearing claim came back dead. On the live run in `evidence/`
that was 11 asks, 8 paid, **$0.08** for a seven-claim decision - close to the price of a
single answer rather than three times it. That is the direct answer to the critique that
multi-buying is commercially weak: verification is now an exception with a trigger,
priced and printed in every memo.

The output is a markdown memo (footnotes, receipt table, a section listing exactly what
could not be verified) plus a JSON bundle with a sha256 that a third party can recompute.
`scripts/verify_bundle.py` does that offline, and will report TAMPERED if a fact, a
receipt or a budget total was edited after the run.

Links: [repository](https://github.com/atharhive/colony) -
[usage](https://github.com/atharhive/colony/blob/main/docs/USAGE.md) -
[pricing](https://github.com/atharhive/colony/blob/main/docs/PRICING.md) -
[decisions](https://github.com/atharhive/colony/blob/main/docs/DECISIONS.md)

### The five commercial questions

**1. Who is it for?**
Treasury, credit and vendor-risk teams at companies that sell on terms - the people who
approve or refuse counterparties weekly and have to defend the decision later. Their
current tools are a $40/seat report, a manual sanctions check and a judgement call that
never gets written down.

**2. What does it improve?**
Two things. Cost: a decision costs $0.08 measured, against a report they buy today.
Auditability: every claim carries a price, a receipt hash and a signal hash, and every
gap is printed instead of smoothed. A single-model tool will happily write "no sanctions
concerns" from memory; Colony cannot say that unless a receipt says it.

**3. What does it do today?**
One command, seven claims, from a live run on 21 Nov against the devnode:

- registry: legal entity **A.P. MØLLER - MÆRSK A/S**, registration **22756214**, active,
  returned by PREFLIGHT Infrastructure Signals for $0.01
- sanctions: one miner returned a 400 (`Missing 'prompt' field`), so the claim was
  escalated to two more; both answered, verdict **HOLD** rather than a fabricated ALLOW
- filings: an answer of **0 filings**, which the first version wrongly treated as a blank
  and is now pinned by a test
- identity, macro (Denmark, 5.529%), news (4 sources), fx (USD 1000 -> DKK 6,801.2739)

11 asks, 8 paid, **$0.08 spent of a $0.25 budget**, 8 receipts, bundle hash verified.
The `HOLD` is the product working: the claim that matters could not be bought, so it
refuses to proceed.

**4. Why would someone adopt it?**
Because a credit file needs a decision with evidence, and this produces the evidence as
a side effect of the decision. It is also cheap enough to run on every counterparty
rather than the top twenty. Before production it needs: mainnet pricing, a cache so that
repeated deterministic claims are not re-bought, and more miners for the thinly supplied
sanctions intent.

**5. How can someone try it?**
`git clone`, a venv, `scripts/fund_testnet.py mint 3`, `deposit 2.5`, then
`python3 -m colony.cli ask "Is this counterparty safe for 60-day terms?" --company "A.P. Moller-Maersk A/S" --budget 0.25`.
Free paths that spend nothing: `colony claims`, `colony ledger`,
`scripts/verify_bundle.py evidence/colony-maersk-20261121.json`, and `pytest tests -q`.
Maintained by @atharhive.

### Demo video

`docs/demo/colony-demo.mp4`, narrated, rendered from the committed run rather than a live
capture. Raw link for the form:
`https://github.com/atharhive/colony/raw/main/docs/demo/colony-demo.mp4`

### Demo script

1. **The question (20s).** A credit team has to say yes or no to 60-day terms today.
2. **The cost objection (30s).** Three answers to one question is 3x the price for a
   consistency score. Watch the allocator buy one ask per claim instead.
3. **The run (60s).** Seven claims, load-bearing first, $0.08. Point at the registry
   answer with its registration number, then at the sanctions claim that failed three
   times.
4. **The refusal (30s).** The verdict is HOLD with confidence 0, and the memo names the
   gap. This is the part a sales deck would hide.
5. **The proof (40s).** `verify_bundle.py` recomputes the hash, counts the receipts,
   checks the budget, and says VERIFIED. Then edit one fact and watch it say TAMPERED.
6. **Why now (20s).** Ranked miners make a fact cheap. The unit of work becomes the
   eight facts behind a decision, not the report.

### Showcase permission

Terminal output, memos, bundles and the demo may be shared publicly. No customer data is
involved. Buyer introductions: yes.

---

## Entry 2 - Evaluators

**Track:** Evaluators
**Contributor address:** `0xb2b73753BC5396f5EbB34b0ea099ABCCFc6F2147`

| Intent | Material | State |
|---|---|---|
| `CONTENT_MODERATION_GENERAL` | 20 preference rows | eligible |
| `KEYWORD_EXTRACTION_GENERAL` | 6 rows | eligible (pool under quorum) |
| `GRAMMAR_SPELL_CHECK_GENERAL` | 6 rows | eligible (pool under quorum) |
| `CRYPTO_PRICE_USD` | Coinbase truth source | admitted, snapshot epoch 16 |
| `CURRENCY_EXCHANGE_CONVERT` | ECB truth source | admitted, snapshot epoch 16 |

The two truth sources are the substantive contribution: a deterministic intent cannot be
scored until someone describes a public API that answers it.

- `truth/truth-coinbase-spot.yaml` - Coinbase keyless rates, `data.rates.USD` as `price_usd`
- `truth/truth-frankfurter-ecb.yaml` - ECB reference rates, `rates.{to}` as `converted_amount`

Both are also intents Colony itself buys, so the evaluation material and the application
reinforce each other.

---

## Before submitting - checklist

- [ ] Star [telegraphprotocol/bounties](https://github.com/telegraphprotocol/bounties)
- [ ] Pick the track on the form for each entry (the form is per entry)
- [ ] Paste the summary and the five answers
- [ ] Attach the evidence links (`evidence/`, `docs/USAGE.md`, verify output)
- [ ] Set showcase permission and buyer-introduction preference
- [ ] Submit by 1 December 2026, 23:59 UTC
