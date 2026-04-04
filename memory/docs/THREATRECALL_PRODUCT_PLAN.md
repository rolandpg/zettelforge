# ThreatRecall — Product Architecture & Roadmap
**Version:** 2.2
**Status:** Active
**Created:** 2026-04-01 | **Rebuilt:** 2026-04-02 | **Updated:** 2026-04-03
**Owner:** Patrick Roland
**Classification:** Confidential (Tier 3 per GOV-021)
**Governance Alignment:** GOV-001 through GOV-022

---

# PART 1: CURRENT STATE

## 1. What Exists Today

ThreatRecall is a cybersecurity-native agent memory system built on A-MEM architecture with proprietary extensions for threat intelligence operations. The system is operational on an ASUS Ascent DGX Spark GB10 (128GB unified memory, self-funded ~$6,000).

### 1.1 Memory System — Phases 1-5.5 Complete

| Component | Status | Evidence |
|---|---|---|
| A-MEM Core (construct, link, evolve, retrieve) | Operational | 167 notes in production |
| Entity Indexer (CVE, actors, tools, campaigns, sectors) | Complete | 27 entities indexed |
| Entity-Guided Linking | Complete | 5/5 tests passing |
| Date-Aware Retrieval (supersedes tracking) | Complete | 3/3 tests passing |
| Mid-Session Snapshot Refresh | Complete | 2/2 tests passing |
| Cold Archive to USB-HDD | Complete | 3/3 tests passing |
| Alias Auto-Update (AliasManager, 3-observation threshold) | Complete | 7/7 tests passing |
| Epistemic Tiering (Tier A/B/C with evolution enforcement) | Complete | 10/10 tests passing |
| Tier-Aware Evolution (REJECT on B to A, NO_CHANGE on C to anything) | Complete | Integrated into Phases 1-5 |
| Reasoning Memory (audit trail for all decisions) | Complete | 9/9 tests passing |
| LanceDB Vector Store | Operational | 103-271ms avg retrieval |
| nomic-embed-text-v2-moe Embeddings (768-dim, local) | Operational | Local inference on DGX Spark |
| Confidence Scoring and Decay (evolution hop limit: 5) | Operational | Integrated |
| Daily/Weekly Maintenance (systemd timers) | Operational | 06:00 CDT daily, Friday 23:00 weekly |
| LLM Model (enrichment + evolution) | **Upgraded** | `qwen2.5:3b` (10x faster than nemotron-3-nano) |
| Parallel Evolution Processing | **New** | ThreadPoolExecutor — 16x end-to-end speedup |

**Total test coverage: 143/143 passing** (33 Phases 1-5 + 7 Phase 3.5 + 10 Phase 4.5 + 9 Phase 5.5 + 36 Phase 6 + 21 Phase 7 + 11 Integration + 6 Performance)

### 1.2 Governance Framework — 22 Documents

A full enterprise engineering governance framework targeting FedRAMP Moderate, CMMC Level 2, NIST 800-171, and NIST 800-53 compliance:

| Document | Scope |
|---|---|
| GOV-001 SDLC Policy | 8-phase lifecycle with gates |
| GOV-002 Version Control | Git workflow, conventional commits |
| GOV-003 Python Coding Standards | Style, patterns, tooling |
| GOV-004 Rust Coding Standards | Future language support |
| GOV-005 API Design Standards | REST conventions, response envelopes, error format, pagination |
| GOV-006 Code Review Standards | Approval requirements, checklist |
| GOV-007 Testing Standards | pytest, 80% line / 70% branch coverage |
| GOV-008 CI/CD Pipeline Standards | Quality gates, deployment automation |
| GOV-009 Dependency Management | Approval, updates, license compliance |
| GOV-010 Release Management | Semantic versioning, changelog |
| GOV-011 Security Development Lifecycle | Threat modeling, SAST/DAST, secure coding |
| GOV-012 Observability and Logging | OCSF v1.3 schema, CMMC-aligned audit events |
| GOV-013 Environment Management | Topology, access tiers, data parity |
| GOV-014 Secrets Management | HashiCorp Vault (local) + Azure Key Vault (cloud) |
| GOV-015 Technical Debt Management | Identification, prioritization, remediation |
| GOV-016 RFC/Design Document Template | Significant change proposals |
| GOV-017 Onboarding Guide | New engineer setup |
| GOV-018 Azure Cloud Configuration | Commercial, GCC-High, DoD endpoint resolution |
| GOV-019 FedRAMP Moderate Alignment | Control mapping to all governance docs |
| GOV-020 ADR Template | Architecture decision records |
| GOV-021 Data Classification | Tier 1 (Public) through Tier 4 (CUI) |
| GOV-022 Incident Response | Development-specific incident procedures |

