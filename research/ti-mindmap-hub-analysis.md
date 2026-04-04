# TI Mindmap HUB — Architecture Analysis

**Source:** https://github.com/TI-Mindmap-HUB-Org/ti-mindmap-hub-research  
**Analysis Date:** 2026-04-03  
**Analyst:** Patton (Roland Fleet)

---

## Executive Summary

TI Mindmap HUB is a production CTI platform using LLM-driven analysis of OSINT sources. They solve several problems Patrick has already tackled (STIX 2.1, IOC extraction, TTP mapping) but with architectural patterns worth studying. Their **MCP server approach** and **multi-agent weekly briefing system** are immediately relevant to Roland Fleet expansion.

---

## Their Architecture (6-Stage Pipeline)

```
Stage 1: Content Acquisition
├─ Curated OSINT source monitoring
├─ Analyst URL submissions (web + MCP)
└─ Validation, deduplication, tracking ID

Stage 2: Normalization
├─ HTML stripping → clean text
├─ Metadata preservation (source, date, URL)
├─ Entity extraction (LLM + pattern matching)
└─ Confidence scoring (high/medium/low)

Stage 3: Threat Analysis (5 parallel branches)
├─ IOC Detection: Regex + LLM → validation → whitelist filtering
├─ TTP Extraction: LLM behavioral analysis → ATT&CK mapping
├─ CVE Extraction: Pattern matching → CVSS/EPSS enrichment
├─ Actor/Malware: Named entity extraction → relationship mapping
└─ Summary Synthesis: Technical summary + mindmap + 5W analysis

Stage 4: STIX 2.1 Structuring
├─ Object assembly (Report, ThreatActor, Malware, Indicator, etc.)
├─ Relationship generation (indicates, uses, attributed-to, exploits)
├─ Bundle validation (STIX schema, reference integrity)
└─ Storage

Stage 5: Frontend Delivery (Per-Article)
├─ Header Metadata
├─ Intel Graph (interactive STIX)
├─ Diamond Model
├─ AI Summary + TI Mindmap
├─ IOCs (high/med confidence, JSON export)
├─ CVEs (with risk context)
├─ TTP Catalog + Attack Flow
├─ ATT&CK Heatmap
└─ Source Report

Stage 6: Weekly Briefing (Multi-Agent)
├─ Collector Agent: Aggregate 50-60 weekly reports
├─ Analyst Agents: Parallel subset analysis
├─ Trend Agent: Pattern identification
├─ Synthesis Agent: Final briefing
└─ Editor Agent: Review/refine
```

---

## Patterns Worth Adopting

### 1. MCP Server Architecture (HIGH PRIORITY)

**What they do:** Expose 19 tools via Model Context Protocol for AI assistant integration.

**Tools categories:**
- Reports (list, get, search, submit)
- Weekly briefings (get, list)
- IOC search (by indicator, by report)
- CVE intelligence (by ID, search)
- STIX bundles (get, validate)
- Platform stats

**Why it matters for Roland Fleet:**
- Vigil could expose CTI data to Claude/Cursor/Copilot for analyst workflows
- Patrick queries CTI DB directly from IDE while writing detection rules
- Standardized protocol instead of custom API wrappers

**Implementation path:**
```
1. Build MCP server wrapping Django CTI models
2. Tools: search_iocs, get_actor_profile, get_cve_analysis, query_stix
3. Deploy alongside existing Django app
4. Connect Patrick's Cursor/Copilot to local MCP endpoint
```

### 2. Multi-Agent Weekly Briefing System (HIGH PRIORITY)

**What they do:** AutoGen-based multi-agent system processing 50-60 reports/week.

**Agent roles:**
- Collector: Aggregation
- Analyst (multiple): Parallel subset processing
- Trend: Pattern identification
- Synthesis: Final output
- Editor: Quality control

**Why it matters:**
- Vigil currently does solo KEV triage. Multi-agent pattern scales to:
  - Cross-report actor correlation
  - TTP trending across time
  - Sector targeting pattern analysis
  - Automated weekly briefings for Patrick

**Implementation path:**
```
1. Use Roland Fleet A2A messaging (sessions_send)
2. Vigil as Collector → distributes to Analyst agents
3. Nexus as Trend agent → identifies emerging techniques
4. Patton as Synthesis/Editor → final briefing
5. Tamara for content formatting if external-facing
```

### 3. Confidence Scoring Pipeline (MEDIUM PRIORITY)

**What they do:** Every extracted entity gets confidence (high/medium/low) with validation layers.

**Validation examples:**
- IOCs: Format validation, private range exclusion, TLD check
- TTPs: ATT&CK ID verification against database
- STIX: Schema compliance, reference integrity

