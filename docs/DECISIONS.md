# Decisions

Short records of the choices that shaped this release. Each one names the alternative
that was rejected and why, because the rejected option is usually the interesting part.

## D1 — Throw away the v2 pinline, keep the client (21 Nov)

v2 was a fixed workflow per mission: `listing`, `stablecoin`, `yield`, `mining`. Each
bought the same intent from three miners and scored the agreement. That is easy to
demo and wrong commercially: the customer pays 3x for something the ranking layer
already provides.

Kept: `core/client.py` (escrow signing, payment challenges, receipts, caps) and the
wallet loader, because they are the genuinely hard, network-specific parts.

Rejected: incrementally adding a fourth and fifth workflow. More workflows would have
made the demo longer and the product the same shape. The shape was the problem.

## D2 — Coverage first, escalation only where it pays (21 Nov)

The allocator buys one ask per claim until the budget is committed. Escalation then
considers only two kinds of cluster: a load-bearing claim that is not settled, and a
claim where two sources already disagree. Everything else stays at one ask.

Rejected: escalating every single-sourced claim. That sounds rigorous and is just the
3x behaviour again with extra steps. Single-sourced is the normal state of a cheap run.

Rejected: a fixed "always verify sanctions twice" rule. It would have been defensible,
but it makes the cost fixed instead of earned, and the code already gives sanctions a
second ask when the first one is dead.

## D3 — False and zero are answers, not blanks (21 Nov)

The first live run classified `{"matched": false, "match_score": 0}` as an empty
answer, so a clean sanctions screen was reported as a gap and the verdict was HOLD.

This was the most dangerous bug in the release: it turned a real finding into a blind
spot. Fixed in `Fact.empty`, with a test that pins it. Blank means `None`, `""`, `[]`
or `{}` - nothing else.

## D4 — `HOLD` when a load-bearing claim cannot be bought (21 Nov)

If the sanctions screen fails three times, Colony returns HOLD with confidence 0 rather
than ALLOW with a caveat. The caveat would be read as permission; HOLD is not.

Rejected: omitting the failed claim from the verdict and reporting on what remained.
That produces a document that looks complete and is worse than no document.

## D5 — The memo is the product, the bundle is the proof (21 Nov)

The memo is markdown with footnotes and a receipt table. The bundle is JSON: every
fact, every receipt, the cluster map, the budget, and one sha256 over the canonical
form so a third party can prove the memo was not edited after the run.

Rejected: a PDF. It cannot be diffed, hashed and verified by a customer's auditor.

Rejected: a web dashboard as the primary surface. It demos well and audits badly.

## D6 — Dependency-free HTTP surface (21 Nov)

`colony/api.py` is stdlib only. One endpoint, one validation rule, no auth, no queue.

Rejected: FastAPI plus a worker. It would add nothing a treasury integration needs in
this release and would make the test suite need a network stack.

## D7 — Seven claims, fixed (21 Nov)

The claim registry is hand-written and closed. Adding an eighth claim means writing the
intent mapping, the field list, the priority, and a test.

Rejected: an LLM that decomposes arbitrary questions into intents at runtime. It makes
a better demo and a worse product: the decomposition could silently ask an intent that
cannot answer the claim, and the customer would pay for a confident mismatch.

## D8 — No averaging, ever (21 Nov)

Disagreement is reported, with both sides and their prices. There is no averaging code
path in the repository, by design.

Why: an average of a $4,000 and a $40,000 answer is a number that no source said and no
auditor can defend. It is the cheapest way to look confident, which is exactly why it
is banned here.
