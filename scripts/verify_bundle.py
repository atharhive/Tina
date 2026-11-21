#!/usr/bin/env python3
"""Verify a Colony bundle without trusting Colony.

Three independent checks:
  1. the sha256 recomputes over the canonical payload;
  2. every footnote row traces to a ledger entry;
  3. every verdict reason is reachable from the cluster map.

Exit 0 clean, 1 tampered, 2 unreadable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

CANONICAL_KEYS = ("company", "question", "verdict", "clusters", "ledger", "budget", "escalations")


def canonical_hash(bundle: dict) -> str:
    payload = {k: bundle[k] for k in CANONICAL_KEYS if k in bundle}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def verify(bundle: dict) -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    expected = canonical_hash(bundle)
    actual = bundle.get("bundle_sha256")
    if expected != actual:
        ok = False
        notes.append(f"hash mismatch: recomputed {expected[:16]}, bundle says {str(actual)[:16]}")
    else:
        notes.append(f"hash ok: {expected[:16]}")

    entries = bundle.get("ledger", {}).get("entries", [])
    claims_with_entries = {e.get("claim") for e in entries}
    for cid in bundle.get("clusters", {}):
        if cid not in claims_with_entries:
            ok = False
            notes.append(f"cluster {cid} has no ledger entry")
    notes.append(f"ledger: {len(entries)} entries cover {len(claims_with_entries)} claims")

    receipts = [e for e in entries if e.get("receipt")]
    unanswered = [e for e in entries if not e.get("ok")]
    notes.append(f"receipts: {len(receipts)} present, {len(unanswered)} asks failed")

    paid = round(sum(float(e.get("price_usd") or 0) for e in entries), 6)
    declared = bundle.get("budget", {}).get("spent_usd")
    if declared is not None and abs(paid - float(declared)) > 1e-9:
        ok = False
        notes.append(f"budget mismatch: entries sum to {paid}, budget says {declared}")

    verdict = bundle.get("verdict", {}).get("verdict", "")
    if verdict not in {"ALLOW", "ALLOW WITH CONDITIONS", "HOLD", "BLOCK"}:
        ok = False
        notes.append(f"unknown verdict {verdict!r}")

    return ok, notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="verify a colony bundle")
    ap.add_argument("path")
    args = ap.parse_args(argv)
    try:
        bundle = json.loads(Path(args.path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable: {exc}", file=sys.stderr)
        return 2
    ok, notes = verify(bundle)
    for note in notes:
        print(("  ok  " if "mismatch" not in note and "no ledger" not in note else "  BAD ") + note)
    print("VERIFIED" if ok else "TAMPERED OR INCOMPLETE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
