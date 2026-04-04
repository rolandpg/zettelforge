# Fleet Growth Plan — Vigil & Nexus Deployment

**Date:** 2026-04-03
**Status:** Research Complete — Pending Patrick Confirmation
**Plan Owner:** Patton
**Stakeholders:** Tamara (social coordination), Patrick (final scope approval)

---

## Executive Summary

Two new agents proposed for Roland Fleet expansion:

1. **Vigil** — CTI Analyst (Priority 1): Dedicates analyst capacity to threat intelligence pipeline
2. **Nexus** — AI Infrastructure Researcher (Priority 2): Ensures tech stack remains cutting-edge

Both agents integrate with existing governance framework (22 GOV documents) and coordinate with existing fleet members.

---

## Part 1: Vigil — CTI Analyst Agent

### Role Definition
Dedicated threat intelligence analyst focused on CVE triage, actor profiling, and alert drafting. Bridges the gap between raw CTI collection and publication-ready content.

### Core Responsibilities

| Function | Daily Tasks | Outputs |
|----------|-------------|---------|
| **KEV Triage** | Monitor CISA KEV at 06:00 CDT | Prioritized list with EPSS/CVSS scoring |
| **CVE Analysis** | Review NVD releases, flag DIB-relevant | Vulnerability briefs with exploitation context |
| **Actor Profiling** | Track MOIS, China-Nexus, ransomware groups | APT profile drafts with ATT&CK mapping |
| **Alert Queue** | Maintain and curate alert backlog | 3-5 queued items/week for Patrick review |
| **Intel Threads** | Draft X thread content for high-priority items | Draft posts (no publish without approval) |

