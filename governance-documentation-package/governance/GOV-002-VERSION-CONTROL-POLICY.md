---
document_id: GOV-002
title: Version Control Policy
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [git, version-control, branching, commits, merge, pull-request, trunk-based, conventional-commits]
compliance_mapping: [FedRAMP-CM-3, FedRAMP-CM-5, FedRAMP-SI-7, NIST-800-171-3.4.3, NIST-800-171-3.4.5]
---

# Version Control Policy

## Purpose

This document defines how source code, configuration, infrastructure definitions, and documentation are managed in version control. It establishes the branching strategy, commit message format, merge requirements, and access controls that ensure every change is traceable, reviewable, and auditable.

## Scope

This policy applies to every repository owned or operated by the organization. This includes application source code, infrastructure-as-code (Terraform/OpenTofu, Bicep), CI/CD pipeline definitions, configuration files, database migration scripts, API contract definitions, and governance documentation. Nothing that ships, deploys, or configures a system exists outside version control.

## Version Control Platform

The organization uses Git as the version control system. Repository hosting uses Gitea (self-hosted, FOSS) for development operations. Gitea is selected for its lightweight footprint, compatibility with Git-standard workflows, and zero licensing cost. Gitea mirrors to Azure Repos (free tier) are configured for CI/CD integration with Azure DevOps Pipelines where applicable.

All repositories must have branch protection rules enabled on the `main` branch. Direct pushes to `main` are prohibited. All changes reach `main` through pull requests.

## Branching Strategy

The organization uses trunk-based development with short-lived feature branches. This strategy prioritizes continuous integration, small incremental changes, and minimal merge conflict risk.

### Branch Types

**`main`** is the single source of truth. It is always in a deployable state. Every commit to `main` has passed code review and all automated quality gates. Production deployments are triggered from `main`.

**`feature/<ticket-id>-<short-description>`** branches are where development happens. They are created from `main`, contain a single logical change, and are deleted after merging. Feature branches should live no longer than 3 business days. If a feature requires more than 3 days, it must be broken into smaller incremental changes that can each be merged independently.

**`hotfix/<ticket-id>-<short-description>`** branches are for emergency production fixes. They follow the emergency change process defined in GOV-001. Hotfix branches are created from `main`, contain only the minimal fix, and are merged with expedited review.

**`release/<version>`** branches are created only when the project ships versioned software to external consumers (not for internally deployed services). They are created from `main` at the point of release and receive only critical bug fixes via cherry-pick. Release branches are tagged with the version number and never deleted.

### Branch Naming Convention

All branch names follow this pattern:

```
<type>/<ticket-id>-<short-kebab-case-description>
```

Examples of correctly named branches: `feature/PROJ-142-add-user-auth-endpoint`, `hotfix/PROJ-287-fix-token-expiry-check`, `release/v2.3.0`. Examples of incorrectly named branches: `patch` (no ticket ID, no description), `johns-branch` (developer names are not branch names), `feature/add_stuff` (no ticket ID, underscores instead of hyphens, vague description).

The `<ticket-id>` must reference the issue tracker ticket associated with the work. This creates an audit trail from code change to business requirement.

## Commit Message Standard

All commits use the Conventional Commits specification (conventionalcommits.org). This format enables automated changelog generation, semantic version bumping, and clear history navigation.

### Commit Message Format

```
<type>(<scope>): <short description>

<body - optional but recommended for non-trivial changes>

<footer - optional, for breaking changes and ticket references>
```

### Commit Types

`feat` is for new features or capabilities. It corresponds to a MINOR version bump in semantic versioning. Example: `feat(auth): add JWT refresh token rotation`.

`fix` is for bug fixes. It corresponds to a PATCH version bump. Example: `fix(api): correct pagination offset calculation`.

`docs` is for documentation-only changes. Example: `docs(readme): update local development setup instructions`.

`style` is for code formatting changes that do not affect behavior (whitespace, semicolons, formatting). Example: `style(models): apply ruff formatting to user models`.

`refactor` is for code restructuring that does not change external behavior. Example: `refactor(auth): extract token validation into dedicated module`.

