# Demo

`colony-demo.mp4` — 2:52, 1280x720, narrated by Brian (en-US, multilingual).

## This one is the real thing

The terminal footage is a **live session recorded in a PTY**, not a mockup and not a
reconstruction. The commands ran against the devnode, the payments settled from escrow,
and the receipts in the video are the receipts in `evidence/`. The pauses where a miner
took six seconds to answer are real pauses; each scene is only sped up or slowed so it
lines up with its narration.

The two browser shots are live pages: `telegraphprotocol.com` and
`github.com/atharhive/colony`.

## What it shows

1. What Telegraph is: a vending machine for facts, where each answer costs a penny and
   comes with a receipt.
2. The problem: decide today whether to give a counterparty 60-day terms.
3. The seven claims, two of them load-bearing.
4. The live run: nine paid asks, two failed registry attempts that cost nothing, and two
   extra sanctions scouts because one opinion was not enough.
5. The memo: ALLOW WITH CONDITIONS, 50/100 confidence, $0.09, and an explicit section on
   what could not be verified.
6. `verify_bundle.py` saying VERIFIED, then catching a single edited fact.
7. 54 tests with no network, then the purchase ledger.
8. Where to check: the repository, and the evidence folder inside it.

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
live outside the package, because nothing in `colony/` depends on them. The capture file
is a JSONL of timestamped chunks, so the same session can be re-cut without re-buying
anything.
