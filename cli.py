#!/usr/bin/env python3
"""Tina: buy corroborated intelligence on Telegraph and turn it into a decision.

Examples
--------
  tina quote listing --token 0x... --pool 0x... --chain base
  tina listing --token 0x... --pool 0x... --chain base --size-usd 25000
  tina stablecoin --symbol USDC --asset USDC --issuer Circle
  tina yield --project aave-v3 --symbol USDC --chain ethereum
  tina account

Every paid run prints the price it was charged and writes a memo plus the raw
answers and receipts under ./runs/. `--dry-run` prices the whole workflow and
spends nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core import __version__
from core.client import PaymentRefused, TelegraphClient, TelegraphError
from core.flows import Desk, listing_check, stablecoin_check, yield_check
from core.report import write_run
from core.wallet import WalletError, load_wallet


def _client(args: argparse.Namespace) -> TelegraphClient:
    wallet = load_wallet(args.wallet)
    if not args.quiet:
        print(f"wallet {wallet.address}")
        print(f"node   {args.node}")
    return TelegraphClient(
        wallet.key,
        node=args.node,
        max_usd_per_ask=args.max_ask,
        max_usd_per_run=args.max_run,
        max_usd_per_day=args.max_day,
        dry_run=args.dry_run,
    )


def _finish(args: argparse.Namespace, report: dict) -> int:
    verdict = report["verdict"]
    print()
    print(f"verdict : {verdict['verdict']} (risk {verdict['risk_score']}/100)")
    for reason in verdict["reasons"]:
        print(f"  - {reason}")
    print(f"cost    : ${report['cost_usd']:.4f} USDC")
    for gap in report.get("gaps") or []:
        print(f"gap     : {gap}")

    if args.json:
        print(json.dumps(report, indent=2))
    if not args.no_save:
        paths = write_run(report, Path(args.out))
        print(f"evidence: {paths['memo']}")
        print(f"run     : {paths['run']}")
    return 0 if verdict["verdict"] != "REJECT" else 2


def cmd_listing(args: argparse.Namespace) -> int:
    client = _client(args)
    desk = Desk(client, miners_per_intent=args.miners)
    report = listing_check(
        desk,
        token=args.token,
        pool=args.pool,
        chain=args.chain,
        trade_usd=args.size_usd,
        on_event=None if args.quiet else print,
    )
    return _finish(args, report)


def cmd_stablecoin(args: argparse.Namespace) -> int:
    client = _client(args)
    desk = Desk(client, miners_per_intent=args.miners)
    report = stablecoin_check(
        desk,
        asset_symbol=args.symbol,
        asset_id=args.asset,
        issuer=args.issuer,
        on_event=None if args.quiet else print,
    )
    return _finish(args, report)


def cmd_yield(args: argparse.Namespace) -> int:
    client = _client(args)
    desk = Desk(client, miners_per_intent=args.miners)
    report = yield_check(
        desk,
        project=args.project,
        symbol=args.symbol,
        chain=args.chain,
        on_event=None if args.quiet else print,
    )
    return _finish(args, report)


def cmd_quote(args: argparse.Namespace) -> int:
    """Price a workflow without paying: one challenge per intent, no signature."""
    client = _client(args)
    planned = {
        "listing": [
            ("LIQUIDITY_DEPTH_VERIFY_GENERAL", {"pool": getattr(args, "pool", "0x0"), "chain": getattr(args, "chain", "base")}),
            ("TOKEN_HOLDER_COUNT_GENERAL", {"token": getattr(args, "token", "0x0"), "chain": getattr(args, "chain", "base")}),
            ("WASH_TRADING_DETECTION_GENERAL", {"subject": getattr(args, "token", "0x0")}),
        ],
        "stablecoin": [
            ("CRYPTO_PRICE_USD", {"symbol": getattr(args, "symbol", "USDC")}),
            ("ASSET_RESERVE_ATTESTATION_GENERAL", {"asset": getattr(args, "asset", "USDC")}),
            ("SANCTIONS_SCREENING_MATCH_GENERAL", {"name": getattr(args, "issuer", "Circle")}),
        ],
        "yield": [
            ("CRYPTO_YIELD_RATE_GENERAL", {"project": getattr(args, "project", "aave-v3"), "symbol": getattr(args, "symbol", "USDC"), "chain": getattr(args, "chain", "ethereum")}),
            ("TVL_LOOKUP_GENERAL", {"protocol": getattr(args, "project", "aave-v3")}),
        ],
    }[args.workflow]

    total = 0.0
    for intent, params in planned:
        try:
            quote = client.quote(intent, params)
            price = quote["escrow_price_usd"] or 0.0
            total += price * args.miners
            print(f"{intent:38} ${price:.2f}/ask x {args.miners} miners  escrow={quote['escrow_available']}")
        except TelegraphError as exc:
            print(f"{intent:38} unavailable: {exc}")
    print(f"\nprojected cost for this run: ${total:.4f} USDC")
    return 0


def cmd_account(args: argparse.Namespace) -> int:
    """Read-only: wallet address and one escrow quote. No payment, no signature."""
    wallet = load_wallet(args.wallet)
    client = TelegraphClient(wallet.key, node=args.node, dry_run=True)
    print(f"wallet   {wallet.address}")
    print(f"node     {args.node}")
    try:
        quote = client.quote("CRYPTO_PRICE_USD", {"symbol": "ETH"})
        print(f"escrow   offered=${quote['escrow_price_usd']} rails={quote['other_rails']}")
    except TelegraphError as exc:
        print(f"escape   {exc}")
    print(f"spent today (local log): ${client.spent_today:.4f}")
    return 0


def cmd_intents(args: argparse.Namespace) -> int:
    wallet = load_wallet(args.wallet)
    client = TelegraphClient(wallet.key, node=args.node, dry_run=True)
    rows = client.intents()
    needle = (args.search or "").upper()
    for row in sorted(rows, key=lambda r: r.get("intent_name", "")):
        name = row.get("intent_name", "")
        if needle and needle not in name:
            continue
        print(f"{name:40} {row.get('miner_count', 0):>4} miners  {row.get('lifecycle_state', '')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tina", description="Corroborated due diligence, bought on Telegraph.")
    p.add_argument("--version", action="version", version=f"tina {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--node", default="https://devnode.telegraphprotocol.com")
    common.add_argument("--wallet", default=None, help="path to wallet.json (default ~/.telegraph/wallet.json)")
    common.add_argument("--miners", type=int, default=3, help="how many independent miners to buy from per intent")
    common.add_argument("--max-ask", type=float, default=0.05, help="cap in USDC for a single ask")
    common.add_argument("--max-run", type=float, default=0.20, help="cap in USDC for one run")
    common.add_argument("--max-day", type=float, default=1.00, help="cap in USDC per UTC day")
    common.add_argument("--dry-run", action="store_true", help="price everything, pay nothing")
    common.add_argument("--json", action="store_true", help="print the full evidence JSON")
    common.add_argument("--no-save", action="store_true", help="do not write a run directory")
    common.add_argument("--out", default="runs", help="directory for evidence (default ./runs)")
    common.add_argument("--quiet", action="store_true")

    sub = p.add_subparsers(dest="command", required=True)

    ls = sub.add_parser("listing", parents=[common], help="token listing risk (Mission 01 Exchange)")
    ls.add_argument("--token", required=True)
    ls.add_argument("--pool", required=True)
    ls.add_argument("--chain", default="base")
    ls.add_argument("--size-usd", type=float, default=25000.0)
    ls.set_defaults(func=cmd_listing)

    sc = sub.add_parser("stablecoin", parents=[common], help="stablecoin peg and reserve check (Mission 02)")
    sc.add_argument("--symbol", default="USDC")
    sc.add_argument("--asset", default="USDC", help="asset identifier the reserve intent expects")
    sc.add_argument("--issuer", default="Circle")
    sc.set_defaults(func=cmd_stablecoin)

    yc = sub.add_parser("yield", parents=[common], help="yield sanity check (Mission 13 Asset Management)")
    yc.add_argument("--project", required=True)
    yc.add_argument("--symbol", default="USDC")
    yc.add_argument("--chain", default="ethereum")
    yc.set_defaults(func=cmd_yield)

    q = sub.add_parser("quote", parents=[common], help="price a workflow without paying")
    q.add_argument("workflow", choices=["listing", "stablecoin", "yield"])
    q.add_argument("--token", default=None)
    q.add_argument("--pool", default=None)
    q.add_argument("--chain", default="base")
    q.add_argument("--size-usd", type=float, default=25000.0)
    q.add_argument("--symbol", default="USDC")
    q.add_argument("--asset", default="USDC")
    q.add_argument("--issuer", default="Circle")
    q.add_argument("--project", default="aave-v3")
    q.set_defaults(func=cmd_quote)

    ac = sub.add_parser("account", parents=[common], help="show the wallet address and escrow quote (free)")
    ac.set_defaults(func=cmd_account)

    it = sub.add_parser("intents", parents=[common], help="list intents this node serves (free)")
    it.add_argument("--search", default=None)
    it.set_defaults(func=cmd_intents)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except PaymentRefused as exc:
        print(f"payment refused: {exc}", file=sys.stderr)
        print("fund escrow with: npx -y @telegraphprotocol/telegraph-protocol-mcp fund", file=sys.stderr)
        return 3
    except (TelegraphError, WalletError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