`test` is for adding or modifying tests. Example: `test(api): add integration tests for user creation endpoint`.

`chore` is for build process, tooling, or dependency changes. Example: `chore(deps): update cryptography to 43.0.1`.

`ci` is for CI/CD pipeline changes. Example: `ci(github): add SAST scanning step to PR pipeline`.

`perf` is for performance improvements. Example: `perf(queries): add composite index for user lookup`.

`security` is for security-related changes. This is a custom type added for compliance traceability. Example: `security(auth): enforce minimum password entropy`.

### Commit Message Rules

The short description must be imperative mood ("add feature" not "added feature" or "adds feature"), lowercase, no period at the end, and no longer than 72 characters. The body wraps at 72 characters per line and explains "what" and "why", not "how" (the code shows "how"). The footer references ticket IDs with `Refs: PROJ-142` or closes them with `Closes: PROJ-142`. Breaking changes are indicated with `BREAKING CHANGE:` in the footer or `!` after the type: `feat(api)!: change authentication header format`.

## Merge Strategy

All merges to `main` use squash merge. Squash merging collapses a feature branch's commits into a single commit on `main`, producing a clean linear history where each commit represents one complete, reviewed, tested change. The squash commit message must follow the Conventional Commits format and include the PR number.

Exceptions: release branches use merge commits (not squash) to preserve the cherry-pick history. This is the only exception.

## Pull Request Requirements

Every pull request must include a descriptive title following the Conventional Commits format, a description explaining what changed and why, a reference to the associated ticket, confirmation that the developer has self-reviewed the diff, and passing status checks for all automated quality gates (linting, type checking, tests, SAST).

Pull requests should be small. The target is under 400 lines of changed code (excluding auto-generated files, lock files, and test fixtures). If a PR exceeds 400 lines, the author must justify why it cannot be split or must break it into stacked PRs with clear dependency ordering.

Draft pull requests are encouraged for work-in-progress to get early feedback. Draft PRs do not require passing checks and cannot be merged.

## Repository Access Controls

Access to repositories follows the principle of least privilege, aligned with FedRAMP AC-6.

**Read access** is granted to all engineering staff for all repositories. Transparency supports code reuse and cross-team awareness.

**Write access** (push to feature branches, create PRs) is granted to developers assigned to the project.

**Merge access** (approve and merge PRs to `main`) is granted to senior developers and tech leads designated as code owners for the relevant code paths. Code ownership is defined in a `CODEOWNERS` file at the repository root.

**Admin access** (repository settings, branch protection rules, webhook configuration) is restricted to the CTO/CIO and designated DevOps personnel.

Access reviews are conducted quarterly and documented. Departing team members have access revoked within 24 hours of separation, per the offboarding checklist in GOV-017.

## Repository Hygiene

Every repository must contain at its root: a `README.md` with project purpose, setup instructions, and links to relevant governance documents; a `LICENSE` file; a `.gitignore` appropriate to the language and tooling; a `CODEOWNERS` file defining review responsibility; and a `CHANGELOG.md` following the Keep a Changelog format (keepachangelog.com).

Repositories must not contain: secrets, credentials, or API keys (see GOV-014); compiled binaries or build artifacts (these go to artifact storage); large binary files (use Git LFS if binary assets are unavoidable); or generated code that can be reproduced from source.

## Git Configuration Requirements

All developers must configure their Git identity with their organizational email address. Commits from personal email addresses will be rejected by pre-receive hooks. GPG or SSH commit signing is required for all commits to provide non-repudiation. Unsigned commits are rejected by branch protection rules.

```bash
# Required Git configuration
git config --global user.name "First Last"
git config --global user.email "first.last@organization.com"
git config --global commit.gpgsign true
```

## Compliance Notes

This policy satisfies FedRAMP Moderate controls CM-3 (Configuration Change Control) through mandatory PR review and audit trail, CM-5 (Access Restrictions for Change) through branch protection and CODEOWNERS, and SI-7 (Software, Firmware, and Information Integrity) through signed commits and automated integrity checks. The full commit history, PR review records, and merge logs serve as the audit evidence for these controls.
