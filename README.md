# Tina

> Autonomous multi-source verification and due-diligence terminal on Telegraph Protocol.

---

## 1. Thesis

A consumer platform that has to decide whether a claim, link, or offer is trustworthy faces a practical problem: a single model can be wrong, stale, or unavailable. Paying for specialist intelligence can help, but only if the request, answer, cost, and limits are visible and testable.

Tina is an early prototype exploring that workflow through Telegraph. The current code is deliberately in **dry-run mode**. It does not yet make paid requests, corroborate independent answers, or produce current receipts. Those capabilities are goals, not shipped behavior.

---

## 2. Current implementation

The repository contains a small Python CLI. By default it prints the supplied target and reports a dry-run status without making network requests or spending funds. `--execute` is intentionally disabled until a safe live flow is verified.

The live request helper is not enabled from the CLI. Any future implementation must use a fresh, unexposed test wallet, the exact live Intent schema, a verified price/quote, explicit spending ceilings, and auditable response evidence. No current per-signal price is claimed.

---

## 3. Evidence status

The repository previously listed three signal/receipt pairs as live-verifiable. As of **November 17, 2026**, the public Devnode returns `signal not found` for the documented moderation signal. Those historical identifiers are therefore not presented here as currently verified evidence. The app has not yet demonstrated a reproducible, current Telegraph purchase with a result and verifiable accounting record from a fresh input.

Track 2 is separate: the public evaluation API currently reports this contributor's existing rows as eligible (20 moderation, 6 keyword extraction, 6 grammar/spell-check). Pool snapshots and eligibility are not proof of prize payment or earnings.

Before using a new signal as proof, verify it against the current public endpoint and record the returned request, result, network, actual price, and available receipt/accounting evidence. Do not infer settlement from an HTTP 200 or a payment challenge.

---

## 4. Run the safe prototype

### Requirements
- Python 3.10+

```bash
git clone https://github.com/atharhive/Tina.git
cd Tina
python3 core/engine.py --target "Suspicious sponsored offer promising guaranteed weekly returns"
```

Expected behavior: prints `DRY RUN: no requests sent and no funds spent.` No key, Node dependency, or network connection is needed for this path. `--execute` currently exits without making a request.

---

## 5. Project status

Tina is an unfinished prototype and is not currently a qualifying, independently reproducible paid Telegraph application. The original Consumer Platform mission issue is #195; it is currently claimed by another contributor, so this repository does not claim that mission. The team has not verified a fresh paid app flow or a prize award.

The existing evaluation submissions are a separate Track 2 contribution. As of November 17, 2026, the public API reports 20 eligible moderation rows, 6 eligible keyword-extraction rows, and 6 eligible grammar/spell-check rows for the contributor. This is not a payout confirmation.

## License

MIT. See [LICENSE](LICENSE). See also `.env.example` for configuration names; never commit real credentials.
