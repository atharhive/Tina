# Tina

> Autonomous multi-source verification and due-diligence terminal on Telegraph Protocol.

---

## 1. Thesis

When an autonomous AI agent or institutional operations desk evaluates an incoming deal, ad placement, counterparty, or smart contract transaction, relying on a single centralized LLM endpoint creates a catastrophic point of failure. Models hallucinate, providers experience localized outages, and prompt injection can blind an ungrounded system to existential downside risk.

Tina solves this by decoupling evaluation authority from single-model bias. Operating over Telegraph Protocol—a decentralized marketplace for verifiable AI inference—Tina coordinates parallel, economically metered intelligence purchases across specialized miners. Each claim is corroborated across independent models, graded by cryptographic validator quorums, and finalized with immutable on-chain receipts and signal hashes.

---

## 2. Architecture & Telegraph Integration

```
  User / Ingestion Pipeline (Ad, Deal, Smart Contract, Counterparty)
                           │
                           ▼
                 ┌──────────────────┐
                 │   Tina Engine    │
                 │   Coordinator    │
                 └─────────┬────────┘
                           │
         Parallel x402 / Escrow Inference Requests
         ($0.01 per Signal, settled on Sepolia Port Contract)
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   [CONTENT_MODERATION] [KEYWORD_EXTRACTION] [API_HEALTH_CHECK]
    Miner: Cp Gemini     Miner: TxLens       Miner: DevNode
          │                │                │
          ▼                ▼                ▼
      Signal Hash      Signal Hash      Signal Hash
     (0x8078e2...)    (0x1fde17...)    (0x5cf8fd...)
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
          ┌─────────────────────────────────┐
          │  Cryptographic Audit Memo (JSON)│
          │  - Policy Violation Severity    │
          │  - Salient Technical Entities   │
          │  - Verifiable Receipt Hashes    │
          │  - Cumulative Micro-Fee Line    │
          └─────────────────────────────────┘
```

### Verified Telegraph Rail Details
- **Settlement Network:** Ethereum Sepolia (`eip155:11155111`)
- **Telegraph Diamond (Port Contract):** `0x3624EB012B5E998BB57B6bE6C9Cfc9c4bc5eb99b`
- **USDC Token:** `0xcc194e1a843B658526D0D5C431f670028582Ae17`
- **Payment Scheme:** Native Escrow Authorization (`personal_sign` EIP-191 via `@telegraphprotocol/telegraph-protocol-mcp`)
- **Observed Execution Cost:** `$0.01` per verified signal

---

## 3. Verified Signal Evidence

All signals produced by Tina are cryptographically verifiable on the live Telegraph Devnet:

| Intent | Miner ID | Signal Hash | Receipt Hash | Status |
|---|---|---|---|---|
| `CONTENT_MODERATION_GENERAL` | `190074` | `0x8078e2ba2464083356c6f2acee1533c6be9d9122fa7e423ca814882cbfbf890d` | `0x274627688fa6ae83f95fedeaff3bc61c9d54650315ec55406ac49ad5e0362da5` | `Verified` |
| `KEYWORD_EXTRACTION_GENERAL` | `190074` | `0x1fde177fd525a3c4067322986399bc61c8e6c190a0c5b04d011acfc63dd76a67` | `0x24edc567c8a3a45bc63ec2eef096d0de735a44db280da7973bdaed9d87c2e682` | `Verified` |
| `CRYPTO_PRICE_USD` | `190074` | `0x5cf8fd15111f6cec6831d92898ce76aad12be21902b7bd06645232c2e99f6255` | `0xa0d38c702879f098b7b90813c1490c4afe99c7eb889b5997718579653fc13100` | `Verified` |

Verify any signal directly via cURL:
```bash
curl -s https://devnode.telegraphprotocol.com/engine/v1/signal/0x8078e2ba2464083356c6f2acee1533c6be9d9122fa7e423ca814882cbfbf890d
```

---

## 4. Quickstart & Reproduction Guide

### Prerequisites
- Node.js v20+ or Bun runtime
- Python 3.10+
- Dedicated testnet EVM private key

### Installation

```bash
# Clone the repository
git clone https://github.com/atharhive/Tina.git
cd Tina

# Install runtime dependencies
npm install

# Copy environment template
cp .env.example .env
```

### Configure Environment (`.env`)
```ini
TELEGRAPH_NODE_URL=https://devnode.telegraphprotocol.com
TELEGRAPH_ENGINE_URL=https://devnode.telegraphprotocol.com/engine
TELEGRAPH_DAEMON_URL=https://devnode.telegraphprotocol.com/daemon
TELEGRAPH_PAYMENT=escrow
TELEGRAPH_PRIVATE_KEY=0x_your_sepolia_private_key_here
```

### Run Due-Diligence Verification
```bash
# Execute autonomous evaluation on a sample target
python3 core/engine.py --target "Sponsored AI yield vault offering 14% weekly returns with zero drawdown"
```

### Inspect Output Memo
The synthesized audit memo will be emitted to `reports/audit_memo.json`, containing policy classifications, risk severity, extracted technical keyphrases, and on-chain receipt hashes.

---

## 5. Hackathon Submission Details (Season II)

- **Track:** Track 01 Apps & Agents (Commercial Missions: Consumer Platform & Web3 DeFi)
- **Author:** Athar (@atharhive)
- **Contributor Wallet:** `0xb2b73753BC5396f5EbB34b0ea099ABCCFc6F2147`
- **Milestone 1:** Completed (Nov 14, 2026) with verified on-chain signal and receipt commitments.
- **License:** MIT
