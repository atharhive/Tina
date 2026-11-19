# Season II submission pack

Everything below is ready to paste into the official H2 form. Numbers come from the
committed runs in `evidence/` (19 November 2026, devnode, escrow rail). Replace
nothing with an estimate without labelling it as one.

## Entry 1 - Apps & Agents

**Project name:** Tina
**Track:** Apps & Agents
**Missions:** 01 Exchange, 02 Stablecoin, 13 Asset Management
**GitHub username that starred the bounties repo:** `atharhive`
**Reviewer link:** https://github.com/atharhive/Tina

### Short public summary

Tina is a due-diligence desk that buys the same question from three independent
Telegraph miners and reports where they agree. One miner's answer is an opinion
nobody can check; three miners priced separately, each with a receipt and a signal
hash, give a decision you can audit. It runs three workflows: listing risk for a
token, peg and counterparty health for a stablecoin, and yield plausibility for an
asset-management position. Testnet only, escrow-paid, capped per ask, run and day.

What works today: real paid requests through the escrow rail (20 paid asks, $0.15
charged across three runs), a verdict with reasons, and evidence a stranger can
re-check with `scripts/verify_evidence.py` (6/6 signal hashes resolute to this payer on
the node).

Links: [repository](https://github.com/atharhive/Tina) -
[usage transcripts](https://github.com/atharhive/Tina/blob/main/docs/USAGE.md) -
[tutorial](https://github.com/atharhive/Tina/blob/main/docs/TUTORIAL.md) -
[troubleshooting notes](https://github.com/atharhive/Tina/blob/main/docs/TROUBLESHOOTING.md)

### The five commercial questions

**1. Who is it for?**
Listing and treasury reviewers at small exchanges, funds and payment companies: the
person who has to say yes or no to a token, an issuer or a yield product, weekly, with
no research team behind them.

**2. What does it improve?**
A single model gives one answer with no provenance. Tina gives three priced answers
with receipts, reports the disagreement, and refuses to pass a decision it cannot
corroborate. Cost is $0.04-$0.10 per decision on testnet, in about 20 seconds of
wall-clock time. The difference is auditability, not model quality.

**3. What does it do today?**
Three workflows, 20 paid asks, all from escrow, all receipted. Real results from 19 Nov:
WETH/USDC on Base showed $24,873,363.78 of liquidity agreed by three miners and 5.2M
holders from two, verdict PASS 15/100; USDC showed a peg within 25 bps with an attested
reserve and no sanctions match, PASS 0/100; aave-v3 USDC showed $13.84B TVL agreed by
two miners but only one supply APY reading, which returns REVIEW 45/100 by design.

**4. Why would someone adopt it?**
Because the failure mode of an automated approval is a confident answer built on one
source. Reviewers already document decisions; Tina produces the document, with the
receipts attached. Before production it needs: mainnet pricing, a cache so repeated
deterministic asks are not re-bought, and more miners per intent for the thinly
supplied ones.

**5. How can someone try it?**
`git clone`, a venv, `scripts/fund_testnet.py mint 3`, `deposit 2.5`, then
`python3 cli.py listing --token ... --pool ... --chain base`. A free `quote` command
shows the cost without paying. Maintained by @atharhive.

### Demo script (2-5 minutes)

1. **Problem (20s).** "This is a listing review. One model says yes, and nobody can
   check why."
2. **Price it (20s).** `tina quote listing --token 0x4200...0006 --pool 0xd0b5...f224 --chain base`
   - shows 9 asks, $0.09 projected, no payment made.
3. **Run it (60s).** the same command without `quote`. Point at the three miners
   agreeing on `$24,873,363.78`, at the miner that failed, and at the verdict line.
4. **Evidence (60s).** open `runs/listing-*.md`, then
   `python3 scripts/verify_evidence.py runs/listing-*.json` and show 6/6 signals
   resolving on the node.
5. **Break it (40s).** `tina yield --project aave-v3` and show REVIEW 45/100 with "only
   one miner answered": the app refuses to pass a single opinion.
6. **Where it goes (20s).** the three missions, and the two truth sources contributed
   back to the evaluation pool so the same intents can be scored.

### Showcase permission

Text, screenshots of the terminal runs, the memo files, and the tutorial may be shared
publicly. No customer data is involved. Buyer introductions: yes.

## Entry 2 - Evaluators

**Track:** Evaluators
**Contributor address:** `0xb2b73753BC5396f5EbB34b0ea099ABCCFc6F2147`

Evaluation material submitted to the pool on the devnode:

| Intent | Rows | State |
|---|---|---|
| `CONTENT_MODERATION_GENERAL` | 20 | eligible |
| `KEYWORD_EXTRACTION_GENERAL` | 6 | eligible |
| `GRAMMAR_SPELL_CHECK_GENERAL` | 6 | eligible |
| `CRYPTO_PRICE_USD` (truth source) | 1 | uploaded 19 Nov, admitted |
| `CURRENCY_EXCHANGE_CONVERT` (truth source) | 1 | uploaded 19 Nov, admitted |

The two truth sources are the interesting part. A deterministic intent cannot be scored
until someone describes a public API that answers it, and one source is enough. Both are
keyless public APIs, checked by hand against the exact parameters the intent sends:

- `truth/truth-coinbase-spot.yaml` - Coinbase exchange rates, `data.rates.USD` as `price_usd`
- `truth/truth-frankfurter-ecb.yaml` - ECB reference rates, `rates.{to}` as `converted_amount`

They are also the sources Tina's own price workflow depends on, so the app and the
evaluation material reinforce each other instead of being two disconnected efforts.

Method and reproduction: `truth/upload_truth_source.py` (signed upload, five-line
EIP-191 message, sha256 of the exact body), and the YAML files themselves.

## Before submitting - checklist

- [ ] Star [telegraphprotocol/bounties](https://github.com/telegraphprotocol/bounties) (done, 19 Nov)
- [ ] Choose the track on the H2 form for each entry (the form is per entry, not per project)
- [ ] Record the 2-5 minute demo following the script above
- [ ] Paste the public summary and the five answers
- [ ] Attach the evidence links (`evidence/`, `docs/USAGE.md`, verify output)
- [ ] Set showcase permission and buyer-introduction preference
- [ ] Submit by 1 December 2026, 23:59 UTC
