---
document_id: GOV-009
title: Dependency Management Policy
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [dependencies, supply-chain, license-compliance, vulnerability, sbom, cve, pip-audit, cargo-audit, renovate]
compliance_mapping: [FedRAMP-SA-12, FedRAMP-SI-2, FedRAMP-SR-3, NIST-800-171-3.14.1]
---

# Dependency Management Policy

## Purpose

This document governs how external dependencies are evaluated, approved, updated, and monitored. Every third-party library, framework, and tool introduced into the codebase expands the attack surface and creates a maintenance obligation. This policy ensures that dependencies are intentionally selected, license-compatible, actively maintained, and continuously monitored for vulnerabilities.

## Scope

This policy covers all external dependencies: Python packages (PyPI), Rust crates (crates.io), system-level packages in container images, JavaScript packages for build tooling, and any other third-party code that is compiled, linked, or executed as part of the organization's software.

## Dependency Approval Process

Before introducing a new dependency, the developer must evaluate it against these criteria and document the evaluation in the PR description:

**Necessity**: Can the functionality be implemented in a reasonable amount of code without the dependency? If the dependency saves fewer than 100 lines and the functionality is not security-critical (where a proven library is preferred over custom implementation), consider implementing it in-house.

**Maintenance status**: The dependency must have at least one commit within the last 12 months. Dependencies with no activity for over 12 months are considered unmaintained and require CTO/CIO approval with a documented risk acceptance and migration plan.

**License compatibility**: The dependency license must be compatible with the organization's distribution model. Permissive licenses (MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Zlib) are approved by default. Weak copyleft licenses (LGPL, MPL-2.0) require review to confirm the dependency is used as a library (not modified and distributed). Strong copyleft licenses (GPL, AGPL) are prohibited unless the project itself is distributed under a compatible copyleft license. Unknown or proprietary licenses require CTO/CIO approval.

**Security posture**: The dependency must not have unpatched CRITICAL or HIGH CVEs at the time of adoption. Check using `pip-audit` (Python) or `cargo-audit` (Rust). Dependencies that handle cryptography, authentication, serialization, or network I/O receive additional scrutiny and require security reviewer approval.

**Transitive dependency impact**: Evaluate the transitive dependency tree the new dependency introduces. A dependency that pulls in 50 transitive dependencies for a simple utility function is disproportionate. Use `pipdeptree` (Python) or `cargo tree` (Rust) to assess the impact.

## Dependency Pinning

All production dependencies are pinned to exact versions in lock files. Python projects use `pip-compile` (from `pip-tools`) to generate a `requirements.lock` or use Poetry/PDM with lock files. Rust projects commit `Cargo.lock` for binary crates. Version ranges in the primary manifest (`pyproject.toml`, `Cargo.toml`) use compatible release specifiers: `~=3.2` (Python) or `^3.2` (Rust) to accept patch updates within the specified minor version.

## Automated Dependency Updates

Renovate Bot (FOSS, self-hosted) runs weekly to detect available dependency updates. Renovate creates PRs for each update, categorized by type:

Patch updates (e.g., 3.2.1 to 3.2.2) are auto-merged if all CI checks pass. These are bug fixes and security patches with minimal breaking risk.

Minor updates (e.g., 3.2.x to 3.3.0) create PRs for human review. The reviewer verifies the changelog for unexpected behavior changes and ensures tests pass.

Major updates (e.g., 3.x to 4.0) create PRs flagged as requiring migration review. The developer assigned to the PR must read the migration guide, test the upgrade locally, and document any code changes required. Major updates are scheduled rather than applied reactively.

## Vulnerability Response

Vulnerability scanning runs in CI on every build (GOV-008, Stage 4) and on a daily scheduled scan of all active repositories.

CRITICAL severity CVEs in dependencies must be patched or mitigated within 48 hours of notification. If a patch is not available, the vulnerable dependency must be isolated, its attack surface must be documented, and compensating controls must be implemented.

HIGH severity CVEs must be addressed within 7 calendar days.

MEDIUM severity CVEs must be addressed within 30 calendar days.

LOW severity CVEs are tracked and addressed during regular dependency update cycles.

Vulnerability triage is documented. If a CVE is not exploitable in the organization's usage context (e.g., the vulnerable code path is never called), this is documented as a risk acceptance with the specific justification and the CTO/CIO's approval.

## Software Bill of Materials

An SBOM is generated for every release artifact. The SBOM includes all direct and transitive dependencies with name, version, license, and supplier information. The format follows CycloneDX (JSON) for machine-readable output and a Markdown summary for human review. SBOMs are stored alongside release artifacts and retained for the lifetime of the release. See the Software Documentation Agent output (SBOM document) for the generation process.

## Prohibited Dependencies

The following categories of dependencies are prohibited without explicit CTO/CIO approval: dependencies that require outbound network calls during import/initialization (telemetry, analytics), dependencies that execute arbitrary code during installation (setup.py with network calls), dependencies from private registries not controlled by the organization, and dependencies that bundle compiled binaries without source availability.

## Compliance Notes

This policy supports FedRAMP SA-12 (Supply Chain Risk Management), SI-2 (Flaw Remediation) through vulnerability response timelines, and SR-3 (Supply Chain Controls and Processes) through the approval and monitoring requirements.
