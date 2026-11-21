# Growth posts

Three dated posts, ready to paste. They are meant to be posted on different days,
because the growth criterion asks for at least three original updates and a burst on one
day does not count as a practice.

---

## Post 1 - the problem and the number

Every counterparty check I have seen ends the same way: a confident yes, and no record of
which fact the yes depended on.

So I built Colony. It takes one question - is this safe for 60-day terms - splits it into
seven claims, and buys the cheapest Telegraph answer for each. Then it prints a decision
where every sentence has a receipt, and a section listing exactly what it could not buy.

First live run: 11 asks, 8 paid, $0.08. The sanctions screen failed three times, so the
verdict was HOLD with confidence 0 instead of a fabricated ALLOW.

github.com/atharhive/colony

## Post 2 - the cost argument

The obvious objection to verifying an answer is that it costs 3x.

It does, if you verify everything. Colony buys one ask per claim, and spends more only in
two cases: two sources already disagree, or a claim the decision hinges on came back dead.
That is capped in code at two claims, so the worst case is 11 asks, not 21.

Measured on the live run: $0.08 for a seven-claim decision, against a $40/seat report
that gets refreshed quarterly.

github.com/atharhive/colony/blob/main/docs/PRICING.md

## Post 3 - the part that is uncomfortable

The most useful line in the memo I generate is not the verdict. It is "what we could not
verify".

On the last run, a Danish registry answered with the legal name and CVR number, and the
sanctions intent failed three times in a row. A model asked the same question will write
"no sanctions concerns" from memory. Colony cannot, because there is no receipt.

The bundle carries a sha256 over every fact and every receipt. You can recompute it
offline, and edit one fact and watch the checker say TAMPERED.

github.com/atharhive/colony

---

## Notes for posting

- Attach `docs/demo/colony-demo.mp4` or the shortest clip of the verify step. Video posts
  travel further than text on this topic.
- Do not claim production readiness. The figures are testnet, and saying so has been the
  difference between a conversation and a dismissal.
- Reply to anyone who asks with the bundle path, not a summary. The bundle is the
  argument.
