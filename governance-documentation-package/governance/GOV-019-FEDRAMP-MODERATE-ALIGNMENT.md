---
document_id: GOV-019
title: FedRAMP Moderate Control Alignment
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [fedramp, moderate, compliance, nist-800-53, controls, mapping, audit, evidence, cmmc, nist-800-171]
compliance_mapping: [FedRAMP-ALL, NIST-800-53-Moderate, NIST-800-171, CMMC-L2]
---

# FedRAMP Moderate Control Alignment

## Purpose

This document maps the organization's governance documentation to FedRAMP Moderate security controls (based on NIST 800-53 Rev 5) and identifies the audit evidence produced by each governance document. FedRAMP Moderate is the target compliance baseline because it covers the security requirements for systems processing moderate-impact federal data, which aligns with the organization's current and anticipated customer base in the Defense Industrial Base. CMMC Level 2 requirements substantially overlap with NIST 800-171, which is itself a subset of NIST 800-53 Moderate controls, so this alignment serves both compliance frameworks.

## Control Family Mapping

### Access Control (AC)

AC-2 (Account Management): GOV-017 defines account provisioning and deprovisioning. GOV-013 defines environment-specific access tiers. Evidence: access provisioning logs, quarterly access reviews, offboarding checklists.

AC-3 (Access Enforcement): GOV-005 defines API authentication/authorization requirements. GOV-014 defines secrets access controls. GOV-013 defines environment access tiers. Evidence: API authentication logs (OCSF class 3001, 3003 per GOV-012), Vault audit logs.

AC-6 (Least Privilege): GOV-002 defines repository access controls (CODEOWNERS, branch protection). GOV-013 enforces tiered environment access. GOV-014 enforces per-service secrets scoping. Evidence: repository permission settings, Vault policies, Azure RBAC assignments.

### Audit and Accountability (AU)

AU-2 (Audit Events): GOV-012 defines mandatory OCSF event classes for all auditable events. Evidence: application log configuration showing OCSF event generation.

AU-3 (Content of Audit Records): GOV-012 specifies required OCSF fields for each event class. Evidence: sample log entries demonstrating OCSF field completeness.

AU-6 (Audit Review, Analysis, and Reporting): GOV-012 defines OpenSearch/Grafana analysis capabilities. Evidence: configured dashboards, alert rules, periodic review logs.

AU-8 (Time Stamps): GOV-012 mandates UTC timestamps on all events. Evidence: log samples showing ISO 8601 UTC timestamps.

AU-12 (Audit Generation): GOV-012 mandates structured logging in all services. GOV-003 and GOV-004 enforce logging standards in code. Evidence: CI pipeline logs showing lint enforcement of logging standards.

### Configuration Management (CM)

CM-2 (Baseline Configuration): GOV-013 defines environment baselines. GOV-008 defines CI/CD pipeline baselines. Evidence: infrastructure-as-code repos, container image definitions.

CM-3 (Configuration Change Control): GOV-001 defines the SDLC with phase gates. GOV-002 mandates PR review for all changes. GOV-006 defines code review requirements. GOV-016 defines the RFC process for significant changes. Evidence: git history, PR review records, merged RFC documents.

CM-5 (Access Restrictions for Change): GOV-002 defines branch protection and CODEOWNERS. Evidence: repository branch protection settings, CODEOWNERS files.

CM-6 (Configuration Settings): GOV-013 defines environment configuration standards. GOV-018 defines Azure cloud endpoint configuration. Evidence: infrastructure-as-code, environment configuration files.

### Identification and Authentication (IA)

IA-5 (Authenticator Management): GOV-014 defines secret rotation schedules and access controls. Evidence: Vault audit logs showing rotation events, Key Vault diagnostic logs.

IA-8 (Identification and Authentication for Non-Organizational Users): GOV-005 mandates API authentication. Evidence: API authentication configuration, OCSF class 3001 logs.

### System and Services Acquisition (SA)

