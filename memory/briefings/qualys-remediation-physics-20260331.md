# Qualys TRU: The Broken Physics of Remediation (2026)

**Source:** Qualys Threat Research Unit | 1B+ CISA KEV records, 10K orgs, 2022-2025
**Date:** March 2026 | PDF: qualys-tru-the-broken-physics-of-remediation.pdf
**Key Stats:** TTE -1 day | KEV vol 6.5x | 88% defender loss rate | <1% of CVEs weaponized

---

## Core Thesis

The patch race is over. Defenders lost.
- Average Time-to-Exploit (TTE): **-1 day** (GTIG/Google, Sep 2025)
- Attackers weaponize before patches exist or at moment of disclosure
- Manual remediation cannot close a gap measured in minutes vs. months
- The mandate: match autonomous offense with autonomous defense

---

## Key Data Points

### Volume Crisis
- KEV vulnerability events closed: 73M (2022) → 473M (2025) = **6.5x growth**
- Critical KEV still open at Day 7: 56% (2022) → **63% (2025)** — WORSE despite more effort
- This is the "human ceiling" — more staffing doesn't fix a broken operational model

### The Physics Gap (52 KEV vulns with complete timelines)
- **88%** of weaponized vulns: defenders patched slower than attackers exploited
- **50%** of weaponized vulns: exploited BEFORE public disclosure
- Avg defender remediation: 21 days | Avg attacker exploitation: <1 day

### The Zero-Day Zone
- Win Kernel EoP (CVE-2024-21338): exploited **182 days** before disclosure
- WinRAR RCE (CVE-2023-38831): weaponized **110 days** early
- ProxyNotShell (CVE-2022-41040): exploited **85 days** before advisory
- Cisco IOS XE: exploited 30 days before Day 0; avg remediation **263 days**

### The Manual Tax
- Spring4Shell: avg is **5.4x** median (49 days median, 266 days avg)
- The tail — forgotten servers, shadow IT, deferred patches — absorbs 4-5x more time than the head

### Asset Class Divide
| Asset Type | Median Close | Challenge |
|---|---|---|
| Endpoints | <14 days | Automated patching works |
| Edge/Perimeter | Weeks-months | Internet-facing, change windows |
| Infrastructure | 116-263 days | Change windows, downtime, manual |

### Risk Mass (Follina/CVE-2022-30190 case study)
- ~33,000 exposure-days from ONE CVE (avg org, 400 assets)
- Blind Spot (pre-disclosure): 12,000 exp-days (36%) — no patch existed
- Sprint (Day 0-23): 6,200 exp-days (19%)
- Long Tail (Day 23+): 14,600 exp-days (44%) — forgotten assets
- **80% of Risk Mass is in the Blind Spot + Long Tail — what dashboards don't measure**

### The Sub-1% Reality
- 2025: 48,172 CVEs disclosed | **357 weaponized** (0.74%)
- CISA KEV: 1,517 of 315,354 all-time = **0.48%**
- Prioritization narrows the haystack. Confirmation finds the real needles.

---

## New Metrics Introduced

1. **AWE (Average Window of Exposure):** Full duration from weaponization to remediation closure across all assets. MTTR ignores the tail; AWE captures it.
2. **Risk Mass:** Vulnerable assets × days exposed = exposure-days. The area under the survival curve. What dashboards measure vs. what actually matters.
3. **ROC (Risk Operations Center):** End-to-end autonomous pipeline: embedded intelligence → active confirmation (exploit-based validation) → autonomous remediation/mitigation.

---

## Implications for DIB/MSSP Context

- DIB orgs (DoD tier 2-4 suppliers) have the same manual ceiling as enterprises
- CMMC compliance posture ≠ actual security — an unpatched vuln counts the same whether mitigated or not
- MSSP clients are relying on human-speed remediation against machine-speed offense
- The "long tail" problem (infrastructure, backup systems) is especially acute for resource-constrained DIB orgs
- CISA KEV is the right baseline but <1% of CVEs demand urgent action — confirmation still required
- The gap between "we know about this CVE" and "we closed it everywhere" is where breaches live

---

## Strategic Takeaways

1. **Stop measuring MTTR as a risk metric** — it rewards the sprint, ignores the tail, and hides the real exposure
2. **Operationalize or accept loss** — autonomous offense requires autonomous defense; human triage is structurally incompatible at TTE -1
3. **Filter twice, act once** — prioritization (KEV, EPSS, TruRisk) narrows to sub-1%. Exploit-based confirmation narrows further to actual environment risk. Only confirmed exploitable gaps trigger autonomous action.
4. **Mitigation is a remediation layer** — for infrastructure with 6-12 month patch cycles, virtual patching / network containment IS the remediation, not a stopgap
5. **Risk Mass is the board metric** — cumulative exposure-days, not CVE counts or MTTR, expresses actual business risk

---

*Filed: 2026-03-31*
