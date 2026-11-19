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
from datetime import datetime, timezone
from pathlib import Path

from core import __version__
from core.client import PaymentRefused, SpendLog, TelegraphClient, TelegraphError
from core.catalogue import health, miners, plan, workflow_health
from core.flows import Desk, listing_check, mining_check, stablecoin_check, yield_check
from core.report import render_memo, write_run
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


def _interval(value: str | None) -> str:
    """Default settlement interval: the current hour, in UTC, as the intent expects."""
    if value:
        return value
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_mining(args: argparse.Namespace) -> int:
    client = _client(args)
    desk = Desk(client, miners_per_intent=args.miners)
    report = mining_check(
        desk,
        zone=args.zone,
        block=args.block,
        hashrate_ph=args.hashrate_ph,
        efficiency_j_per_th=args.efficiency,
        interval=_interval(args.interval),
        on_event=None if args.quiet else print,
    )
    economics = report["verdict"].get("economics", {})
    if economics.get("margin_usd_per_day") is not None:
        print(
            f"\n{economics['hashrate_ph']:g} PH at {economics['efficiency_j_per_th']:g} J/TH = "
            f"{economics['power_kw']:,.0f} kW; revenue ${economics['revenue_usd_per_day']:,.2f}/day, "
            f"power ${economics['power_cost_usd_per_day']:,.2f}/day, margin "
            f"${economics['margin_usd_per_day']:,.2f}/day ({economics['margin_pct']}%)"
        )
    return _finish(args, report)


