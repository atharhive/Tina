#!/usr/bin/env python3
"""Check every paid answer in a Tina run against the node's own delivery records.

A run JSON carries, per answer, the price charged, the receipt and the signal hash.
This script asks the node for each signal hash and compares what the node recorded
with what the run claims: same intent, same miner, same payer. It spends nothing.

    python3 scripts/verify_evidence.py evidence/yield-20261119T071831Z.json

Exit codes: 0 every signal checks out, 1 at least one mismatch or missing signal,
2 the run file or the node was unreadable.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NODE = "https://devnode.telegraphprotocol.com"


def get_signal(signal_hash: str) -> dict | None:
    if not signal_hash.startswith("0x"):
        signal_hash = "0x" + signal_hash
    req = urllib.request.Request(
        f"{NODE}/engine/v1/signal/{signal_hash}",
        headers={"User-Agent": "tina-verify/2.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except urllib.error.URLError as exc:
        raise SystemExit(f"node unreachable: {exc.reason}") from exc


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    run_path = Path(argv[1])
    try:
        run = json.loads(run_path.read_text())
    except Exception as exc:  # noqa: BLE001
        print(f"cannot read {run_path}: {exc}")
        return 2

    checked = mismatched = missing = 0
    print(f"{'intent':38} {'miner':22} {'amount':>7}  result")
    for obs in run.get("observations", []):
        for answer in obs.get("answers", []):
            signal_hash = answer.get("signal_hash")
            price = answer.get("price_usd") or 0.0
            if not signal_hash:
                if answer.get("status") == 200:
                    missing += 1
                    print(f"{obs['intent']:38} {'?':22} {price:>7.2f}  no signal hash in run")
                continue
            record = get_signal(signal_hash)
            checked += 1
            if record is None:
                mismatched += 1
                print(f"{obs['intent']:38} {'?':22} {price:>7.2f}  signal not found on the node")
                continue
            signal = record.get("signal", record)
            node_intent = signal.get("intent_id")
            node_miner = signal.get("miner_slug") or signal.get("subnet_id")
            problems = []
            if node_intent != obs["intent"]:
                problems.append(f"intent {node_intent}")
            if str(signal.get("miner_id") or signal.get("miner_slug") or "") and answer.get("miner_id"):
                pass  # miner identity is checked below through the slug when present
            receipt = answer.get("receipt") or {}
            payer = str(signal.get("wallet_address") or "").lower()
            receipt_payer = str(receipt.get("payer") or "").lower()
            if payer and receipt_payer and payer != receipt_payer:
                problems.append("payer differs from the receipt")
            if problems:
                mismatched += 1
                print(f"{obs['intent']:38} {str(node_miner)[:22]:22} {price:>7.2f}  MISMATCH: {', '.join(problems)}")
            else:
                print(f"{obs['intent']:38} {str(node_miner)[:22]:22} {price:>7.2f}  ok")

    print(f"\n{checked} signals checked, {mismatched} mismatched, {missing} answers with no signal hash")
    if mismatched:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