SA-3 (System Development Life Cycle): GOV-001 defines the complete SDLC. Evidence: documented phase gates, PR history, design documents.

SA-8 (Security Engineering Principles): GOV-011 defines the Security Development Lifecycle. GOV-003 and GOV-004 embed secure coding standards. Evidence: threat models, SAST configuration, secure coding checklist adherence.

SA-10 (Developer Configuration Management): GOV-002 defines version control standards. GOV-010 defines release management. Evidence: git history, release tags, changelogs.

SA-11 (Developer Security Testing): GOV-011 defines SAST, SCA, and DAST requirements. GOV-007 defines testing standards. GOV-008 integrates security scanning into CI. Evidence: CI pipeline logs showing SAST/SCA scan results, DAST reports.

SA-12 (Supply Chain Risk Management): GOV-009 defines dependency management including approval, monitoring, and vulnerability response. Evidence: dependency approval records in PR descriptions, SBOMs, vulnerability scan reports.

### System and Communications Protection (SC)

SC-7 (Boundary Protection): GOV-018 defines cloud endpoint boundaries per environment. GOV-013 defines environment isolation. Evidence: network configuration, Azure NSG rules, firewall configurations.

SC-8 (Transmission Confidentiality and Integrity): GOV-005 mandates HTTPS for all APIs. GOV-011 specifies TLS 1.2 minimum. Evidence: TLS configuration, API endpoint configurations.

SC-12 (Cryptographic Key Establishment and Management): GOV-014 defines key management and rotation. Evidence: Vault key configuration, Key Vault access policies, rotation logs.

SC-28 (Protection of Information at Rest): GOV-014 defines encrypted secret storage. GOV-021 defines data classification and encryption requirements. Evidence: Vault seal configuration, Key Vault encryption settings, database encryption configuration.

### System and Information Integrity (SI)

SI-2 (Flaw Remediation): GOV-009 defines vulnerability response timelines. GOV-015 defines technical debt management including security debt. Evidence: vulnerability tracking tickets, remediation timelines, patching records.

SI-4 (Information System Monitoring): GOV-012 defines monitoring, metrics, alerting, and log analysis. Evidence: Prometheus configuration, Grafana dashboards, alert routing rules.

SI-7 (Software, Firmware, and Information Integrity): GOV-002 mandates signed commits. GOV-008 builds artifacts from reviewed code only. Evidence: signed commit verification, CI build provenance.

SI-10 (Information Input Validation): GOV-003, GOV-004, and GOV-011 mandate input validation. Evidence: code review records showing validation review, SAST rules for injection vulnerabilities.

## Evidence Collection

For each control, evidence is automatically produced as a byproduct of following the governance processes. The primary evidence sources are: version control history (git log, PR records, review comments), CI/CD pipeline execution logs, application audit logs (OCSF format), infrastructure-as-code repositories, secrets management audit logs (Vault, Key Vault), monitoring and alerting configuration, and governance documents themselves (version-controlled, change-tracked).

No separate compliance documentation effort is required if the governance processes are followed consistently. The governance framework is designed so that compliance evidence is a natural output of doing the work correctly.

## Gap Analysis

Areas where the governance documentation does not yet fully address FedRAMP Moderate requirements and will need additional work as the organization matures:

Physical and Environmental Protection (PE family): not applicable for cloud-hosted workloads (inherited from Azure), but relevant for the local homelab infrastructure housing Vault and development systems. A physical security assessment of the homelab environment may be needed.

Contingency Planning (CP family): disaster recovery and business continuity plans are not yet documented. This should be addressed as the organization moves toward production workloads.

Personnel Security (PS family): background check requirements for personnel with access to sensitive systems are defined at a basic level in GOV-017 but may need expansion for FedRAMP authorization.

Risk Assessment (RA family): a formal risk assessment process is not yet documented. Risk is currently managed through threat modeling (GOV-011) and technical debt tracking (GOV-015), but a formal risk assessment framework (e.g., NIST 800-30) should be adopted.