def cmd_quote(args: argparse.Namespace) -> int:
    """Price a workflow without paying: one challenge per intent, no signature."""
    client = _client(args)
    inputs = {
        "token": args.token,
        "pool": args.pool,
        "chain": args.chain,
        "symbol": args.symbol,
        "asset": args.asset,
        "issuer": args.issuer,
        "project": args.project,
        "zone": getattr(args, "zone", ""),
        "block": getattr(args, "block", 0),
        "interval": _interval(getattr(args, "interval", None)),
    }
    estimate = plan(client, args.workflow, inputs, args.miners)
    for row in estimate["asks"]:
        if "error" in row:
            print(f"{row['intent']:38} unavailable: {row['error']}")
            continue
        print(
            f"{row['intent']:38} ${row['price_usd']:.2f}/ask x {args.miners} miners  "
            f"escrow={row['escrow_available']}"
        )
    print(f"\nprojected cost for this run: ${estimate['projected_usd']:.4f} USDC")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Re-render a memo from saved evidence, without buying anything again."""
    path = Path(args.run)
    if not path.exists():
        print(f"no such run file: {path}")
        return 1
    report = json.loads(path.read_text())
    memo = render_memo(report)
    if args.write:
        target = path.with_suffix(".replayed.md")
        target.write_text(memo)
        print(f"memo written to {target}")
    else:
        print(memo)
    verdict = report["verdict"]
    print(f"replay: {verdict['verdict']} (risk {verdict['risk_score']}/100), "
          f"cost ${report.get('cost_usd', 0):.4f}, {len(report.get('observations', []))} intents")
    return 0


def cmd_signal(args: argparse.Namespace) -> int:
    """Look a signal hash up on the node: the delivery record behind a paid answer. Free."""
    client = _client(args)
    try:
        record = client.signal(args.hash)
    except TelegraphError as exc:
        print(f"signal not found or unavailable: {exc}")
        return 1
    signal = record.get("signal", record)
    for key in ("signal_hash", "kind", "wallet_address", "miner_slug", "intent_id", "created_at"):
        if signal.get(key) is not None:
            print(f"{key:15} {signal[key]}")
    if args.json:
        print(json.dumps(record, indent=2))
    return 0


def cmd_spend(args: argparse.Namespace) -> int:
    """What the caps have actually been charged, per UTC day. Free."""
    log = SpendLog()
    rows = log.history()
    if not rows:
        print("nothing charged yet")
    for day, amount in rows.items():
        print(f"{day}  ${amount:.4f}")
    print(f"today  ${log.today():.4f} of ${args.max_day:.2f} daily cap")
    return 0


def cmd_miners(args: argparse.Namespace) -> int:
    """Who serves an intent, at what price, in what order. Free."""
    client = _client(args)
    rows = miners(client, args.intent, args.limit)
    if not rows:
        print(f"no active miner serves {args.intent}")
        return 1
    print(f"{'rank':>5}  {'id':>8}  {'slug':32}  {'price':>7}  requests")
    for m in rows:
        rank = "-" if m.get("rank") is None else str(m["rank"])
        print(f"{rank:>5}  {m['id']:>8}  {(m.get('slug') or '')[:32]:32}  {m['price_usd']:>7.4f}  {m['requests_served']}")
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    """How buyable an intent or a whole workflow looks right now. Free."""
    client = _client(args)
    if args.target in {"listing", "stablecoin", "yield"}:
        report = workflow_health(client, args.target)
        rows = report["intents"]
    else:
        rows = [health(client, args.target)]
    ok = True
    for row in rows:
        if "error" in row:
            ok = False
            print(f"{row['intent']:38} {row['error']}")
            continue
        fields = ", ".join(row["fields"][:4])
        print(
            f"{row['intent']:38} ranked={row['miners_ranked']:>2}/{row['miners_registered']:<4} "
            f"price={row['cheapest_usd']}-{row['priciest_usd']} fields=[{fields}]"
        )
        if not row["miners_ranked"]:
            ok = False
    return 0 if ok else 1


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

    mn2 = sub.add_parser("mining", parents=[common], help="mining margin at a power price (Mission 12)")
    mn2.add_argument("--zone", required=True, help="pricing node or bidding zone, e.g. ERCOT.HB_NORTH")
    mn2.add_argument("--block", type=int, required=True, help="Bitcoin block height for the hashprice read")
    mn2.add_argument("--hashrate-ph", type=float, default=1.0, help="site hashrate in PH/s (default 1)")
    mn2.add_argument("--efficiency", type=float, default=25.0, help="rig efficiency in J/TH (default 25)")
    mn2.add_argument("--interval", default=None, help="settlement interval start (default: this hour, UTC)")
    mn2.set_defaults(func=cmd_mining)

    q = sub.add_parser("quote", parents=[common], help="price a workflow without paying")
    q.add_argument("workflow", choices=["listing", "stablecoin", "yield", "mining"])
    q.add_argument("--token", default=None)
    q.add_argument("--pool", default=None)
    q.add_argument("--chain", default="base")
    q.add_argument("--size-usd", type=float, default=25000.0)
    q.add_argument("--symbol", default="USDC")
    q.add_argument("--asset", default="USDC")
    q.add_argument("--issuer", default="Circle")
    q.add_argument("--project", default="aave-v3")
    q.add_argument("--zone", default="ERCOT.HB_NORTH")
    q.add_argument("--block", type=int, default=920000)
    q.add_argument("--interval", default=None)
    q.set_defaults(func=cmd_quote)

    rp = sub.add_parser("replay", parents=[common], help="re-render a memo from a saved run (free)")
    rp.add_argument("run")
    rp.add_argument("--write", action="store_true", help="write <run>.replayed.md instead of printing")
    rp.set_defaults(func=cmd_replay)

    sg = sub.add_parser("signal", parents=[common], help="look up a paid answer's delivery record (free)")
    sg.add_argument("hash")
    sg.set_defaults(func=cmd_signal)

    sp = sub.add_parser("spend", parents=[common], help="what the caps have been charged, per day (free)")
    sp.set_defaults(func=cmd_spend)

    mn = sub.add_parser("miners", parents=[common], help="ranked miners for an intent, with prices (free)")
    mn.add_argument("intent")
    mn.add_argument("--limit", type=int, default=10)
    mn.set_defaults(func=cmd_miners)

    hl = sub.add_parser("health", parents=[common], help="supply and price for an intent or workflow (free)")
    hl.add_argument("target", help="an intent name, or one of listing, stablecoin, yield")
    hl.set_defaults(func=cmd_health)

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
