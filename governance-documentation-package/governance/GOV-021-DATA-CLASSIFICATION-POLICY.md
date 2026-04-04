---
document_id: GOV-021
title: Data Classification Policy
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [data-classification, cui, pii, sensitive, public, confidential, handling, encryption, labeling, retention]
compliance_mapping: [FedRAMP-RA-2, FedRAMP-SC-28, FedRAMP-MP-4, NIST-800-171-3.1.22, NIST-800-171-3.8.1, NIST-800-171-3.8.3, NIST-800-171-3.8.4]
---

# Data Classification Policy

## Purpose

This document defines the data classification tiers, labeling requirements, handling rules, storage requirements, and transmission requirements for all data processed by the organization's systems. Data classification ensures that protection measures are proportional to the sensitivity of the data. Not all data needs the same level of protection, and treating everything as equally sensitive wastes resources while treating everything as non-sensitive creates unacceptable risk.

## Classification Tiers

### Tier 1: Public

Data that is explicitly approved for public release. Examples: published documentation, open-source code, marketing materials, publicly available API documentation. Handling: no special controls required. May be stored in any approved system. May be transmitted over any channel.

### Tier 2: Internal

Data intended for internal use that would cause minor inconvenience or competitive disadvantage if disclosed. Examples: internal process documentation, team meeting notes, non-sensitive project plans, internal communications, system architecture documents that do not reveal security controls. Handling: access limited to authenticated team members. Stored in systems with basic access controls. Transmitted over encrypted channels (TLS). No special labeling required beyond repository access controls.

### Tier 3: Confidential

Data whose disclosure would cause significant harm to the organization, its clients, or individuals. Examples: personally identifiable information (PII), financial records, authentication credentials, client contract details, security vulnerability details before remediation, proprietary algorithms, and trade secrets. Handling: access granted on a need-to-know basis. Encrypted at rest and in transit. Stored only in approved systems (encrypted databases, Vault, Key Vault). Logged access per GOV-012 OCSF class 1001 and 3003. Never stored in version control, logs, or error messages.

### Tier 4: Controlled Unclassified Information (CUI)

Data subject to federal government safeguarding requirements per 32 CFR Part 2002. Examples: data covered by DFARS 252.204-7012, ITAR/EAR controlled technical data, law enforcement sensitive information, and data marked with CUI categories. Handling: all Tier 3 controls plus compliance with NIST 800-171 controls. Stored only in environments authorized for CUI (FedRAMP Moderate or higher, or systems assessed against NIST 800-171). Transmitted only over FIPS 140-2 validated encrypted channels. Access limited to US persons where required by regulatory framework. Labeled with the appropriate CUI marking.

## Data Handling Rules by Tier

### Storage

Tier 1 and 2 data may be stored in any system approved for general use. Tier 3 data must be stored in encrypted databases (AES-256 at rest), encrypted file systems, or approved secrets management systems (Vault, Key Vault). Tier 4 data must be stored only in systems that meet the NIST 800-171 requirements mapped in GOV-019, within Azure environments that meet FedRAMP Moderate (GCC-High or DoD per GOV-018 for cloud workloads, or local systems assessed against NIST 800-171 for on-premises storage).

### Transmission

All data, regardless of tier, must be transmitted over encrypted channels (TLS 1.2 minimum, TLS 1.3 preferred) per GOV-005 and GOV-011. Tier 4 data requires FIPS 140-2 validated cryptographic modules for transmission. Azure GCC-High and DoD environments provide FIPS-validated TLS by default. For local systems, configure OpenSSL or equivalent with FIPS-validated modules.

### Logging and Monitoring

Tier 3 and Tier 4 data access is logged as OCSF events per GOV-012. Logs themselves must not contain Tier 3 or Tier 4 data values (log the access event, not the data content). Anomalous access patterns for Tier 3 and 4 data generate alerts per the monitoring thresholds in GOV-012.

### Retention and Disposal

Each data type must have a defined retention period based on business requirements and regulatory obligations. When data reaches the end of its retention period, it must be securely deleted. For databases, this means cryptographic erasure or secure overwrite, not just row deletion (deleted rows may persist in backups and WAL files). For object storage, this means lifecycle policies that enforce deletion. Backup retention must align with data retention requirements.

### Development and Testing

Tier 3 and Tier 4 data must never appear in development or staging environments. Test data uses synthetic generation or anonymization (irreversible transformation that removes all identifying characteristics). If realistic data shapes are needed for testing, a documented anonymization process must be approved by the CTO/CIO and security team. Anonymized data is classified as Tier 2.

## Developer Responsibilities

Developers must identify the classification tier of data their code handles during the design phase (GOV-016). Code that processes Tier 3 or Tier 4 data must include the classification in code comments and the threat model. Code review (GOV-006) verifies that data handling matches the classification requirements. SAST rules (GOV-011) flag patterns that suggest Tier 3/4 data in logs, error messages, or unencrypted storage.

## Compliance Notes

This policy satisfies FedRAMP RA-2 (Security Categorization) through the tiered classification system, SC-28 (Protection of Information at Rest) through encrypted storage requirements, and MP-4 (Media Storage) through storage and disposal requirements. The CUI handling requirements align with NIST 800-171 controls for CMMC Level 2 compliance.
