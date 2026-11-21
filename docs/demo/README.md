# Demo

`colony-demo.mp4` — 2:48, 1280x720, narrated (en-GB, Thomas).

## How it was made

It is a **reconstruction, not a screen recording.** Every terminal frame is rendered
from the committed run in `evidence/colony-maersk-20261121.json` and the memo it
produced. The numbers, the miner names, the verdict and the cost are the run's, not
plausible-looking placeholders. Nothing is a live capture, and the video does not claim
to be one.

If you would rather watch a live session, `docs/USAGE.md` has the exact commands, and the
whole run costs about eight cents on testnet.

## What it shows

1. The decision a credit team actually makes, and the file it never produces.
2. The seven claims, and which two are load-bearing.
3. One ask per claim, escalation only where the answer changes: 11 asks, 8 paid, $0.08.
4. The memo, including the section most tools would leave out.
5. `verify_bundle.py` saying VERIFIED, and what happens when one fact is edited.
6. The cost ladder, and the cap that prevents a quiet 21-ask run.

## Transcript

The narration text lives in the build script's `SCENES` list, which is kept outside the
repository because it is a render tool, not part of the product. The scenes map 1:1 to
the sections above.

## Rebuilding it

The renderer needs Pillow, edge-tts and ffmpeg, and rebuilds the whole video in about
five minutes. It is intentionally not part of the package: nothing in `colony/` depends
on it.
