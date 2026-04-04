---
document_id: GOV-000
title: Governance Documentation Index
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [index, governance, navigation, onboarding, documentation-map]
---

# Governance Documentation Index

## Purpose

This index serves as the master navigation document for all software engineering governance documentation. It provides reading orders for different audiences, a quick-reference mapping of common questions to specific documents, and metadata about the documentation package itself.

## Document Registry

| Doc ID | Document | Purpose | Primary Audience |
|--------|----------|---------|-----------------|
| GOV-001 | SDLC-POLICY.md | Software Development Lifecycle phases, gates, and responsibilities | All engineering staff |
| GOV-002 | VERSION-CONTROL-POLICY.md | Git workflow, branching strategy, commit standards | All engineering staff |
| GOV-003 | CODING-STANDARDS-PYTHON.md | Python style, patterns, tooling, and conventions | Python developers |
| GOV-004 | CODING-STANDARDS-RUST.md | Rust style, patterns, tooling, and conventions | Rust developers |
| GOV-005 | API-DESIGN-STANDARDS.md | REST API conventions, versioning, error formats, Azure endpoint configs | API developers, integrators |
| GOV-006 | CODE-REVIEW-STANDARDS.md | Review process, approval requirements, checklist | All engineering staff |
| GOV-007 | TESTING-STANDARDS.md | Test types, coverage requirements, frameworks, naming | All engineering staff |
| GOV-008 | CICD-PIPELINE-STANDARDS.md | Pipeline stages, quality gates, deployment automation | DevOps, all engineering staff |
| GOV-009 | DEPENDENCY-MANAGEMENT-POLICY.md | Dependency approval, updates, license compliance, vulnerability response | All engineering staff |
| GOV-010 | RELEASE-MANAGEMENT-POLICY.md | Versioning, release cadence, changelog, hotfix process | Release managers, all engineering staff |
| GOV-011 | SECURITY-DEVELOPMENT-LIFECYCLE.md | Threat modeling, secure coding, SAST/DAST, SDL gates | All engineering staff, security team |
| GOV-012 | OBSERVABILITY-LOGGING-STANDARDS.md | OCSF schema logging, CMMC-aligned audit, metrics, tracing | All engineering staff, security team |
| GOV-013 | ENVIRONMENT-MANAGEMENT-POLICY.md | Environment topology, access controls, data handling, parity | DevOps, all engineering staff |
| GOV-014 | SECRETS-MANAGEMENT-POLICY.md | HashiCorp Vault and Azure Key Vault integration, rotation, access | All engineering staff, security team |
| GOV-015 | TECHNICAL-DEBT-MANAGEMENT.md | Debt identification, categorization, prioritization, remediation | Tech leads, all engineering staff |
| GOV-016 | RFC-DESIGN-DOCUMENT-TEMPLATE.md | Template for proposing significant technical changes | All engineering staff |
| GOV-017 | ONBOARDING-GUIDE.md | New engineer setup, system access, first-week tasks | New engineering hires |
| GOV-018 | AZURE-CLOUD-CONFIGURATION.md | Azure endpoint configurations for Commercial, GCC-High, and DoD clouds | All engineering staff, DevOps |
| GOV-019 | FEDRAMP-MODERATE-ALIGNMENT.md | FedRAMP Moderate control mapping to governance documents | Compliance, security team, leadership |
| GOV-020 | ADR-TEMPLATE.md | Architecture Decision Record template and process | All engineering staff |
| GOV-021 | DATA-CLASSIFICATION-POLICY.md | Data handling tiers, labeling, storage, and transmission rules | All engineering staff |
| GOV-022 | INCIDENT-RESPONSE-DEVELOPMENT.md | Development-specific incident response for security and availability events | All engineering staff, on-call |

## Suggested Reading Orders

### New Engineer (First Week)

Read in this order to go from zero to productive:

1. GOV-017 ONBOARDING-GUIDE.md (setup and access)
2. GOV-001 SDLC-POLICY.md (understand the process)
3. GOV-002 VERSION-CONTROL-POLICY.md (how to commit and branch)
4. GOV-003 or GOV-004 CODING-STANDARDS (your primary language)
5. GOV-006 CODE-REVIEW-STANDARDS.md (how your code gets reviewed)
6. GOV-007 TESTING-STANDARDS.md (what tests to write)
7. GOV-014 SECRETS-MANAGEMENT-POLICY.md (never commit secrets)

### LLM Context Loading (Priority Order)

For injecting governance context into an LLM agent, load in this order until context window is full:

1. GOV-005 API-DESIGN-STANDARDS.md (API contracts and patterns)
2. GOV-003 or GOV-004 CODING-STANDARDS (relevant language)
3. GOV-002 VERSION-CONTROL-POLICY.md (commit and branch conventions)
4. GOV-012 OBSERVABILITY-LOGGING-STANDARDS.md (logging patterns)
5. GOV-014 SECRETS-MANAGEMENT-POLICY.md (security constraints)
6. GOV-018 AZURE-CLOUD-CONFIGURATION.md (cloud endpoint configs)

### Compliance Auditor

1. GOV-019 FEDRAMP-MODERATE-ALIGNMENT.md (control mapping)
2. GOV-011 SECURITY-DEVELOPMENT-LIFECYCLE.md (SDL process)
3. GOV-021 DATA-CLASSIFICATION-POLICY.md (data handling)
4. GOV-012 OBSERVABILITY-LOGGING-STANDARDS.md (audit logging)
5. GOV-014 SECRETS-MANAGEMENT-POLICY.md (secrets handling)
6. GOV-009 DEPENDENCY-MANAGEMENT-POLICY.md (supply chain)

## Quick-Reference: Common Questions

| Question | Document | Section |
|----------|----------|---------|
| How do I name my Git branch? | GOV-002 | Branch Naming Convention |
| What Python formatter do we use? | GOV-003 | Tooling and Automation |
| How do I add a new dependency? | GOV-009 | Dependency Approval Process |
| Where do I put secrets? | GOV-014 | Storage Hierarchy |
| What log format do we use? | GOV-012 | OCSF Event Schema |
| How do I deploy to staging? | GOV-008 | Pipeline Stages |
| What Azure endpoints do I use? | GOV-018 | Endpoint Reference Tables |
| How do I propose a new service? | GOV-016 | RFC Template |
| What tests do I need to write? | GOV-007 | Test Type Requirements |
| How do I handle a security incident in code? | GOV-022 | Incident Classification |

## Package Metadata

- **Generated**: 2026-04-02
- **Target Compliance Frameworks**: FedRAMP Moderate, CMMC Level 2, NIST 800-171, NIST 800-53
- **Primary Languages**: Python, Rust
- **Cloud Platform**: Microsoft Azure (Commercial, GCC-High, DoD)
- **Tooling Philosophy**: FOSS and Community Edition only
- **Secrets Infrastructure**: HashiCorp Vault (local) + Azure Key Vault (cloud)
- **Logging Schema**: OCSF (Open Cybersecurity Schema Framework)