This framework maps every governance document to specific FedRAMP/NIST controls and identifies the audit evidence each produces. Compliance evidence is a natural output of following the governance processes.

### 1.3 Phase 6 — Complete ✅

Phase 6 (Ontology, Knowledge Graph, and FIRST IEP 2.0 Governance) is **complete** with 36/36 tests passing. Key capabilities delivered:
- Ontology-validated relationships (USES, TARGETS, EXPLOITS, MITIGATES, GOVERNS, APPLIES_TO, RESTRICTS)
- IEP 2.0 policy nodes with full HASL schema
- IEP-filtered retrieval
- Multi-hop graph traversal
- Temporal policy overlap resolution
- Graph persistence (45 nodes, 128 edges)

**Test Results:** 36/36 tests passing (124.3s)

### 1.4 Phase 7 — Complete ✅

Phase 7 (Synthesis Layer / RAG-as-Answer) is **complete** with 21/21 tests passing. Implements LLM-based answer synthesis using vector retrieval + knowledge graph traversal:
- Hybrid retrieval (vector + graph)
- 4 response formats: direct_answer, synthesized_brief, timeline_analysis, relationship_map
- Quality scoring and confidence thresholds
- Source citation with relevance scores

**Test Results:** 21/21 tests passing (89.7s)

### 1.5 Performance Optimization — Parallel Evolution ✅

Implemented **parallel evolution assessment** reducing `remember()` latency from ~48s to ~3s (16x speedup):
- LLM model upgraded: `nemotron-3-nano` → `qwen2.5:3b` (10x faster per call)
- ThreadPoolExecutor for parallel assessment (5.9x speedup)
- Candidate cap optimized: 20 → 10 (quality vs performance balance)
- End-to-end `remember()` time: **~3 seconds** (interactive-ready)

**Documentation:** See `PARALLEL_EVOLUTION.md` for full technical details.

### 1.6 What Remains Before First Pilot

| Gap | Status | Required For | Estimated Effort | Governance Ref |
|---|---|---|---|---|
| ~~Bug fixes (alias collision, atomic writes, soft-pass tests, rollback)~~ | ✅ **Complete** | ~~Burn-in start~~ | — | GOV-011 |
| ~~Phase 6 implementation (ontology, knowledge graph, IEP)~~ | ✅ **Complete** | ~~Differentiation~~ | — | GOV-016 |
| ~~Phase 7 implementation (synthesis layer)~~ | ✅ **Complete** | ~~Differentiation~~ | — | GOV-016 |
| 30-day burn-in test | 🔄 **In Progress (concurrent)** | Operational proof metrics | 30 days | GOV-007 |
| Secrets abstraction (Vault/Key Vault/env) | ✅ **Complete** | Production auth | 4-6 hours | GOV-014 |
| API layer (FastAPI, auth, tenant isolation) | 🔄 **In Progress** | Product access | 40-60 hours | GOV-005 |
| OpenAPI 3.1 spec (contract-first per GOV-005) | 🔄 **In Progress (TR-API-001 drafted)** | API documentation | 8-12 hours | GOV-005 |
| OCSF-schema audit logging | 🔄 **Partial (middleware stub + structlog)** | Compliance requirement | 6-8 hours | GOV-012 |
| Dockerfile + deployment pipeline | Pending | Deployment | 4-6 hours | GOV-008 |
| THIRD_PARTY_NOTICES file | Pending | Legal compliance | 2 hours | IP Risk Register |
| Customer-facing docs + Python SDK | Pending | Onboarding | 8-12 hours | GOV-005 |

