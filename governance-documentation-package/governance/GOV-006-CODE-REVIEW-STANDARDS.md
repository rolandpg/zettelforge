---
document_id: GOV-006
title: Code Review Standards
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [code-review, pull-request, approval, checklist, peer-review, quality-gate]
compliance_mapping: [FedRAMP-CM-3, FedRAMP-SA-11, FedRAMP-SI-7, NIST-800-171-3.4.3]
---

# Code Review Standards

## Purpose

This document defines the mandatory code review process, reviewer responsibilities, approval requirements, and review checklist. Code review is the primary human quality gate in the SDLC. It catches defects that automated tools miss, spreads knowledge across the team, and maintains architectural consistency. Every line of code that reaches the main branch has been read and approved by at least one person other than the author.

## Scope

All code changes to protected branches require review. This includes application code, test code, infrastructure-as-code, CI/CD pipeline definitions, database migrations, configuration changes, and documentation. The only exception is automated dependency update PRs that pass all CI checks and modify only lock files (these may be auto-merged per GOV-009).

## Approval Requirements

Standard changes (non-security, non-infrastructure, non-data-model) require one approving review from a developer with merge permissions on the repository. The reviewer must not be the PR author.

Security-relevant changes (authentication, authorization, cryptography, input validation, secrets handling, CORS/CSP configuration) require two approving reviews: one from a developer with merge permissions and one from the designated security reviewer or CTO/CIO.

Infrastructure changes (Terraform/OpenTofu, Bicep, CI/CD pipelines, container definitions, environment configuration) require two approving reviews: one from a developer with merge permissions and one from a designated DevOps reviewer or CTO/CIO.

Database schema changes (migrations, index changes, constraint modifications) require two approving reviews: one from a developer with merge permissions and one from a senior developer familiar with the data model.

## Review Turnaround

Reviewers should provide initial feedback within one business day of being assigned. For blocking PRs (hotfixes, dependency on other work), the author may request expedited review through direct communication. If a reviewer cannot respond within one business day, they must reassign or communicate the delay.

## Reviewer Responsibilities

Reviewers evaluate code against these dimensions in priority order:

**Correctness** is the primary concern. Does the code do what the requirements specify? Does it handle edge cases? Are there off-by-one errors, race conditions, null pointer risks, or logic errors? Does the implementation match the design document (if one exists)?

**Security** is the second priority. Does the code introduce vulnerabilities? Are inputs validated? Are outputs encoded? Are secrets handled per GOV-014? Does the code follow the secure coding guidelines in GOV-011? For Python: are SQL queries parameterized, are deserialization inputs trusted? For Rust: is unsafe code justified and sound?

**Architecture and design** come third. Does the code follow the established patterns in the codebase? Does it introduce unnecessary coupling? Would a different approach be simpler or more maintainable? Are new dependencies justified per GOV-009?

**Readability and maintainability** matter for long-term health. Are names clear? Are functions focused on a single responsibility? Are comments explaining "why" rather than "what"? Would a future developer (or LLM agent) understand this code without the PR description?

**Testing** must be adequate. Are there tests for the new behavior? Do the tests actually assert meaningful outcomes (not just "code runs without throwing")? Are edge cases covered? Are the test names descriptive enough to serve as documentation?

**Performance** is evaluated when relevant. Is the algorithmic complexity appropriate? Are there unnecessary allocations, redundant queries, or N+1 patterns? For hot paths, are benchmarks included?

## Review Checklist

Reviewers verify these items before approving. Not all items apply to every PR:

The PR title follows the Conventional Commits format. The PR description explains what and why. The change is scoped to a single logical unit (not a grab bag of unrelated modifications). No secrets, credentials, PII, or internal URLs are present in the code or test fixtures. Type annotations are complete (Python) or types are sound (Rust). Error handling follows the patterns in GOV-003 or GOV-004. Logging follows the OCSF schema per GOV-012 and does not log sensitive data. New dependencies are justified and license-compatible per GOV-009. Database migrations are reversible. API changes are backward-compatible or versioned per GOV-005. Tests exist and are meaningful. All CI checks pass.

## Author Responsibilities

Before requesting review, the author must: self-review the entire diff (reading your own code as if someone else wrote it catches a surprising number of issues), ensure all CI checks pass, write a clear PR description with context, link the associated ticket, and keep the PR under 400 lines of changed code where possible.

When responding to review feedback, the author addresses every comment: either making the requested change, providing a technical justification for an alternative approach, or explicitly deferring with a new ticket for follow-up. "Will fix later" without a ticket is not acceptable.

## Disagreement Resolution

Technical disagreements between author and reviewer that cannot be resolved in PR comments within two rounds of discussion are escalated to the tech lead. If the tech lead is one of the parties, escalation goes to the CTO/CIO. The decision is documented as a comment on the PR and, if it establishes a new precedent, captured as an ADR (GOV-020).

## Compliance Notes

Code review records (PR history, review comments, approvals) serve as audit evidence for FedRAMP CM-3 (Configuration Change Control) and SA-11 (Developer Security Testing). These records are retained in the version control platform and must not be deleted or modified after merge.