### Success Metrics
- Alert-to-draft latency: <4 hours for High EPSS (>0.5)
- Thread drafts queued: 3/week minimum
- False positive rate: <10% (measured against Patrick's final edits)
- DIB relevance score: 90%+ of queued items must map to DIB sector

### Resource Requirements

**Workspace:** `~/.openclaw/workspace-vigil/`

**Shared Resources:**
- Read access: `~/cti-workspace/data/cti/cti.db` (Django CTI DB)
- Read access: `~/.openclaw/workspace/memory/` (context)
- Read access: `~/.openclaw/workspace/SKILL.md` (tools reference)

**Dedicated Resources:**
- SQLite/hot cache for working memory
- `~/.openclaw/workspace-vigil/fleet/vigil_daily.md` (sync file)
- `~/.openclaw/workspace-vigil/briefs/` (intel briefs output)

### Governance Integration

**Required GOV Document Training (Priority Order):**

| Priority | Document | Why Required |
|----------|----------|--------------|
| 1 | GOV-021 DATA-CLASSIFICATION-POLICY.md | CTI data handling, TLP markings |
| 2 | GOV-011 SECURITY-DEVELOPMENT-LIFECYCLE.md | Secure coding for intel tools |
| 3 | GOV-003 CODING-STANDARDS-PYTHON.md | Collector scripts in Python |
| 4 | GOV-012 OBSERVABILITY-LOGGING-STANDARDS.md | OCSF logging for intel activities |
| 5 | GOV-002 VERSION-CONTROL-POLICY.md | Git workflow for intel updates |

**Compliance Notes:**
- CTI data classification: Most intel is TLP:AMBER or TLP:GREEN
- No raw IOCs in version control — only processed/anonymized
- All briefs must include source reliability ratings (per FIRST CTI-SIG)

### Coordination Protocol

**With Patton (Me):**
- Daily sync via `fleet/vigil_daily.md` (mirrors Patton/Tamara pattern)
- Escalate critical alerts immediately (CISA KEV + active exploitation)
- Weekly briefing: Friday 12:00 CDT

**With Tamara:**
- Queue thread drafts to `~/.openclaw/workspace-vigil/drafts/x_threads/`
- Tamara pulls drafts for scheduling and engagement optimization
- Coordination on: timing, tone, PE/VC audience targeting

**With Patrick:**
- No external publication without explicit approval
- Weekly review meeting: Friday 14:00 CDT (suggested)
- Alert notifications: High EPSS + DIB relevance = immediate flag

### Deployment Phases

| Phase | Duration | Milestone |
|-------|----------|-----------|
| **Phase 1: Bootstrap** | Day 1-2 | Workspace creation, SOUL.md, governance training |
| **Phase 2: Integration** | Day 3-5 | CTI DB access, collector familiarization, test runs |
| **Phase 3: Shadow** | Week 2 | Parallel analysis with Patton verification |
| **Phase 4: Autonomous** | Week 3+ | Independent operation with periodic review |

### Technical Stack

**Languages:** Python 3.11+ (matches existing collectors)
**Databases:** SQLite (working), Django ORM (read-only CTI DB)
**Key Libraries:** pandas (analysis), requests (APIs), python-stix2 (STIX handling)
**Models:** Local Ollama for entity extraction (matches privacy requirements)

---

## Part 2: Nexus — AI Infrastructure Researcher

### Role Definition
Cutting-edge technology scout focused on AI/ML infrastructure, deployment patterns, and emerging capabilities. Mission: ensure ThreatRecall and fleet tech stack remains current without technical debt or obsolescence.

### Core Responsibilities

| Function | Activities | Outputs |
|----------|------------|---------|
| **Model Tracking** | Monitor new releases (Llama, Mistral, Gemma, etc.) | Capability assessment briefs |
| **Quantization Research** | Track GGUF, AWQ, GPTQ, EXL2 developments | Performance/cost trade-off analysis |
| **Edge Deployment** | Research on-device inference, mobile optimization | Deployment recommendations |
| **Hardware Acceleration** | Track CUDA, ROCm, Apple Silicon, NPUs | Hardware selection guidance |
| **Agent Frameworks** | Monitor OpenClaw, LangChain, AutoGPT evolution | Migration/upgrade recommendations |
| **Cost Optimization** | Analyze inference costs, token economics | Budget impact projections |

### Success Metrics
- Technology briefs: 2/week minimum
- Upgrade recommendations: Monthly synthesis report
- Obsolescence warnings: 30-day advance notice for critical dependencies
- Implementation guides: Quarterly deep-dive on priority technology

### Research Priorities (Q2 2026)

1. **Embedding Model Evolution** — nomic-embed-text-v2-moe alternatives, multimodal embeddings
2. **Local LLM Optimization** — llama.cpp advancements, speculative decoding, continuous batching
3. **RAG Architecture Patterns** — query routing, hybrid search, re-ranking strategies
4. **Agent Orchestration** — multi-agent patterns, state management, coordination protocols
5. **Observability for AI** — LLM tracing, cost attribution, performance monitoring

### Resource Requirements

**Workspace:** `~/.openclaw/workspace-nexus/`

**Shared Resources:**
- Read access: `~/.openclaw/workspace/` (fleet context)
- Read access: `~/.openclaw/workspace-tamara/` (social strategy alignment)

**Dedicated Resources:**
- Research notes: `~/.openclaw/workspace-nexus/research/`
- Benchmark data: `~/.openclaw/workspace-nexus/benchmarks/`
- Weekly reports: `~/.openclaw/workspace-nexus/reports/`

### Governance Integration

**Required GOV Document Training:**

| Priority | Document | Why Required |
|----------|----------|--------------|
| 1 | GOV-009 DEPENDENCY-MANAGEMENT-POLICY.md | Dependency approval for new tools |
| 2 | GOV-014 SECRETS-MANAGEMENT-POLICY.md | API key handling for research tools |
| 3 | GOV-015 TECHNICAL-DEBT-MANAGEMENT.md | Obsolescence assessment criteria |
| 4 | GOV-016 RFC-DESIGN-DOCUMENT-TEMPLATE.md | Technology adoption proposals |
| 5 | GOV-007 TESTING-STANDARDS.md | Benchmark methodology standards |

### Coordination Protocol

**With Patton:**
- Weekly research digest: Monday 09:00 CDT
- Immediate flag for critical vulnerabilities in dependencies
- RFC coordination for architecture changes

**With Tamara:**
- AI tooling insights for social content (when relevant)
- Coordination on: AI industry trends, thought leadership angles

**With Patrick:**
- Monthly deep-dive: 30-min briefing on strategic technology shifts
- Ad-hoc consultation: When technology decisions required

---

## Part 3: Fleet Coordination Structure

### Communication Matrix

| From \ To | Patrick | Patton | Tamara | Vigil | Nexus |
|-----------|---------|--------|--------|-------|-------|
| **Patrick** | — | Direct | @tamaraSM_bot | Via Patton | Via Patton |
| **Patton** | Direct | — | sessions_send | file sync | file sync |
| **Tamara** | Via Patton | sessions_send | — | Via Patton | Via Patton |
| **Vigil** | Via Patton | file sync | Via Patton | — | file sync |
| **Nexus** | Via Patton | file sync | Via Patton | file sync | — |

### Shared Resources Plan

Current model (isolated workspaces) scales to 4-5 agents. Beyond that, migrate to:

```
~/.openclaw/fleet-shared/
├── governance/          # GOV docs (single source)
├── memory/             # Cross-agent memory (read-only for most)
├── tools/              # Shared skills and scripts
├── ctidb/              # CTI database (read-only access)
└── sync/               # Fleet sync files (per-agent subdirs)
```

### Governance Enforcement

All new agents must:

1. **Complete governance training** — read and acknowledge GOV docs
2. **Cite GOV document IDs** in code comments when applicable
3. **Follow naming conventions** — snake_case for modules (GOV-003)
4. **Use OCSF logging** — structured observability (GOV-012)
5. **No secrets in code** — HashiCorp Vault when available (GOV-014)
6. **Version control discipline** — feature branches, semantic commits (GOV-002)

---

## Part 4: Deployment Checklist

### Pre-Deployment (Patton)

- [ ] Confirm scope with Patrick
- [ ] Create workspaces: `workspace-vigil/`, `workspace-nexus/`
- [ ] Bootstrap SOUL.md files for both agents
- [ ] Copy governance docs to each workspace
- [ ] Set up systemd timers for daily operations
- [ ] Configure CTI DB read access for Vigil

### Vigil Bootstrap

- [ ] Write `SOUL.md` — CTI analyst persona
- [ ] Read GOV-021, GOV-011, GOV-003 (governance training)
- [ ] Familiarize with CTI DB schema
- [ ] Test collector access (CISA KEV, NVD)
- [ ] Draft first alert queue entry

### Nexus Bootstrap

- [ ] Write `SOUL.md` — technology researcher persona
- [ ] Read GOV-009, GOV-014, GOV-015 (governance training)
- [ ] Set up research monitoring (RSS, GitHub, arXiv)
- [ ] Establish benchmark baseline (current stack)
- [ ] Draft first technology brief

### Post-Deployment

- [ ] First week: shadow mode with Patton verification
- [ ] Second week: supervised autonomy
- [ ] Third week: full autonomous operation
- [ ] Monthly: performance review against metrics

---

## Appendices

### A. Governance Quick Reference

**GOV-003 Python Naming:**
- Modules: `snake_case`
- Classes: `PascalCase`
- Functions: `snake_case` with verb prefix
- Constants: `UPPER_SNAKE_CASE`

**GOV-012 OCSF Logging:**
- Event type: `activity_id`
- Severity: `severity_id` (1-6 scale)
- Actor: `actor` (user/process context)

**GOV-021 Data Classification:**
- TLP:RED — Strictly controlled
- TLP:AMBER — Limited distribution
- TLP:GREEN — Community sharing
- TLP:WHITE — Public

### B. Vigil Intel Thread Template

```
{Confidence} {EPSS/CVSS} | {probability language} exploitation
{actor if known} using {CVE}
{ATT&CK technique chain}
{key IOCs if actionable}
Source: {source} | Reliability: {A-F rating}
Link: {NVD/KEV link}
```

### C. Nexus Research Brief Template

```
# Technology: {name}
**Date:** {YYYY-MM-DD}
**Status:** {researching | evaluating | recommended | deprecated}
**Priority:** {critical | high | medium | low}

## Summary
{2-3 sentence overview}

## Capability Assessment
{what it does, how it works}

## Relevance to Fleet
{specific use cases for Roland Fleet}

## Cost/Performance Analysis
{quantified trade-offs}

## Migration Path
{if applicable}

## Recommendation
{adopt | evaluate further | defer | reject}
```

---

**Next Action:** Await Patrick scope confirmation before proceeding with deployment.
