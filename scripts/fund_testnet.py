#!/usr/bin/env python3
"""Fund a Tina test wallet on Ethereum Sepolia: mint test USDC, deposit escrow.

Testnet only. The Sepolia test USDC at 0xcc194e1a... is an open mint token, which
is how the Telegraph docs say to fund a devnet wallet; no real asset is involved.

    python3 scripts/fund_testnet.py mint 3        # 3 test USDC to the wallet
    python3 scripts/fund_testnet.py deposit 2.5   # approve + depositUSDC on the node's Diamond
    python3 scripts/fund_testnet.py status        # on-chain + node ledger view
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eth_account import Account  # noqa: E402
from eth_utils import keccak  # noqa: E402

from core.wallet import load_wallet  # noqa: E402

RPC = "https://ethereum-sepolia-rpc.publicnode.com"
NODE = "https://devnode.telegraphprotocol.com"
USDC = "0xcc194e1a843B658526D0D5C431f670028582Ae17"
DIAMOND = "0x72a70e949362670Bf8bceAd24eFC5b8f950aa08b"  # the Diamond /engine/v1/ask settles to
CHAIN_ID = 11155111


def rpc(method: str, params: list) -> Any:
    req = urllib.request.Request(
        RPC,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"},
    )
    out = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in out:
        raise RuntimeError(out["error"].get("message", out["error"]))
    return out["result"]


def send(acct, to: str, data: str, gas: int = 300_000) -> str:
    nonce = int(rpc("eth_getTransactionCount", [acct.address, "pending"]), 16)
    base = int(rpc("eth_getBlockByNumber", ["latest", False])["baseFeePerGas"], 16)
    tx = {
        "to": to,
        "data": data,
        "value": 0,
        "gas": gas,
        "maxFeePerGas": base * 2 + 10**9,
        "maxPriorityFeePerGas": 10**9,
        "chainId": CHAIN_ID,
        "nonce": nonce,
        "type": 2,
    }
    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    return rpc("eth_sendRawTransaction", ["0x" + raw.hex()])


def wait(tx: str) -> str:
    for _ in range(60):
        receipt = rpc("eth_getTransactionReceipt", [tx])
        if receipt:
            return receipt["status"]
        time.sleep(3)
    raise RuntimeError(f"no receipt for {tx}")


def call(to: str, sig: str, arg: str = "") -> int:
    data = "0x" + keccak(text=sig)[:4].hex() + arg
    return int(rpc("eth_call", [{"to": to, "data": data}, "latest"]), 16)


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    amount = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    wallet = load_wallet()
    acct = Account.from_key(wallet.key)
    units = int(round(amount * 1_000_000))
    padded = acct.address[2:].lower().rjust(64, "0")

    if action == "mint":
        if units <= 0:
            print("usage: fund_testnet.py mint <usdc>")
            return 1
        data = "0x" + keccak(text="mint(address,uint256)")[:4].hex() + padded + units.to_bytes(32, "big").hex()
        tx = send(acct, USDC, data)
        print(f"mint   {tx} status={wait(tx)}")
    elif action == "deposit":
        if units <= 0:
            print("usage: fund_testnet.py deposit <usdc>")
            return 1
        data = "0x" + keccak(text="approve(address,uint256)")[:4].hex() + DIAMOND[2:].lower().rjust(64, "0") + units.to_bytes(32, "big").hex()
        tx = send(acct, USDC, data)
        print(f"approve {tx} status={wait(tx)}")
        data = "0x" + keccak(text="depositUSDC(uint256)")[:4].hex() + units.to_bytes(32, "big").hex()
        tx = send(acct, DIAMOND, data)
        print(f"deposit {tx} status={wait(tx)}")
    elif action != "status":
        print("usage: fund_testnet.py [mint|deposit|status] [usdc]")
        return 1

    usdc = call(USDC, "balanceOf(address)", padded)
    escrow = rpc("eth_call", [{"to": DIAMOND, "data": "0x" + keccak(text="ledgerAccount(address)")[:4].hex() + padded}, "latest"])
    deposited = int(escrow[2:66], 16)
    print(f"wallet  {acct.address}")
    print(f"usdc    {usdc / 1e6:.6f} (Sepolia test token)")
    print(f"escrow  {deposited / 1e6:.6f} deposited on the node Diamond")
    try:
        ledger = json.loads(
            urllib.request.urlopen(
                urllib.request.Request(f"{NODE}/v1/ledger/account/{acct.address}", headers={"User-Agent": "tina/2.0"}),
                timeout=30,
            ).read()
        )
        print(f"node    available={int(ledger['available']) / 1e6:.6f} balance={int(ledger['balance']) / 1e6:.6f} epoch={ledger['active_root']['epoch_id']}")
    except Exception as exc:  # noqa: BLE001
        print(f"node    ledger unavailable: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
