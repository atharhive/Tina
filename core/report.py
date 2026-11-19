"""Run evidence: every paid call, its receipt, and a memo a reviewer can audit."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_run(report: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    """Persist a flow result as run.json, understand.json, and memo.md."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{report['workflow']}-{stamp}"
    report = {**report, "run_id": run_id, "generated_at": datetime.now(timezone.utc).isoformat()}

    run_path = out_dir / f"{run_id}.json"
    run_path.write_text(json.dumps(report, indent=2))

    memo_path = out_dir / f"{run_id}.md"
    memo_path.write_text(render_memo(report))

    # A tiny, human-friendly copy of just the decision, for dashboards and tests.
    decision_path = out_dir / f"{run_id}.verdict.json"
    decision_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "workflow": report["workflow"],
                "mission": report.get("mission"),
                "input": report.get("input"),
                "verdict": report["verdict"],
                "cost_usd": report.get("cost_usd"),
                "gaps": report.get("gaps"),
            },
            indent=2,
        )
    )
    _append_index(out_dir, report, run_path)
    return {"run": run_path, "memo": memo_path, "verdict": decision_path}


def _append_index(out_dir: Path, report: dict[str, Any], run_path: Path) -> None:
    """Keep one small index so a reviewer can see every run without opening them all."""
    index_path = out_dir / "index.json"
    try:
        rows = json.loads(index_path.read_text())
        if not isinstance(rows, list):
            rows = []
    except Exception:  # noqa: BLE001 - a missing index starts empty
        rows = []
    rows.append(
        {
            "run_id": report["run_id"],
            "workflow": report["workflow"],
            "mission": report.get("mission"),
            "verdict": report["verdict"]["verdict"],
            "risk_score": report["verdict"]["risk_score"],
            "cost_usd": report.get("cost_usd"),
            "generated_at": report["generated_at"],
            "file": run_path.name,
        }
    )
    index_path.write_text(json.dumps(rows[-200:], indent=2))


def render_memo(report: dict[str, Any]) -> str:
    verdict = report["verdict"]
    lines: list[str] = []
    lines.append(f"# Tina verification memo: {report['workflow']}")
    lines.append("")
    lines.append(f"- Mission: {report.get('mission', 'n/a')}")
    lines.append(f"- Verdict: **{verdict['verdict']}** (risk {verdict['risk_score']}/100)")
    lines.append(f"- Cost of this outcome: ${report.get('cost_usd', 0):.4f} USDC (escrow, testnet)")
    lines.append(f"- Rail: Telegraph escrow on Ethereum Sepolia; each answer carries a receipt")
    lines.append("")
    lines.append("## Input")
    for key, value in (report.get("input") or {}).items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    economics = (verdict.get("economics") or {}) if isinstance(verdict, dict) else {}
    if economics.get("margin_usd_per_day") is not None:
        lines.append("")
        lines.append("## Numbers")
        for key, label in (
            ("hashrate_ph", "hashrate (PH/s)"),
            ("efficiency_j_per_th", "efficiency (J/TH)"),
            ("power_kw", "power draw (kW)"),
            ("revenue_usd_per_day", "revenue (USD/day)"),
            ("power_cost_usd_per_day", "power cost (USD/day)"),
            ("margin_usd_per_day", "margin (USD/day)"),
            ("margin_pct", "margin (%)"),
            ("breakeven_lmp_usd_per_mwh", "break-even power price (USD/MWh)"),
        ):
            if economics.get(key) is not None:
                lines.append(f"- {label}: {economics[key]:,}")

    lines.append("")
    lines.append("## Why")
    for reason in verdict.get("reasons") or ["no risk factors triggered"]:
        lines.append(f"- {reason}")
    excluded = report.get("excluded") or []
    if excluded:
        lines.append("")
        lines.append("## Bought but set aside")
        lines.append("These answers were paid for and priced a different market than the zone asked about:")
        for row in excluded:
            lines.append(f"- {row.get('miner')} (id {row.get('miner_id')}): {row.get('market') or 'no market label'}, zone {row.get('zone') or 'unlabelled'}")

    lines.append("")
    lines.append("## What was bought")
    for obs in report.get("observations", []):
        lines.append("")
        lines.append(f"### {obs['intent']}")
        lines.append(f"params `{json.dumps(obs['params'])}` - asked {obs['asked']}, answered {obs['answered']}, cost ${obs['cost_usd']:.4f}")
        if obs.get("error"):
            lines.append(f"gap: {obs['error']}")
        for answer in obs.get("answers", []):
            status = "answered" if answer["status"] == 200 else f"failed ({answer.get('error')})"
            lines.append(
                f"- miner {answer.get('miner_name') or '?'} (id {answer.get('miner_id')}): {status}, "
                f"${answer.get('price_usd', 0):.4f}"
            )
            if answer.get("result"):
                lines.append(f"  - result: `{json.dumps(answer['result'])[:400]}`")
            if answer.get("receipt"):
                receipt = answer["receipt"]
                keys = ", ".join(f"{k}={receipt[k]}" for k in list(receipt)[:4])
                lines.append(f"  - receipt: {keys}")
            if answer.get("signal_hash"):
                lines.append(f"  - signal hash: `{answer['signal_hash']}`")
    lines.append("")
    lines.append("## Limits of this memo")
    lines.append(
        "- Answers are bought opinions from independent miners, not ground truth. Agreement is evidence "
        "about consistency, not correctness."
    )
    lines.append("- Prices are the node's quoted testnet prices; no mainnet settlement is claimed.")
    lines.append("- A failed ask is never billed; the cost shown is what the node actually charged.")
    return "\n".join(lines) + "\n"
