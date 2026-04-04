---
document_id: GOV-011
title: Security Development Lifecycle
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [security, sdl, threat-modeling, stride, sast, dast, secure-coding, vulnerability, penetration-testing]
compliance_mapping: [FedRAMP-SA-3, FedRAMP-SA-8, FedRAMP-SA-11, FedRAMP-SA-15, FedRAMP-SI-10, NIST-800-171-3.13.2, NIST-800-171-3.14.1, NIST-800-171-3.14.2, NIST-800-171-3.14.3]
---

# Security Development Lifecycle

## Purpose

This document defines how security is integrated into every phase of the software development lifecycle. Security is not a phase or a gate that happens after development. It is a continuous discipline woven into design, implementation, testing, deployment, and operations. This SDL ensures that security defects are prevented or caught as early as possible, where they are cheapest to fix and least likely to cause harm.

## Scope

This SDL applies to all software developed, maintained, or operated by the organization. It covers application code, infrastructure-as-code, CI/CD pipelines, container definitions, API designs, and third-party integrations. It operates in conjunction with the SDLC (GOV-001) and supplements the language-specific coding standards (GOV-003, GOV-004).

## Security Activities by SDLC Phase

### Planning Phase: Threat Assessment

Every feature or change that meets any of the following criteria requires a threat assessment before implementation begins: it handles user input, it modifies authentication or authorization logic, it introduces a new external integration, it changes data models for sensitive data, it modifies cryptographic operations, or it changes network boundaries or exposure.

The threat assessment uses the STRIDE framework: Spoofing (can an attacker impersonate a legitimate entity?), Tampering (can an attacker modify data in transit or at rest?), Repudiation (can an attacker deny performing an action without detection?), Information Disclosure (can an attacker access data they should not see?), Denial of Service (can an attacker make the system unavailable?), and Elevation of Privilege (can an attacker gain higher permissions than intended?).

The threat assessment is documented in the design document (GOV-016) or in a dedicated `THREAT_MODEL.md` for significant features. It identifies threats, rates their likelihood and impact, and specifies mitigations that must be implemented. Mitigations are tracked as requirements with acceptance criteria.

### Design Phase: Secure Architecture

Design reviews evaluate: authentication and authorization model correctness (no implicit trust between components), data flow analysis for sensitive data (PII, credentials, CUI per GOV-021), encryption requirements for data at rest and in transit, input validation strategy at trust boundaries, error handling that does not leak internal state, and logging strategy that captures security events without logging sensitive data (GOV-012).

Cryptographic choices must use well-established algorithms and libraries. Custom cryptographic implementations are absolutely prohibited. For Python, use `cryptography` library. For Rust, use `ring` or `rustls`. AES-256-GCM for symmetric encryption. RSA-2048 or Ed25519 for asymmetric operations. SHA-256 minimum for hashing. Argon2id for password hashing. TLS 1.2 minimum, TLS 1.3 preferred.

### Implementation Phase: Secure Coding

Developers follow the secure coding guidelines embedded in the language-specific coding standards (GOV-003, GOV-004). Key requirements summarized here:

Input validation occurs at every trust boundary. All external input (user input, API requests, file uploads, environment variables, database reads from shared databases) is validated for type, length, format, and range before processing. Use allowlists over denylists. Use schema validation (Pydantic for Python, serde with validation for Rust) rather than manual parsing.

Output encoding prevents injection attacks. HTML output is escaped. SQL uses parameterized queries exclusively. Shell commands use subprocess with argument arrays, never string interpolation. Serialization uses safe formats (JSON) with explicit schema validation on deserialization.

Secrets management follows GOV-014 strictly. No secrets in code, configuration files, or environment variable defaults. No secrets in log output. No secrets in error messages. No secrets in URLs or query parameters.

Session management uses secure defaults: HttpOnly and Secure flags on cookies, SameSite=Lax or Strict, short session lifetimes (configurable, default 1 hour), and server-side session invalidation on logout.

### Testing Phase: Security Testing

Security testing operates at three levels:

**Static Application Security Testing (SAST)** runs in CI on every build (GOV-008). Bandit rules (via Ruff) for Python. Clippy security lints for Rust. Semgrep community rules for cross-language patterns. SAST findings are triaged: CRITICAL and HIGH findings block merging. MEDIUM findings are triaged within 5 business days. FALSE positives are suppressed with inline comments documenting the justification.

**Software Composition Analysis (SCA)** scans all dependencies for known vulnerabilities. `pip-audit` for Python, `cargo-audit` for Rust, and Trivy (FOSS) for container images. Runs in CI and on a daily schedule. Vulnerability response follows GOV-009 timelines.

**Dynamic Application Security Testing (DAST)** runs against the staging environment after deployment. Uses OWASP ZAP (FOSS) in automated scan mode targeting the API surface. DAST scans run weekly on staging and before any production release. Findings are triaged with the same severity-based timelines as SAST.

Manual penetration testing is conducted annually for production systems and after significant architectural changes. Penetration testing scope, rules of engagement, and findings are documented and tracked through remediation.

### Deployment Phase: Secure Deployment

Container images use minimal base images (distroless preferred, alpine acceptable). No build tools, compilers, or debugging utilities in production images. Container images are scanned by Trivy before deployment. Images run as non-root users. Dockerfile best practices: pin base image digests (not just tags), copy only necessary files, use multi-stage builds.

Infrastructure deployment follows the principle of least privilege. Service accounts have only the permissions required for their function. Network policies restrict traffic to explicitly allowed paths. See GOV-013 for environment-specific security controls.

### Operations Phase: Security Monitoring

Production systems generate security-relevant logs per the OCSF schema (GOV-012). Security events are monitored and alerted on. Authentication failures beyond threshold trigger alerts. Authorization failures are logged and reviewed. Configuration changes are audited. See GOV-022 for incident response procedures specific to development-originated security events.

## Security Training

All developers complete security awareness training annually, covering: OWASP Top 10 for the current year, secure coding practices for their primary language, the organization's SDL requirements, and incident response procedures. Training completion is tracked and reported. New hires complete security training within their first 30 days.

## Compliance Notes

This SDL aligns with FedRAMP SA-3 (System Development Life Cycle), SA-8 (Security Engineering Principles), SA-11 (Developer Security Testing and Evaluation), SA-15 (Development Process, Standards, and Tools), and SI-10 (Information Input Validation). The combination of threat modeling, SAST, SCA, DAST, and penetration testing provides the multi-layered assurance that FedRAMP Moderate requires. Evidence is maintained through CI/CD logs, scan reports, and threat model documentation.
