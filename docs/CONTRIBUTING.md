# Contributing

Tina is small on purpose: a client, three workflows, a report writer, and tests.
Keep it that way.

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m pytest tests -q
```

The suite is offline. It must stay that way: no test may reach the network, need a
wallet, or spend anything. Payment-path tests use a fake transport
(`tests/test_client.py`).

## Adding a workflow

1. Add the intents and their parameters to `INTENTS` in `core/flows.py`. The cost
   estimate, the CLI and the workflow read that table, so they stay in step.
2. Write a pure scoring function: `score_<workflow>(...) -> {"risk_score", "verdict", "reasons"}`.
   No I/O. Missing data must add risk, never zero risk.
3. Write the orchestration function that buys the observations and calls the scorer.
4. Add tests: one that passes, one that rejects, one where a miner returns nothing.
5. Add the command to `cli.py` with the shared `common` parser, and a line in the
   README table.

## Rules the code follows

- **Never claim more than the receipt shows.** The node's `cost_usd`, `signal_hash`
  and `X-PAYMENT-RESPONSE` are the evidence; the memo quotes them.
- **A missing answer is not a good answer.** If a field is absent, risk goes up and
  the reason says so.
- **Caps before signatures.** Every paid ask passes `--max-ask`, `--max-run` and
  `--max-day` before anything is signed.
- **No key material anywhere.** Not in logs, memos, run JSON, errors or tests. Only
  the public address is printed.
- **Failures are recorded, not swallowed.** A miner that dies mid-run appears in the
  run JSON with its error and in the memo as a gap.

## Pull requests

- One behaviour per commit, `type(scope): summary` in the imperative, no emoji.
- Run `./.venv/bin/python -m pytest tests -q` and `./.venv/bin/python cli.py quote yield`
  before pushing.
- If you change a verdict threshold, say which run in `evidence/` changes with it.

## Evaluation material

`truth/` holds truth sources and the signed uploader. An upload is free and does not
register a miner, but it changes the live pool other people's rankings depend on:

- Only upload a source you have called yourself, with the exact parameters the
  intent sends.
- Prefer APIs that need no key: a truth source never carries credentials.
- Verify the answer field path in the response before uploading. A wrong path makes
  the intent grade miners against nothing.
- One intent per upload. Re-uploading the same endpoints is a duplicate, not an
  improvement.
