#!/usr/bin/env python3
"""Colony CLI.

  colony ask "Is Maersk safe to give 60-day terms?" --company "A.P. Moller-Maersk A/S" --budget 0.25
  colony watch --book book.json --budget 1.00
  colony ledger
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from colony import __version__
from colony.client import PaymentRefused, TelegraphClient, TelegraphError
from colony.intents import CLAIMS, Inputs
from colony.ledger import Ledger
from colony.memo import bundle, render
from colony.policy import Budget, BudgetExceeded
from colony.queen import run
from colony.wallet import WalletError, load_wallet


def _client(args) -> TelegraphClient:
    wallet = load_wallet(getattr(args, "wallet", None))
    if not args.quiet:
        print(f"wallet {wallet.address}")
        print(f"node   {args.node}")
    return TelegraphClient(
        wallet.key,
        node=args.node,
        max_usd_per_ask=args.max_ask,
        max_usd_per_run=max(args.max_run, args.budget),
        max_usd_per_day=args.max_day,
    )


def _live_observer():
    """Print each purchase as it lands, so a run can be watched instead of awaited."""
    started = time.time()
    count = [0]

    def observer(fact) -> None:
        count[0] += 1
        price = f"${fact.price_usd:.2f}" if fact.price_usd else "free"
        state = "ok" if fact.ok else ("empty" if fact.ok else "FAIL")
        miner = (fact.miner or "routed")[:24]
        print(f"  [{count[0]:02d}] {fact.claim_id:<9} {miner:<24} {price:<5} {state:<5} {time.time() - started:5.1f}s", flush=True)

    return observer


def cmd_ask(args) -> int:
    client = _client(args)
    inputs = Inputs(
        company=args.company,
        jurisdiction=args.jurisdiction,
        domain=args.domain or args.company.lower().replace(" ", ""),
        country=args.country,
        year=args.year,
    )
    budget = Budget(total_usd=args.budget, max_per_ask=args.max_ask)
    ledger = Ledger(path=None if args.no_ledger else Path(args.ledger))

    if args.live:
        print("scouts out")
    answer = run(
        client, args.question, inputs, budget, ledger=ledger,
        escalate=not args.no_escalate,
        observer=_live_observer() if args.live else None,
    )

    print()
    print(render(answer))
    if args.json or args.bundle:
        payload = bundle(answer)
        if args.bundle:
            Path(args.bundle).parent.mkdir(parents=True, exist_ok=True)
            Path(args.bundle).write_text(json.dumps(payload, indent=1))
            print(f"bundle   {args.bundle}")
            print(f"sha256   {payload['bundle_sha256']}")
        if args.json:
            print(json.dumps(payload, indent=1))
    return 0 if answer.verdict["verdict"] != "BLOCK" else 2


def cmd_watch(args) -> int:
    """Run the same swarm over a book of companies, cheapest claims first."""
    client = _client(args)
    book = json.loads(Path(args.book).read_text())
    per = args.budget / max(1, len(book.get("companies", [])))
    rows = []
    for company in book.get("companies", []):
        inputs = Inputs(company=company.get("name", ""), jurisdiction=company.get("jurisdiction", "Denmark"),
                        domain=company.get("domain"), country=company.get("country"))
        budget = Budget(total_usd=per, max_per_ask=args.max_ask)
        answer = run(client, f"terms decision: {inputs.company}", inputs, budget,
                     ledger=Ledger(path=Path(args.ledger)), escalate=False)
        rows.append({"company": inputs.company, "verdict": answer.verdict["verdict"],
                     "confidence": answer.verdict["confidence"], "spent": budget.spent_usd})
        print(f"{inputs.company:40} {answer.verdict['verdict']:22} {budget.spent_usd:.4f}")
    if args.json:
        print(json.dumps(rows, indent=1))
    return 0


def cmd_ledger(args) -> int:
    path = Path(args.ledger)
    if not path.exists():
        print(f"no ledger at {path}")
        return 1
    entries = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    total = sum(e["price_usd"] for e in entries)
    print(f"purchases {len(entries)}, spent ${total:.4f}")
    for e in entries[-args.tail:]:
        print(f"  {e['at'][:19]}  {e['claim']:10} {e['miner'][:26]:26} ${e['price_usd']:.4f}  {(e.get('signal_hash') or '')[:12]}")
    return 0


def cmd_claims(args) -> int:
    for claim in CLAIMS:
        flag = "load-bearing" if claim.load_bearing else ""
        print(f"{claim.id:10} {claim.intent:38} {flag}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="colony", description="A swarm that prices a question before it answers it.")
    p.add_argument("--version", action="version", version=f"colony {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--node", default="https://devnode.telegraphprotocol.com")
    common.add_argument("--wallet", default=None)
    common.add_argument("--max-ask", type=float, default=0.05)
    common.add_argument("--max-run", type=float, default=1.0)
    common.add_argument("--max-day", type=float, default=2.0)
    common.add_argument("--ledger", default="runs/ledger.jsonl")
    common.add_argument("--json", action="store_true")
    common.add_argument("--quiet", action="store_true")

    sub = p.add_subparsers(dest="cmd", required=True)
    ask = sub.add_parser("ask", parents=[common], help="buy a decision about one company")
    ask.add_argument("question")
    ask.add_argument("--company", required=True)
    ask.add_argument("--jurisdiction", default="Denmark")
    ask.add_argument("--domain", default=None)
    ask.add_argument("--country", default=None)
    ask.add_argument("--year", type=int, default=2025)
    ask.add_argument("--budget", type=float, default=0.25)
    ask.add_argument("--bundle", default=None, help="write the signed bundle here")
    ask.add_argument("--no-escalate", action="store_true")
    ask.add_argument("--live", action="store_true", help="print each purchase as it lands")
    ask.add_argument("--no-ledger", action="store_true")
    ask.set_defaults(func=cmd_ask)

    w = sub.add_parser("watch", parents=[common], help="run the swarm over a book")
    w.add_argument("--book", required=True)
    w.add_argument("--budget", type=float, default=1.0)
    w.set_defaults(func=cmd_watch)

    led = sub.add_parser("ledger", parents=[common], help="show what has been bought")
    led.add_argument("--tail", type=int, default=15)
    led.set_defaults(func=cmd_ledger)

    cl = sub.add_parser("claims", parents=[common], help="list the claims the swarm buys")
    cl.set_defaults(func=cmd_claims)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except PaymentRefused as exc:
        print(f"payment refused: {exc}", file=sys.stderr)
        return 3
    except BudgetExceeded as exc:
        print(f"budget: {exc}", file=sys.stderr)
        return 3
    except (TelegraphError, WalletError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
