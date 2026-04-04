# Psyche (NousNet) - Security & Privacy Assessment
**Date:** 2026-03-29
**Repo:** PsycheFoundation/nousnet
**Classification:** OPEN SOURCE - RUN AT YOUR OWN RISK

## Executive Summary
Psyche is a distributed training platform for transformer-based AI models using peer-to-peer networking (iroh) and Solana blockchain for coordination/payments. **Significant security and privacy concerns** for production deployment.

---

## Security Concerns

### 1. CRITICAL: Model Weights Exposed to Peers
**Severity: HIGH**

The entire premise of the system involves distributing model parameters (weights) between untrusted peers over the internet. Each participant downloads model shards from other participants.

```
Risk: Your model weights (intellectual property) are shared with unknown parties.
Attack surface: Any peer in the network can receive your gradient updates or model parameters.
```

**What happens:**
- Participants share model parameters via iroh (P2P)
- Gradients are exchanged between untrusted parties
- No verification that peers aren't harvesting model weights

**Recommendation:** If running private training, this is a deal-breaker. Model IP WILL be distributed to the network.

### 2. MEDIUM: Solana Integration - Smart Contract Risk
**Severity: MEDIUM**

```
Programs: solana-coordinator, solana-treasurer, solana-authorizer, solana-distributor
Language: Anchor (Rust)
```

Smart contracts on Solana are irreversible. Issues include:
- Program upgrade authority (can they upgrade after deployment?)
- Reentrancy vulnerabilities in reward distribution
- Token handling in solana-treasurer (SOL or SPL tokens)

**Recommendation:** Audit Anchor programs before any mainnet deployment.

### 3. MEDIUM: Iroh P2P Networking
**Severity: MEDIUM**

The iroh library handles:
- Direct peer-to-peer connections (QUIC)
- Relay servers for NAT traversal
- Blob storage and transfer

**Concerns:**
```
- relay.iroh.network (and iroh.world) - relay servers used for NAT traversal
- Endpoint IDs are public keys (not pseudonymous by default)
- Connection metadata exposed to relay servers
```

**Configuration in code:**
```rust
iroh::{Endpoint, RelayConfig}
iroh_gossip - gossip protocol for peer discovery
```

### 4. MEDIUM: External Dependencies
**Severity: MEDIUM**

Significant dependency surface:

| Dependency | Purpose | Risk |
|-----------|---------|------|
| iroh v0.97 | P2P networking | Unknown security posture |
| anchor | Solana programs | Well-audited but complex |
| tch-rs | PyTorch bindings | Research-grade |
| OpenTelemetry | Metrics | Standard, but sends data out |

### 5. LOW: Agenix Secrets Management
**Severity: LOW**

Secrets encrypted with SSH keys via agenix:
```
secrets/devnet/wallet.age
secrets/devnet/rpc.age
secrets/mainnet/rpc.age
```

Good practice for repo secrets. However:
- Secrets are encrypted for multiple dev keys (allDevKeys)
- Mainnet RPC URLs could be sensitive

---

## Privacy Concerns

### 1. CRITICAL: Training Data Exposure
**Severity: CRITICAL**

Participants exchange:
- Model gradient updates (reveals training data patterns)
- Model parameters (full IP theft possible)
- Dataset shards via data-provider module

**No privacy preservation** built in. Gradient updates can reveal training data (see literature on gradient inversion attacks).

### 2. MEDIUM: OpenTelemetry Metrics
**Severity: MEDIUM**

The system has OpenTelemetry integration for metrics:

```rust
// shared/metrics/src/iroh.rs
use opentelemetry::{
    metrics::{Counter, Gauge, Meter},
};
```

**Concern:** Metrics may include:
- Peer endpoint IDs
- Connection patterns
- Training progress
- Bandwidth/latency measurements

**Recommendation:** Disable OTel export in production or route to internal collector only.

### 3. MEDIUM: Blockchain Transparency
**Severity: MEDIUM**

All transactions on Solana are public:
- Training participation rewards
- Coordinator state changes
- Participant claims

**If using real tokens (not just devnet):** All financial activity is publicly linkable to wallet addresses.

### 4. MEDIUM: IP/Network Information
**Severity: MEDIUM**

P2P networking reveals:
- IP addresses to peers
- Connection timing patterns
- Bandwidth characteristics

### 5. LOW: Git History
**Severity: LOW**

Full commit history is available:
```
git clone https://github.com/PsycheFoundation/nousnet
```
All historical code, commits, and development patterns visible.

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Psyche Network                          │
├─────────────────────────────────────────────────────────────┤
│  Participant A          │  Coordinator  │  Participant B │
│  ┌─────────┐             │   (on-chain)  │  ┌─────────┐    │
│  │ Model   │◄──P2P──►   │  ┌─────────┐   │  │ Model   │    │
│  │ Weights │   (iroh)   │  │ Solana  │   │  │ Weights │    │
│  └─────────┘             │  │Programs │   │  └─────────┘    │
│  ┌─────────┐             │  └─────────┘   │  ┌─────────┐    │
│  │Training │              │                │  │Training │    │
│  │ Data    │◄──Data──►   │  ┌─────────┐   │  │ Data    │    │
│  └─────────┘   Provider  │  │Treasury│   │  └─────────┘    │
│                          │  └─────────┘                    │
│  ┌─────────┐             │                │  ┌─────────┐    │
│  │Metrics │───OTel───►  │                │  │Metrics │     │
│  └─────────┘             │                │  └─────────┘    │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │ relay.iroh.network │
          │ (NAT traversal)  │
          └──────────────────┘
```

---

## Threat Model

### External Adversaries
| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| Model IP theft via P2P | HIGH | CRITICAL | Don't use for proprietary models |
| Network surveillance | MEDIUM | HIGH | Use VPN/Tor |
| Metrics exfiltration | LOW | MEDIUM | Disable OTel |

### Malicious Peers
| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| Gradient harvesting | HIGH | CRITICAL | Not designed to prevent |
| Poisoning training | MEDIUM | HIGH | Verify checkpoint signatures |
| Free-riding | MEDIUM | LOW | Economic incentives in Solana programs |

### Smart Contract Risks
| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| Reward drainage | LOW | HIGH | Audit Anchor programs |
| Unauthorized upgrades | UNKNOWN | HIGH | Verify upgrade authority |

---

## Recommendations

### Before Any Deployment

1. **DO NOT** use for proprietary or sensitive model training
2. **Audit Anchor programs** (solana-treasurer, coordinator, etc.)
3. **Disable OTel** or route to internal collector
4. **Use devnet only** until programs are audited
5. **Review iroh security model** - relay servers see connection metadata

### For Testing/Research
```bash
# Use isolated network namespace
ip netns add psyche-test

# Run with no network access to peers
# (only connect to known-good participants)
```

### For Production
- **Wait** for formal security audit
- Consider **alternative** with better privacy guarantees (e.g., secure aggregation)

---

## Files Analyzed
- `Cargo.toml` - workspace dependencies
- `flake.nix` - nix configuration
- `secrets.nix` - secret management (agenix)
- `shared/network/src/` - P2P networking (iroh)
- `shared/metrics/src/iroh.rs` - OpenTelemetry integration
- `architectures/decentralized/solana-*/` - blockchain programs

---

## Verdict

**For DIB/Enterprise Use:** **NOT RECOMMENDED**

The fundamental design distributes model weights and gradients to untrusted P2P participants. This is incompatible with protecting intellectual property or training data privacy.

**For Research/Personal:** Acceptable risk with proper isolation.

**The blockchain integration** adds complexity without solving the core security issues of distributed training.
