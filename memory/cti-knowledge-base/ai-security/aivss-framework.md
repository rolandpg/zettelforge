# AIVSS — Agentic AI Vulnerability Scoring System
**Source:** OWASP AIVSS v0.8 (2026-03) — https://aivss.owasp.org/
**Status:** Active framework for scoring AI agent security risks

---

## The Core Insight: Force Multiplier Concept

Traditional vulnerabilities have a static impact ceiling. Agentic AI systems act as **force multipliers** — autonomy, tool use, and persistence expand the blast radius of any underlying technical flaw.

**Key formula:**
```
AIVSS = (CVSS_Base + AARS) * Mitigation_Factor

AARS = (10 - CVSS_Base) * (Factor_Sum / 10) * Threat_Multiplier
```

Where Factor_Sum = sum of 10 agentic amplification factors (0.0 to 1.0 each, max 10.0)

---

## The 10 Agentic Amplification Factors

| Factor | What It Measures |
|--------|-----------------|
| Autonomy | Executes actions without human co-sign |
| Tools | Breadth/privilege of external APIs and tools |
| Language | Reliance on natural language for goal formulation |
| Context | Use of environmental sensors/broad data context |
| Non-Determinism | Variance in output for identical inputs |
| Opacity | Lack of internal visibility or auditability |
| Persistence | Retains memory across sessions |
| Identity | Dynamic role/permission assumption at runtime |
| Multi-Agent | Coordination with other autonomous agents |
| Self-Mod | Ability to alter own code, prompts, or tools |

---

## The 10 OWASP Agentic AI Core Risks (Ranked by Severity)

1. **Agentic AI Tool Misuse** — Autonomy + Tools + Language
2. **Agent Access Control Violation** — Tools + Identity + Persistence
3. **Agent Cascading Failures** — Autonomy + Multi-Agent + Non-Determinism + Opacity
4. **Agent Orchestration and Multi-Agent Exploitation** — Autonomy + Identity + Multi-Agent + Context
5. **Agent Identity Impersonation** — Identity + Opacity + Language
6. **Agent Memory and Context Manipulation** — Persistence + Context + Opacity
7. **Insecure Agent Critical Systems Interaction** — Autonomy + Tools + Context + Self-Mod
8. **Agent Supply Chain and Dependency Risk** — All factors, esp. Autonomy + Tools + Self-Mod
9. **Agent Untraceability** — Opacity + Identity + Non-Determinism
10. **Agent Goal and Instruction Manipulation** — Language + Autonomy + Non-Determinism + Context

---

## Critical Finding: Low CVSS Can = High AIVSS

| Risk | CVSS Base | AIVSS Final |
|------|-----------|-------------|
| Goal Manipulation | 2.1 (Low) | **7.1** (High) |
| Memory Manipulation | 5.8 (Medium) | **8.9** (High) |
| Cascading Failures | 7.1 (High) | **9.4** (Critical) |
| Orchestration Exploitation | 9.4 (Critical) | **10.0** (Critical) |

**Implication:** A CVSS 2.1 prompt injection in an agent with high autonomy + memory + context = AIVSS 7.1. The agentic deployment context is the primary risk driver, NOT the underlying technical vulnerability.

---

## Key Attack Scenarios (Real-World Relevance)

### Tool Misuse
- MCP server tool squatting for covert data exfiltration
- Rogue A2A server impersonation for unauthorized communication
- Agentic privilege abuse for destructive system integrity compromise (legitimate commands with catastrophic scope)

### Access Control
- Memory poisoning → GitHub Copilot leaks private repo data into public issues
- Cross-repository data exfiltration via GitHub MCP prompt injection
- Temporal permission drift (admin role persists 30 min after task completion)

### Cascading Failures
- Malicious MCP tool metadata → market analysis agents trigger cascading failures across trading systems
- Data poisoning → agentic systems propagate erroneous decisions network-wide

### Multi-Agent Exploitation
- Rogue agent masquerading as legitimate data validation service
- Task spoofing: impersonating authorized research requests to export patient data
- Token replay attacks on long-running DevOps automation agents

### Memory Manipulation
- Long-term memory poisoning: "user convenience prioritizes security" → agent bypasses security rules
- RAG data poisoning via email prompt injection
- Multi-session conditioning: fragments of malicious rules accumulate into high-priority override

### Critical Systems
- Water treatment plant sabotage via poisoned log file → agent bypasses static safety limits
- CI/CD pipeline takeover via prompt-injected pull request → agent injects malicious step into CircleCI config
- Data center infiltration via falsified IoT temperature sensor → agent unlocks secure room for physical access

---

## Defensive Recommendations (From AIVSS)

1. **Kill switches** — Network-isolated, infrastructure-level, not software commands the agent can ignore
2. **Tool allowlisting** — Centralized inventory of all tools, capabilities, permissions, usage policies
3. **Memory isolation** — User context segregation, TTL enforcement on shared memory objects
4. **Human-in-the-loop** — Autonomous commits only in sandbox/non-critical paths
5. **Behavioral monitoring** — Model and agent behavior monitoring for early IOC detection
6. **DLP inspection** — Automated scanning of agent interactions and tool outputs
7. **Cryptographic role attestation** — Signed tokens, verifiable credentials for role assertions

---

## Relevance to Summit 7 / Vigilance

**Advisory opportunity:** DIB clients deploying AI agents need AIVSS-style risk assessments before production. Current security reviews don't account for:
- Autonomous chaining of low-severity vulns into catastrophic outcomes
- Memory poisoning as a persistent, hard-to-detect attack vector
- Multi-agent orchestration blast radius

**CTI angle:** Check Point already documented AI agents autonomously escalating privileges. AIVSS provides the scoring framework to tell that story quantitatively.

**PE thesis:** MSSP consolidation + CMMC expertise + AI security assessment = differentiated advisory offering.

---

*Framework: OWASP AIVSS v0.8 (2026-03)*
*Key references: MITRE ATLAS, NIST AI RMF, CSA MAESTRO, OWASP LLM Top 10*
