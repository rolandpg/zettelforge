---
document_id: GOV-001
title: Software Development Lifecycle Policy
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [sdlc, process, lifecycle, phases, gates, roles, responsibilities, governance]
compliance_mapping: [FedRAMP-SA-3, FedRAMP-SA-8, FedRAMP-CM-3, NIST-800-171-3.4.3, NIST-800-171-3.4.4]
---

# Software Development Lifecycle Policy

## Purpose

This document defines the mandatory phases, quality gates, roles, and artifacts that govern how software moves from concept to production. Every feature, bug fix, infrastructure change, and configuration modification must follow this lifecycle. The SDLC exists to ensure that software is built securely, reviewed consistently, tested adequately, deployed safely, and maintained responsibly. Deviations from this process require written approval from the CTO/CIO with documented justification.

## Scope

This policy applies to all software developed, maintained, or operated by the organization. This includes application code in Python and Rust, infrastructure-as-code, CI/CD pipeline definitions, configuration files, database migrations, API definitions, and documentation that ships as part of the product. Third-party integrations and vendor-managed components are governed by the Dependency Management Policy (GOV-009) and the Security Development Lifecycle (GOV-011).

## SDLC Phases

### Phase 1: Planning and Requirements

Every development effort begins with a clear definition of what is being built and why. For features above the trivial threshold (more than 2 days of estimated effort or any change touching authentication, authorization, data models, or external APIs), a design document is required per the RFC/Design Document Template (GOV-016).

**Required artifacts:**

The planning phase produces a requirements specification (can be a user story, issue description, or formal requirements document depending on scope), acceptance criteria that define "done" in testable terms, and a preliminary threat assessment for any feature that handles user input, authentication, external data, or sensitive information. For changes estimated at 2 days or less, a well-written issue ticket with acceptance criteria is sufficient.

**Gate criteria to exit Planning:**

Requirements and acceptance criteria are documented and reviewed by at least one peer. For significant changes, the RFC/design document is approved. Security-relevant changes have a threat assessment on file. The work is estimated and prioritized in the backlog.

### Phase 2: Design and Architecture

Design translates requirements into technical decisions. This phase determines what components are affected, what data models change, what APIs are added or modified, and how the change integrates with the existing architecture.

**Required artifacts:**

For significant changes, the design document (GOV-016) must include component-level design, data model changes, API contract changes (per GOV-005), and a deployment strategy. For routine changes, inline code comments and commit messages documenting design rationale are sufficient. Any new architecture decision must be captured in an Architecture Decision Record (GOV-020).

**Gate criteria to exit Design:**

Design document is approved by the designated reviewer(s). API contracts are defined in OpenAPI format if applicable. Database migration strategy is documented. No unresolved security concerns from the threat assessment.

### Phase 3: Implementation

Implementation is where code is written. All code must comply with the relevant Coding Standards (GOV-003 for Python, GOV-004 for Rust), the Version Control Policy (GOV-002), and the Secrets Management Policy (GOV-014).

**Required practices during implementation:**

Developers work on feature branches following the branching strategy in GOV-002. Commits follow the Conventional Commits format. Code is self-documenting with comments explaining "why" not "what." Tests are written alongside implementation, not after. Secrets are never committed to version control. All logging follows the OCSF schema defined in GOV-012.

**Gate criteria to exit Implementation:**

All code compiles/passes lint checks. Unit tests are written and passing. The developer has self-reviewed their own diff before requesting peer review. No secrets, credentials, or PII exist in the code or configuration.

### Phase 4: Code Review

Code review is a mandatory quality gate. No code merges to the main branch without review. The Code Review Standards (GOV-006) define the full process.

**Gate criteria to exit Code Review:**

Minimum required approvals are obtained per GOV-006. All automated checks (linting, type checking, unit tests, SAST) pass. Review comments are addressed or explicitly deferred with documented justification. The reviewer has verified that tests cover the new or changed behavior.

### Phase 5: Testing and Validation

Beyond unit tests written during implementation, this phase covers integration testing, end-to-end testing for critical paths, and security testing as defined in GOV-007 and GOV-011.

**Gate criteria to exit Testing:**

All tests pass in the CI pipeline. Code coverage meets the minimum thresholds defined in GOV-007. For security-relevant changes, SAST findings are triaged and resolved or accepted with documented risk acceptance. Performance tests pass for changes affecting critical paths.

### Phase 6: Deployment

Deployment follows the CI/CD Pipeline Standards (GOV-008) and the Release Management Policy (GOV-010). Production deployments are automated through the pipeline and never performed manually except during documented emergency procedures.

**Gate criteria to exit Deployment:**

The artifact is built from a reviewed and tested commit on the main branch. Staging environment validation is complete. Deployment runbook is available for complex changes. Rollback procedure is documented and tested. Change is logged in the release changelog.

### Phase 7: Operations and Monitoring

Post-deployment, the system is monitored per the Observability and Logging Standards (GOV-012). The team that builds it is responsible for operating it until ownership is formally transferred.

**Ongoing responsibilities:**

Monitor error rates, latency, and resource utilization against defined SLOs. Respond to alerts within the SLA defined in GOV-022. Maintain documentation as the system evolves. Manage technical debt per GOV-015.

### Phase 8: Decommission

When a component, service, or feature is retired, it must be decommissioned deliberately rather than abandoned. This includes removing dead code, cleaning up infrastructure resources, updating documentation, notifying dependent teams or consumers, and archiving relevant artifacts.

## Roles and Responsibilities

**Developer**: Implements code, writes tests, creates documentation, participates in code review, responds to incidents for owned services.

**Tech Lead / Senior Developer**: Reviews design documents, approves code reviews for complex changes, makes architecture decisions (documented as ADRs), mentors junior developers, owns technical debt prioritization for their domain.

**CTO/CIO**: Approves significant architecture decisions, owns the governance documentation, resolves escalated technical disputes, approves SDLC deviations, maintains the technology roadmap.

**Security Lead**: Reviews threat assessments, triages SAST/DAST findings, approves security-relevant design decisions, maintains the Security Development Lifecycle (GOV-011).

## Emergency Change Process

Emergency changes (production outages, critical security vulnerabilities) may bypass the standard review timeline but must still meet minimum quality standards. The emergency process requires: verbal approval from the CTO/CIO or designated delegate, a paired review (synchronous review with another engineer), automated tests for the fix, and a post-incident retrospective within 5 business days that includes a full review of the emergency change. Emergency changes must be documented with the tag `[EMERGENCY]` in the commit message and tracked in the incident log.

## Compliance Notes

This SDLC aligns with FedRAMP Moderate controls SA-3 (System Development Life Cycle), SA-8 (Security Engineering Principles), and CM-3 (Configuration Change Control). Evidence of SDLC compliance is maintained through version control history, CI/CD pipeline logs, code review records, and the artifacts produced at each phase gate.
