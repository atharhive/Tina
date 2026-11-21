#!/usr/bin/env python3
"""Upload an evaluation-pool truth source to a Telegraph node.

Usage:
    python3 truth/upload_truth_source.py truth/truth-coinbase-spot.yaml CRYPTO_PRICE_USD

The row is signed with EIP-191 over the exact body sha256, as the node requires:
five lines, no trailing newline, chain id 11155111 on the testnet node.
Uploads are free and do not register a miner on chain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eth_account import Account  # noqa: E402
from eth_account.messages import encode_defunct  # noqa: E402

from core.wallet import load_wallet  # noqa: E402

NODE = "https://devnode.telegraphprotocol.com"
CHAIN_ID = "11155111"


def upload(node: str, intent: str, body: bytes, key: str) -> dict:
    acct = Account.from_key(key)
    body_sha = hashlib.sha256(body).hexdigest()
    nonce = secrets.token_hex(16)
    message = (
        "Telegraph eval-pool submission v1\n"
        f"intent_id: {intent}\n"
        f"body_sha256: {body_sha}\n"
        f"nonce: {nonce}\n"
        f"chain_id: {CHAIN_ID}"
    )
    sig = acct.sign_message(encode_defunct(text=message)).signature
    sig_hex = sig.hex() if isinstance(sig, (bytes, bytearray)) else str(sig)
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex

    url = f"{node}/api/evalpool/submissions?intent_id={intent}&submitter={acct.address}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-ndjson",
            "X-Evalpool-Signature": sig_hex,
            "X-Evalpool-Nonce": nonce,
            "User-Agent": "colony-uploader/3.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code, "error": exc.read().decode(errors="replace")[:500]}


def mine(node: str, intent: str, address: str) -> dict:
    url = f"{node}/api/evalpool/submissions/mine?submitter={address}&intent_id={intent}"
    req = urllib.request.Request(url, headers={"User-Agent": "colony-uploader/3.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="truth source YAML")
    ap.add_argument("intent", help="canonical intent this source answers")
    ap.add_argument("--node", default=NODE)
    args = ap.parse_args()

    text = Path(args.file).read_text()
    wallet = load_wallet()
    row = json.dumps({"label_kind": "truth_source", "source": text}, ensure_ascii=False) + "\n"
    result = upload(args.node, args.intent, row.encode(), wallet.key)
    print(json.dumps(result, indent=2))

    print("\nrows credited to this wallet:")
    rows = mine(args.node, args.intent, wallet.address)
    for r in rows.get("rows", [])[-5:]:
        print(f"  {r.get('status')} {r.get('provenance_class')} {r.get('row_hash','')[:16]}")
    return 0 if result.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
