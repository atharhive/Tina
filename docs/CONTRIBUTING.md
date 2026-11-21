# Contributing

## The shape of a change

Every change lands in one of five places:

1. **A claim** (`colony/intents.py`): a question, an intent, the fields, a priority.
2. **A scout** (`colony/scouts.py`): how one ask becomes one fact. Rarely changes.
3. **The map** (`colony/cluster.py`): what agreement means for this domain.
4. **The allocator** (`colony/allocator.py`): who gets bought, and who gets a second ask.
5. **The memo** (`colony/memo.py`): what the customer reads.

If a change does not fit one of those, it is probably a new product, not a patch.

## Adding a claim

```python
Claim(
    id="ownership",
    question="Who ultimately owns this entity?",
    intent="BENEFICIAL_OWNERSHIP_LOOKUP_GENERAL",
    params={"company": "$company"},
    fields=("owner_name", "ownership_pct"),
    load_bearing=False,
    priority=35,
)
```

Then add a test in `tests/test_intents.py` that pins the resolved params, and one in
`tests/test_queen_memo.py` if the claim can change a verdict.

Rules:

- `load_bearing=True` means a failure of this claim can force HOLD or BLOCK. Use it
  sparingly: every load-bearing claim raises the cost of a bad run.
- `priority` decides what gets bought first when the budget is small. Lower buys earlier.
- Never add a claim whose intent does not exist on the node. Check with
  `./.venv/bin/python -m colony.cli claims` and the node's intent catalogue.

## What will not be merged

- **Averaging disagreeing answers.** The memo shows both sides. There is no code path
  that produces a number no source said.
- **Unconditional multi-buying.** One ask per claim is the default. Extra scouts need a
  trigger in `allocator.escalation_plan` and a test.
- **A verdict that hides a gap.** If a load-bearing claim failed, the verdict is HOLD.
- **A dependency for the HTTP surface.** It is stdlib on purpose.

## Tests

```bash
./.venv/bin/python -m pytest tests -q
```

Offline, no wallet, no network, no spend. A test that needs a miner belongs in a fake
client, not in CI.

## Commits

`type(scope): sentence in the imperative`. One idea per commit. If a commit needs the
word "and" twice, it is two commits.
