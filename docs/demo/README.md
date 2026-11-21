# Demo

`colony-demo.mp4` — 3:31, 1280x720, narrated by Brian (en-US, multilingual).

## This is a recorded session, not a mockup

The terminal footage is a **live session captured in a PTY**. The commands ran against
the devnode, the payments settled from escrow, and the receipts in the video are the
receipts in `evidence/`. The six-second pauses are real pauses; each scene is only
stretched or compressed so it lines up with its narration.

The browser shots are live pages: `telegraphprotocol.com` and the repository's
`evidence/` folder.

## The script, in order

1. **Hook.** "Will this company pay me back?" Today the options are three days of analyst
   work or a guess, and neither leaves a receipt.
2. **Why Colony.** One answer with no provenance is not evidence.
3. **The seven claims.** Two are load-bearing: sanctions and legal existence.
4. **How the swarm works.** A scout buys one answer; the queen maps agreement,
   disagreement and blindness; extra money is spent only where it changes the verdict,
   inside a hard budget cap.
5. **Telegraph, in one minute.** Intents are the menu, miners compete and are ranked,
   payment is per answer through an escrow rail, and every answer carries a receipt hash
   and a signal hash.
6. **The live run.** Seven claims at a penny each, two registry failures that cost
   nothing, then two extra sanctions scouts because one opinion cannot decide that claim.
7. **The decision.** ALLOW WITH CONDITIONS, 50/100, $0.09, with the reason confidence is
   not higher printed in the memo.
8. **Proof.** `verify_bundle.py` recomputes the hash and says VERIFIED.
9. **Tamper.** One edited fact and the same checker says TAMPERED.
10. **Tests and ledger.** 54 tests with no network, and every purchase in order.
11. **Where to check.** The repository, starting with the `evidence/` folder.
12. **Why the swarm.** One scout per claim keeps cost near a single answer; the map makes
    disagreement visible; the queen spends depth only where it changes the decision; the
    memo footnotes or omits every sentence.
13. **Outro.** Built by Athar, with love.

## What changed in this cut

The previous version had abrupt transitions and lines that were clipped at the window
edge. Fixed by sampling the session on a fixed 0.22s grid instead of on chunk boundaries,
adding a short fade at each scene edge, and soft-wrapping long terminal lines the way a
real terminal would instead of truncating them.

## Reproducing it

```
git clone https://github.com/atharhive/colony && cd colony
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m colony ask "Is this counterparty safe for 60-day payment terms?" \
  --company "A.P. Moller-Maersk A/S" --domain maersk.com --budget 0.25 \
  --bundle runs/demo.json --live
./.venv/bin/python scripts/verify_bundle.py runs/demo.json
```

Costs about nine cents of testnet USDC. `--live` prints each purchase as it lands, which
is the view used in the video.

## The taping

One take, one session, default budget. The video stays honest about the awkward parts:
two registry miners failed, confidence is 50 rather than 100, and the memo says why.

## Rebuilding it

The recorder (`pty` capture with timings) and the renderer (Pillow + edge-tts + ffmpeg)
live outside the package, because nothing in `colony/` depends on them. The capture is a
JSONL of timestamped chunks, so the same session can be re-cut without re-buying
anything.