**Current Roland Fleet gap:**
- Vigil has source reliability (A-F) and confidence (High/Med/Low) per FIRST CTI-SIG
- But no systematic validation pipeline for IOC extraction
- False positives (common domains, RFC 5737 IPs) not filtered

**Implementation:**
```
1. Add IOC validation layer to vigil_collect.py
2. Whitelist: google.com, microsoft.com, cloud provider ranges
3. Private IP exclusion: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
4. RFC 5737 doc ranges: 192.0.2.x, 198.51.100.x, 203.0.113.x
```

### 4. Structured Output Frontend (MEDIUM PRIORITY)

**What they do:** Per-article tabbed interface with 10+ structured views.

**Tabs:** Intel Graph, Diamond Model, AI Summary, Mindmap, IOCs, CVEs, TTP Catalog, Attack Flow, 5W Context, ATT&CK Heatmap, Source

**Current Roland Fleet state:**
- Django admin + basic HTML dashboard
- No interactive STIX graph
- No mindmap visualization
- No ATT&CK heatmap

**Implementation:**
```
1. STIX graph: Use stix2viz or custom D3.js
2. Mindmap: Mermaid.js (they use this)
3. ATT&CK heatmap: MITRE's attack-navigator or custom grid
4. Diamond model: Simple 4-quadrant visualization
```

### 5. Report-Centric STIX Bundles (LOW PRIORITY — Already Done)

**What they do:** Each report generates a complete STIX bundle with relationships.

**Bundle structure:**
```
Bundle
├── Report (SDO) — container
├── ThreatActor(s) (SDO)
├── Malware (SDO)
├── Indicator(s) (SDO) — IOCs with STIX patterns
├── AttackPattern(s) (SDO) — ATT&CK techniques
├── Vulnerability (SDO) — CVEs
└── Relationship(s) (SRO) — connects objects
```

**Roland Fleet status:** ✅ Already implemented in Django models (IOC, ThreatActor, CVE, Sector, ThreatAlert)
**Gap:** Need STIX export endpoint for bundles

---

## Technology Stack Comparison

| Component | TI Mindmap HUB | Roland Fleet |
|-----------|----------------|--------------|
| LLM | OpenAI GPT-4 / Azure | Local (Ollama/llama.cpp) |
| Backend | Python, Azure Functions | Python, Django |
| Database | Azure Cosmos DB | SQLite (Django) |
| Frontend | React, TypeScript | Django templates + basic HTML |
| Auth | Azure AD B2C | None (local homelab) |
| Hosting | Azure | Local DGX Spark |
| Protocol | MCP server | None yet |
| Multi-agent | AutoGen | OpenClaw native A2A |

---

## Recommendations

### Immediate (This Week)

1. **MCP Server Prototype**
   - Wrap Django CTI models with MCP protocol
   - Start with 3 tools: search_iocs, get_actor_profile, get_cve_analysis
   - Test with Patrick's Cursor IDE

2. **IOC Validation Layer**
   - Add whitelist filtering to vigil_collect.py
   - Implement confidence scoring for extracted IOCs
   - Document per GOV-012 (OCSF logging)

### Short-term (Next 2 Weeks)

3. **Multi-Agent Weekly Briefing Pilot**
   - Vigil aggregates weekly KEV + NVD + THN data
   - Sessions_send to Patton for synthesis
   - Test A2A coordination pattern

4. **STIX Export Endpoint**
   - Add `/api/stix/bundle/<report_id>` to Django
   - Validate against cti-stix2-validator
   - Test import into MISP/OpenCTI

### Medium-term (Next Month)

5. **Interactive Frontend Views**
   - STIX relationship graph (D3.js)
   - ATT&CK heatmap
   - Diamond model visualization

6. **Knowledge Graph Construction**
   - Cross-report correlation (their "Future Research Direction #1")
   - Link actors across multiple campaigns
   - Longitudinal TTP trending

---

## Files Referenced

- `docs/concepts/methodology.md` — 6-stage pipeline
- `docs/concepts/data-model.md` — STIX 2.1 generation
- `docs/mcp/index.md` — MCP server architecture
- `schemas/stix-examples/example-apt-campaign.json` — Bundle format

---

## Open Questions

1. Should Roland Fleet expose an MCP server, or consume external MCP servers (like TI Mindmap HUB's)?
2. Does Patrick want interactive frontend visualizations, or is API-only sufficient?
3. Priority: Weekly multi-agent briefings vs. MCP server vs. knowledge graph?

---

*Analysis complete. Ready for implementation planning.*
