import argparse
import json
import os
import subprocess

DEFAULT_TARGET = (
    "Sponsored investment announcement: AI-powered decentralized trading vault "
    "guaranteeing 12% weekly APY with zero drawdown. Direct USDT deposits to verified "
    "smart contract 0x3624... with instant automated payouts."
)

def require_private_key():
    """Require an explicitly configured key; never fall back to a source literal."""
    key = os.environ.get("TELEGRAPH_PRIVATE_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "TELEGRAPH_PRIVATE_KEY is required. Use a fresh, funded test wallet; "
            "do not reuse a key that has been committed or shared."
        )
    if not key.startswith("0x") or len(key) != 66:
        raise RuntimeError("TELEGRAPH_PRIVATE_KEY must be a 0x-prefixed 32-byte hex key.")
    try:
        int(key[2:], 16)
    except ValueError as exc:
        raise RuntimeError("TELEGRAPH_PRIVATE_KEY must contain only hexadecimal bytes.") from exc
    return key


def query_telegraph(query, intent=None, params=None):
    """Call the Telegraph payer with data passed separately from executable code."""
    key = require_private_key()
    payload = {"query": query}
    if intent:
        payload.update({"intent": intent, "params": params or {}})
    script = r'''import('@telegraphprotocol/telegraph-protocol-mcp/dist/pay.js').then(async m => {
  const cfg = {
    url: process.env.TELEGRAPH_NODE_URL || 'https://devnode.telegraphprotocol.com',
    diamond: process.env.TELEGRAPH_DIAMOND || '0x3624EB012B5E998BB57B6bE6C9Cfc9c4bc5eb99b',
    chainId: Number(process.env.TELEGRAPH_CHAIN_ID || 11155111),
    payment: process.env.TELEGRAPH_PAYMENT || 'escrow',
    home: process.env.TELEGRAPH_HOME || (process.env.HOME + '/.telegraph'),
    maxAskUsd: Number(process.env.TELEGRAPH_MAX_ASK_USD || 0.05),
    dailyLimitUsd: Number(process.env.TELEGRAPH_DAILY_LIMIT_USD || 0.10)
  };
  const payload = JSON.parse(process.env.TINA_REQUEST_JSON);
  const payer = new m.Payer(cfg, process.env.TELEGRAPH_PRIVATE_KEY);
  const result = await payer.post('/engine/v1/ask', payload);
  console.log(JSON.stringify(result));
}).catch(error => { console.error(error.message); process.exitCode = 1; });
'''
    env = os.environ.copy()
    env["TINA_REQUEST_JSON"] = json.dumps(payload, ensure_ascii=False)
    env["TELEGRAPH_PRIVATE_KEY"] = key
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Telegraph request failed: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError("Telegraph returned an unrecognized response.") from exc

def evaluate(target_text, execute=False):
    print("TINA: TELEGRAPH VERIFICATION PROTOTYPE")
    print(f"Target: {target_text[:120]}")
    if not execute:
        print("DRY RUN: no requests sent and no funds spent.")
        return {"status": "dry_run", "requests_sent": 0, "cost_usd": 0}
    raise RuntimeError(
        "Paid mode is disabled until the live Intent schema, current quote, "
        "and safe wallet authorization are verified. No request was sent."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tina: Telegraph verification prototype")
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--execute", action="store_true", help="Reserved; currently disabled")
    args = parser.parse_args()
    evaluate(args.target, execute=args.execute)
