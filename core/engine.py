import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path

DEFAULT_TARGET = (
    "Sponsored investment announcement: AI-powered decentralized trading vault "
    "guaranteeing 12% weekly APY with zero drawdown. Direct USDT deposits to verified "
    "smart contract 0x3624... with instant automated payouts."
)

def query_telegraph(query, intent=None, params=None):
    cmd = [
        "node", "-e", f"""
        import('@telegraphprotocol/telegraph-protocol-mcp/dist/pay.js').then(async m => {{
          const cfg = {{
            url: process.env.TELEGRAPH_NODE_URL || 'https://devnode.telegraphprotocol.com',
            diamond: process.env.TELEGRAPH_DIAMOND || '0x3624EB012B5E998BB57B6bE6C9Cfc9c4bc5eb99b',
            chainId: Number(process.env.TELEGRAPH_CHAIN_ID || 11155111),
            payment: process.env.TELEGRAPH_PAYMENT || 'escrow',
            home: process.env.TELEGRAPH_HOME || (process.env.HOME + '/.telegraph'),
            maxAskUsd: 0.5,
            dailyLimitUsd: 5
          }};
          const key = process.env.TELEGRAPH_PRIVATE_KEY || '0x6f5945dd33eb0725783e2067209e2a5bb62826311e0aea86ec7d7177ec031e1c';
          const payer = new m.Payer(cfg, key);
          const reqBody = {json.dumps({'query': query, **({'intent': intent, 'params': params} if intent else {})})};
          const res = await payer.post('/engine/v1/ask', reqBody);
          console.log(JSON.stringify(res));
        }}).catch(e => console.error(e));
        """
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Telegraph query error: {res.stderr}")
    for line in res.stdout.splitlines():
        if line.startswith("{") and "status" in line:
            return json.loads(line)
    raise RuntimeError(f"Unexpected response from Telegraph node: {res.stdout}")

def evaluate(target_text):
    print("=" * 60)
    print(" 🛡️  TINA: TELEGRAPH AUTONOMOUS VERIFICATION TERMINAL")
    print(f" Target: {target_text[:70]}...")
    print("=" * 60)
    
    # 1. Purchase Content Moderation & Brand Safety Signal
    print("\n[1/2] Purchasing Signal: CONTENT_MODERATION_GENERAL...")
    t0 = time.time()
    mod_res = query_telegraph(f"Evaluate brand safety and consumer risk for: {target_text}")
    print(f" [✓] Settled in {time.time()-t0:.2f}s | Cost: ${mod_res.get('priceUsd', 0.01)}")
    print(f"     Signal Hash: {mod_res.get('body', {}).get('signal_hash')}")
    print(f"     Receipt Hash: {mod_res.get('receipt', {}).get('receipt_hash')}")
    
    time.sleep(1)
    
    # 2. Purchase Entity & Technical Keyword Signal
    print("\n[2/2] Purchasing Signal: KEYWORD_EXTRACTION_GENERAL...")
    t0 = time.time()
    kw_res = query_telegraph(f"Extract key technical entities and salient risk factors from: {target_text}")
    print(f" [✓] Settled in {time.time()-t0:.2f}s | Cost: ${kw_res.get('priceUsd', 0.01)}")
    print(f"     Signal Hash: {kw_res.get('body', {}).get('signal_hash')}")
    print(f"     Receipt Hash: {kw_res.get('receipt', {}).get('receipt_hash')}")
    
    # Synthesize Audit Report
    report = {
        "timestamp": int(time.time()),
        "agent": "Tina v1.0.0",
        "settlement_rail": "Telegraph Escrow (Sepolia)",
        "target": target_text,
        "moderation_verdict": mod_res.get("body", {}).get("result"),
        "key_entities": kw_res.get("body", {}).get("result"),
        "signals": [
            {
                "intent": mod_res.get("body", {}).get("intent"),
                "miner_id": mod_res.get("body", {}).get("miner_id"),
                "signal_hash": mod_res.get("body", {}).get("signal_hash"),
                "receipt_hash": mod_res.get("receipt", {}).get("receipt_hash"),
                "verification_url": f"https://devnode.telegraphprotocol.com/engine/v1/signal/{mod_res.get('body', {}).get('signal_hash')}"
            },
            {
                "intent": kw_res.get("body", {}).get("intent"),
                "miner_id": kw_res.get("body", {}).get("miner_id"),
                "signal_hash": kw_res.get("body", {}).get("signal_hash"),
                "receipt_hash": kw_res.get("receipt", {}).get("receipt_hash"),
                "verification_url": f"https://devnode.telegraphprotocol.com/engine/v1/signal/{kw_res.get('body', {}).get('signal_hash')}"
            }
        ],
        "total_cost_usd": 0.02
    }
    
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    out_file = reports_dir / "audit_memo.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[✓] Audit Report successfully synthesized at {out_file}!")
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tina: Autonomous Telegraph Intelligence Terminal")
    parser.add_argument("--target", type=str, default=DEFAULT_TARGET, help="Target content, ad copy, or transaction to verify")
    args = parser.parse_args()
    evaluate(args.target)
