---
document_id: GOV-013
title: Environment Management Policy
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [environment, staging, production, development, infrastructure, access-control, data-handling, parity, containers]
compliance_mapping: [FedRAMP-CM-2, FedRAMP-CM-6, FedRAMP-AC-6, FedRAMP-SC-4, NIST-800-171-3.1.5, NIST-800-171-3.4.1, NIST-800-171-3.4.2]
---

# Environment Management Policy

## Purpose

This document defines the environment topology, access controls, data handling rules, and parity requirements for all deployment environments. Environments exist to provide isolation between development experimentation, integration validation, and production operations. Mismanaged environments lead to "works on my machine" failures, data leakage between tiers, and unreliable testing.

## Environment Topology

The organization maintains three primary environments. Each environment is fully isolated with its own infrastructure, secrets, and access controls.

### Development (Local)

The developer's local workstation. Services run locally or in local containers (Podman or Docker). Uses local HashiCorp Vault (dev mode) for secrets. Connects to local databases (containerized PostgreSQL). No access to staging or production data. The development environment is the developer's responsibility to maintain per the onboarding guide (GOV-017). For the homelab, the ASUS Ascent DGX Spark GB10 and the RTX 5090 gaming/compute PC serve as shared development infrastructure on the 192.168.1.0/24 network.

### Staging

Mirrors production configuration as closely as possible. Deployed automatically on merge to `main` (GOV-008). Uses its own secrets (GOV-014), its own database instance with synthetic test data, and its own Azure resource group. Staging is where integration tests, smoke tests, and DAST scans run. Staging data must never contain production PII or real customer data. If realistic data is needed, use a data synthesis tool or anonymize production data through a documented, auditable process.

### Production

The live environment serving real users or systems. Deployed only after staging validation (GOV-008, GOV-010). Access is strictly limited. No developer has direct shell access to production compute. Database access for debugging requires a documented justification, a time-limited credential from Vault (dynamic secrets with 1-hour TTL), and an audit trail logged per GOV-012. Production changes are made exclusively through the CI/CD pipeline, never manually.

## Access Controls by Environment

Development: all developers have full access to their local environment. Staging: all developers have read access to logs and metrics; write access (deployment) is restricted to the CI/CD pipeline; database query access requires justification logged to the team lead. Production: read access to logs and metrics is granted to on-call engineers and senior developers; database access requires CTO/CIO or security lead approval with a time-limited credential and full audit logging; deployment is automated through the pipeline only.

Access reviews for staging and production are conducted quarterly and documented.

## Environment Parity

Staging must match production in these dimensions: same container images (built once, deployed to both), same configuration structure (different values, same keys), same database engine version, same network topology (if applicable), and same monitoring and alerting rules. Divergence between staging and production is a leading indicator of deployment failures and is tracked as technical debt (GOV-015).

## Infrastructure as Code

All environment infrastructure is defined in code using OpenTofu (FOSS) for Azure resources and Podman Compose or Kubernetes manifests for container orchestration. Environment-specific values are parameterized, not hardcoded. The infrastructure code is version-controlled, reviewed, and deployed through the same CI/CD pipeline as application code.

## Compliance Notes

This policy supports FedRAMP CM-2 (Baseline Configuration) through defined environment configurations, CM-6 (Configuration Settings) through standardized settings across environments, AC-6 (Least Privilege) through tiered access controls, and SC-4 (Information in Shared Resources) through environment isolation.