---

# PART 2: STRATEGIC POSITIONING

## 2. Why the Governance Framework Is the Moat

Every horizontal memory provider (Mem0, MemGPT, MemOS) is a developer tool. They sell to engineers who want to add memory to an AI chatbot. Their documentation covers installation, API calls, and model configuration.

ThreatRecall sells to MSSPs and enterprise SOCs in the Defense Industrial Base. These buyers do not ask "does it work?" first. They ask "how do you build your software?" and "can you pass our vendor security assessment?" and "does this align with CMMC?"

The 22-document governance framework answers all of those questions before the first sales call. It maps to FedRAMP Moderate, CMMC Level 2, NIST 800-171, and NIST 800-53. It specifies OCSF-schema audit logging that is natively compatible with Microsoft Sentinel. It defines data classification tiers that handle CUI. It mandates Azure GCC-High and DoD cloud endpoint support.

No competitor has this. Mem0 raised $24M and has 80,000 developers. They do not have a FedRAMP alignment document. They do not have OCSF logging. They do not have a data classification policy. They cannot sell to the DIB sector without building all of this from scratch.

## 3. Competitive Landscape

| Competitor | Positioning | Strengths | Weakness vs ThreatRecall |
|---|---|---|---|
| Mem0 | Horizontal memory for all AI apps | $24M funded, 80K devs, AWS exclusive | No security domain, no compliance framework, no IEP, no entity resolution, no MITRE mapping, cannot sell to DIB |
| A-MEM (academic) | Research prototype | NeurIPS 2025 paper | No production features, no governance, no commercial intent |
| MemGPT / Letta | Virtual context management | Tiered memory hierarchy | Generic paging, no security enrichment, no compliance |
| ThreatRecall | FedRAMP-aligned cybersecurity agent memory | Entity indexing, alias resolution, MITRE mapping, epistemic tiering, IEP governance, knowledge graph, 22-doc compliance framework, DIB operator credibility | Pre-revenue, API layer in progress |

---

# PART 3: API ARCHITECTURE (GOV-005 ALIGNED)

## 4. API Design Principles

All API design follows GOV-005 API Design Standards:

- URL Pattern: `https://{host}/api/v1/{resource}` with plural nouns, kebab-case
- Response Envelope: All responses wrapped in `{ "data": {...}, "meta": {...} }`
- Error Format: Structured error objects with UPPER_SNAKE_CASE codes
- Pagination: Cursor-based exclusively (no offset/limit per GOV-005)
- Auth: Bearer token in Authorization header, mandatory on all endpoints except health
- Rate Limiting: Headers on every response (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
- Request ID: UUID v4 on every request, in response body and logs
- Contract-First: OpenAPI 3.1 spec at api/openapi.yaml before implementation
- Logging: All API activity logged as OCSF class 6002 events per GOV-012

## 5. API Endpoint Specification

### 5.1 Memory Operations

**POST /api/v1/memories** — Store a new memory note through the full pipeline.
Maps to: mm.remember(content, source_type, source_ref)

Request body includes: content (required), source_type (for tier assignment), source_ref (traceability), iep_policy_id (optional, links to IEP policy).

Response includes data envelope with: note_id, status (created or duplicate_skipped), tier, entities (canonical post-alias-resolution), links_created, evolution_triggered, duplicate_of, iep_policy_id. Meta envelope includes: request_id, timestamp, latency_ms.

Duplicate response returns status duplicate_skipped with duplicate_of note ID and similarity reason.

Error responses follow GOV-005 format with error code, message, details array, request_id, and documentation_url.

**GET /api/v1/memories** — Semantic recall with optional IEP filter.
Maps to: mm.recall(query, k, expand_links)

Query parameters: q (search query), page_size (default 25, max 100), cursor (opaque), expand_links (boolean), iep_min_tlp (green/amber/red/white filter).

Response includes data array with notes (each containing note_id, content, semantic, metadata with tier, similarity_score, iep_policy_id), meta with expanded_from_links count and iep_filter_applied, and pagination with cursor and has_more.

### 5.2 Entity Recall

**GET /api/v1/actors/{name}** — Recall by actor with alias resolution.
Maps to: mm.recall_actor(name)

Response includes: query_alias, canonical_name, mitre_id, known_aliases array, notes array (each with tier), total_notes.

**GET /api/v1/cves/{cve_id}** — Recall by CVE.
**GET /api/v1/tools/{name}** — Recall by tool with alias resolution.
**GET /api/v1/campaigns/{name}** — Recall by campaign.
**GET /api/v1/sectors/{name}** — Recall by sector.

All follow the same response envelope pattern.

### 5.3 Alias Resolution

**GET /api/v1/aliases/resolve/{entity_type}/{name}** — Resolve a name to canonical.
Maps to: resolver.resolve(entity_type, name)

Response includes: input, entity_type, canonical, mitre_id, all_aliases.

**GET /api/v1/aliases/{entity_type}** — List all canonical entities and alias counts.

### 5.4 Knowledge Graph (Phase 6)

**POST /api/v1/graph/traverse** — Multi-hop graph traversal with optional IEP filter.
Request body: start_entity, relationship_path array, iep_filter object, max_hops.
Response: traversal results with entity chains showing each hop.

**GET /api/v1/graph/shareable?min_tlp={level}** — IEP-filtered retrieval.
**GET /api/v1/graph/nodes/{entity_type}** — List graph nodes by type.
**GET /api/v1/graph/edges/{entity}** — List edges for an entity.
**GET /api/v1/graph/export?format={dot|json}** — Graph visualization export.

### 5.5 IEP Policy Management

**POST /api/v1/iep-policies** — Create FIRST IEP 2.0 policy (immutable after creation per Section 4.4).
Request includes all 12 required HASL fields plus optional external_references.

**GET /api/v1/iep-policies** — List all policies.
**GET /api/v1/iep-policies/{id}** — Get specific policy.
**PUT /api/v1/iep-policies/{id}** — Returns 409 CONFLICT (immutable).
**GET /api/v1/iep-policies/{id}/notes** — Notes governed by this policy.

### 5.6 Reasoning and Audit Trail

**GET /api/v1/reasoning/{note_id}** — Full decision audit trail for a note.
Maps to: logger.get_reasoning(note_id)
Response includes event array with tier_assignment, link_created, evolution_decision events.

### 5.7 Entity Statistics

**GET /api/v1/entities/stats** — Entity index statistics.

### 5.8 Administration

**GET /api/v1/health** — No auth. Service health, note count, entity count, uptime.
**POST /api/v1/admin/rebuild-index** — Force entity index rebuild.
**POST /api/v1/admin/reload-aliases** — Hot-reload alias maps.
**GET /api/v1/admin/maintenance-status** — Last maintenance results.

---

# PART 4: IMPLEMENTATION ARCHITECTURE

## 6. Project Structure

```
threatrecall/
  api/
    openapi.yaml              # Contract-first spec (GOV-005)
    main.py                   # FastAPI app, middleware, startup
    routes/
      memories.py             # POST/GET /api/v1/memories
      actors.py               # GET /api/v1/actors/{name}
      cves.py                 # GET /api/v1/cves/{id}
      tools.py                # GET /api/v1/tools/{name}
      aliases.py              # GET /api/v1/aliases/*
      graph.py                # POST/GET /api/v1/graph/*
      iep_policies.py         # POST/GET /api/v1/iep-policies/*
      reasoning.py            # GET /api/v1/reasoning/{note_id}
      entities.py             # GET /api/v1/entities/stats
      admin.py                # health, rebuild, reload
    middleware/
      auth.py                 # API key validation via SecretsProvider
      request_id.py           # UUID v4 request ID injection
      rate_limit.py           # Per-tenant rate limiting + headers
      ocsf_logger.py          # OCSF class 6002 API activity logging
    tenants.py                # Tenant routing and isolation
    models.py                 # Pydantic request/response schemas
    errors.py                 # Structured error responses (GOV-005)
  memory/                      # EXISTING CODE
    memory_manager.py
    entity_indexer.py
    alias_resolver.py
    alias_manager.py
    link_generator.py
    memory_evolver.py
    reasoning_logger.py
    note_constructor.py
    note_schema.py
    memory_store.py
    vector_retriever.py
    vector_memory.py
    alias_maps/
    ontology_schema.json       # Phase 6
    ontology_validator.py      # Phase 6
    knowledge_graph.py         # Phase 6
    graph_retriever.py         # Phase 6
    iep_policy.py              # Phase 6
  secrets/
    provider.py                # SecretsProvider abstraction (GOV-014)
    vault_provider.py          # HashiCorp Vault backend
    keyvault_provider.py       # Azure Key Vault backend
    env_provider.py            # Dev/test only
  logging/
    ocsf.py                    # OCSF event formatters (GOV-012)
  config/
    settings.py                # App config, Azure cloud resolver (GOV-018)
  tenants/                     # Per-customer data (gitignored, Tier 3)
  tests/
    unit/                      # ~70% per GOV-007
    integration/               # ~20% per GOV-007
    e2e/                       # ~10% per GOV-007
  governance/                  # GOV-001 through GOV-022
  burnin/                      # 30-day burn-in test data
  Dockerfile
  docker-compose.yml
  requirements.txt
  THIRD_PARTY_NOTICES
  CHANGELOG.md                 # Per GOV-010
  README.md
```

## 7. Authentication Architecture (GOV-014 Aligned)

API keys stored in the secrets backend, not in config files. Application resolves secrets source at startup via SECRETS_BACKEND environment variable:

- Development/homelab: SECRETS_BACKEND=vault (local HashiCorp Vault)
- Cloud production: SECRETS_BACKEND=azure-keyvault (Azure Key Vault)
- CI/testing only: SECRETS_BACKEND=env (environment variables, never in production)

For the MVP and first 3 pilots, SECRETS_BACKEND=env is acceptable. The abstraction layer is in place from day one so the migration to Vault/Key Vault is a configuration change, not a code change.

## 8. Audit Logging (GOV-012 Aligned)

Every API request generates an OCSF class 6002 (API Activity) event with class_uid, activity_name, severity_id, status_id, UTC timestamp, api operation and version, http_request method and url, http_response code, actor tenant_id, and product metadata.

Authentication events use OCSF class 3001. Authorization failures use OCSF class 3003. These are natively ingestible by Microsoft Sentinel without custom parsers.

## 9. Data Classification (GOV-021 Aligned)

| Data Type | Tier | Handling |
|---|---|---|
| Threat intelligence notes (customer data) | Tier 3 (Confidential) | Encrypted at rest, encrypted in transit (TLS 1.2+), tenant-isolated, access-logged |
| Alias maps (shared reference data) | Tier 2 (Internal) | Access controlled, not customer-specific |
| IEP policy definitions | Tier 2 (Internal) | Shared reference data per FIRST CC-BY-SA |
| API keys and tenant credentials | Tier 3 (Confidential) | Vault/Key Vault only, never in logs/code/config |
| Audit logs (OCSF events) | Tier 2 (Internal) | Must not contain Tier 3 data values per GOV-021 |
| Customer CUI data (if applicable) | Tier 4 (CUI) | NIST 800-171, Azure GCC-High/DoD only, FIPS 140-2 |

## 10. Deployment Targets (GOV-018 Aligned)

| Environment | Cloud | Use Case | Compliance |
|---|---|---|---|
| Development / Homelab | Local (DGX Spark) | Building and burn-in | N/A |
| Pilot (Phase C) | Azure Commercial or Cloudflare Tunnel | First 3 non-CUI customers | Tier 3 handling |
| Production Commercial | Azure Commercial | Non-DIB customers | FedRAMP-equivalent |
| Production GCC-High | Azure Government GCC-High | DIB customers with CUI | FedRAMP Moderate, CMMC L2 |
| Production DoD | Azure Government DoD (IL5) | DoD customers | FedRAMP High, IL5 |

Single codebase supports all environments via AZURE_CLOUD environment variable per GOV-018.

---

# PART 5: PRODUCT ROADMAP

## 11. Release Plan

### v0.1.0 — Internal Proof (Target: May 2026)
Fix Patton bug findings. Rerun all 59 tests. Start 30-day burn-in with real threat intel feeds.
Success: Burn-in report with hard operational metrics.

### v0.2.0 — Phase 6 Complete (Target: July 2026)
Implement ontology, knowledge graph, IEP policy layer. All 13 Phase 6 tests passing. Total: 72/72 tests.
Write technical whitepaper with burn-in metrics and Phase 6 capabilities.
Success: Whitepaper with hard numbers.

### v0.3.0 — API Layer (Target: October 2026)
OpenAPI 3.1 spec (contract-first). FastAPI with GOV-005 response envelopes, error format, pagination. Auth via SecretsProvider. Tenant isolation. OCSF audit logging. Docker container.
Success: All endpoints return GOV-005 compliant responses. Container runs.

### v0.4.0 — Pilot-Ready (Target: December 2026)
Deploy to Azure or Cloudflare Tunnel. HTTPS with TLS 1.2+. Customer docs and Python SDK.
Success: Customer engineer stores first memory within 30 minutes of reading docs.

### v0.5.0 — Production (Target: March 2027)
Usage metering. Rate limiting enforcement. Admin dashboard. Secrets migration to Vault.
Success: Customers paying, uptime tracked.

### v1.0.0 — General Availability (Target: Q3 2027)
Self-service signup. Stripe billing. Azure GCC-High option for DIB/CUI. SOC 2 Type I docs.
Success: Customer signs up, pays, uses ThreatRecall without talking to Patrick.

## 12. Pricing Tiers

| Tier | Monthly | Includes |
|---|---|---|
| Starter | $3,000 | Memory core + CVE dedup + entity indexing. 10K ops/month. |
| Professional | $8,000 | + alias resolution + MITRE mapping + tiering + evolution + IEP. 50K ops/month. |
| Enterprise | $15,000+ | + knowledge graph + custom alias maps + IEP-filtered retrieval + GCC-High + SLA. Unlimited. |

## 13. Revenue Forecast

| Quarter | Customers | Avg MRR/Cust | MRR | ARR Run Rate |
|---|---|---|---|---|
| Q1 2027 | 3 (pilot) | $0 | $0 | $0 |
| Q2 2027 | 5 paid | $6,000 | $30K | $360K |
| Q3 2027 | 7 | $7,000 | $49K | $588K |
| Q4 2027 | 10 | $8,000 | $80K | $960K |

---

# PART 6: BUILD SEQUENCE

## 14. Ordered Implementation Checklist

| Step | What to Build | Hours | Status | Gov Ref |
|---|---|---|---|---|
| 1-4 | Alias resolver, wiring, dedup, acceptance tests | Done | ✅ COMPLETE (59/59) | GOV-007 |
| 5 | Fix Patton 4 bug findings (alias rollback) | 4-6 | ✅ **COMPLETE** — Commit db8da6e | GOV-011 |
| 6 | Rerun all tests (now 143) | 1 | ✅ COMPLETE | GOV-007 |
| 7 | Start 30-day burn-in | 30 days | 🔄 **CONCURRENT** | GOV-007 |
| 8 | Implement Phase 6 (ontology, graph, IEP) | 30-50 | ✅ **COMPLETE** — 36/36 tests | GOV-016 |
| 9 | Phase 6 tests | 8-12 | ✅ COMPLETE (124.3s) | GOV-007 |
| 9b | Implement Phase 7 (synthesis layer) | 20-30 | ✅ **COMPLETE** — 21/21 tests | GOV-016 |
| 9c | Parallel evolution optimization | 4-6 | ✅ **COMPLETE** — 16x speedup | GOV-016 |
| 10 | Technical whitepaper | 8-12 | 🔄 **READY** (unblocked) | -- |
| 11 | OpenAPI 3.1 spec (contract-first) | 8-12 | After 9 | GOV-005 |
| 12 | data_dir parameter on MemoryManager | 1 | After 9 | -- |
| 13 | .to_dict() on note objects | 1 | After 9 | -- |
| 14 | secrets/provider.py abstraction | 3 | After 9 | GOV-014 |
| 15 | logging/ocsf.py formatters | 4 | After 9 | GOV-012 |
| 16 | api/middleware/ (auth, request_id, rate_limit, ocsf) | 6 | After 14,15 | GOV-005 |
| 17 | api/routes/memories.py | 4 | After 13,16 | GOV-005 |
| 18 | api/routes/ entity recall (actors, cves, tools) | 4 | After 17 | GOV-005 |
| 19 | api/routes/aliases.py | 2 | After 16 | GOV-005 |
| 20 | api/routes/graph.py | 4 | After 9,16 | GOV-005 |
| 21 | api/routes/iep_policies.py | 3 | After 9,16 | GOV-005 |
| 22 | api/routes/reasoning.py | 2 | After 16 | GOV-005 |
| 23 | api/routes/entities.py + admin.py | 2 | After 16 | GOV-005 |
| 24 | api/main.py | 2 | After 17-23 | GOV-005 |
| 25 | API test suite (80% line / 70% branch) | 6 | After 24 | GOV-007 |
| 26 | Dockerfile + docker-compose.yml | 3 | After 25 | GOV-008 |
| 27 | Container build and verify | 2 | After 26 | GOV-008 |
| 28 | THIRD_PARTY_NOTICES | 2 | Any time | IP Register |
| 29 | Customer docs + Python SDK | 8-12 | After 25 | GOV-005 |
| 30 | Deploy to Azure or Cloudflare Tunnel | 4 | After 27 | GOV-018 |
| 31 | Onboard first pilot customer | 4 | After 29,30 | -- |

Critical path: Steps 5-9c (bug fixes, Phase 6/7, parallel evolution) are **COMPLETE**. **Burn-in and API development run concurrently** — burn-in does not gate API progress. API layer is Steps 11-27 (~55-70 hours). Secrets abstraction (Step 14) is complete. OpenAPI spec (Step 11) is in draft. At 15-20 hrs/week, first pilot approximately **2-3 months** from today.

---

# PART 7: COMPLIANCE AS A PRODUCT FEATURE

## 15. What Customers Get That Competitors Cannot Provide

Technical product: Cybersecurity agent memory with entity indexing, alias resolution, epistemic tiering, knowledge graph with IEP governance, and an audit trail for every decision.

Compliance package: 22-document governance framework mapping to FedRAMP Moderate, CMMC Level 2, NIST 800-171. Customer compliance teams review GOV-019 and see exactly which controls ThreatRecall satisfies. Auditors see automated evidence collection.

Operational alignment: OCSF-schema audit logs ingestible by Microsoft Sentinel. Azure GCC-High deployment for CUI. Data classification aligned with CMMC. IEP policies enforcing sharing restrictions at the data layer.

No other agent memory provider offers any of this.

## 16. THIRD_PARTY_NOTICES Requirements

| Component | License | Required |
|---|---|---|
| A-MEM reference implementation | MIT | Copyright notice + MIT license text |
| LanceDB | Apache 2.0 | License + NOTICE file + state modifications |
| nomic-embed-text | Apache 2.0 | License + attribution |
| FIRST IEP 2.0 Framework | CC-BY-SA | Attribution to FIRST, share-alike on derived IEP specs |
| MITRE ATT&CK | CC-BY 4.0 | Attribution when distributing MITRE data |
| Pydantic | MIT | Copyright notice |
| Ollama client | MIT | Copyright notice |

---

*End of document. Version 2.0 supersedes all previous versions.*
*Governance alignment verified against GOV-001 through GOV-022 as of 2026-04-02.*
