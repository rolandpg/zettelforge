---
document_id: GOV-010
title: Release Management Policy
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [release, versioning, semver, changelog, hotfix, feature-flags, deployment, rollback]
compliance_mapping: [FedRAMP-CM-3, FedRAMP-CM-4, FedRAMP-SA-10, NIST-800-171-3.4.3, NIST-800-171-3.4.4]
---

# Release Management Policy

## Purpose

This document defines how software is versioned, released, documented, and rolled back. It distinguishes between deployment (code running in an environment) and release (functionality available to users), establishes the versioning scheme, and defines the changelog and hotfix processes.

## Versioning

All projects use Semantic Versioning 2.0.0 (semver.org). The version format is `MAJOR.MINOR.PATCH` where MAJOR increments for breaking changes to public interfaces, MINOR increments for new features that are backward-compatible, and PATCH increments for backward-compatible bug fixes. Pre-release versions use the format `MAJOR.MINOR.PATCH-rc.N` for release candidates.

Version 0.x.y indicates initial development. The public API is not considered stable and breaking changes may occur in minor releases. Version 1.0.0 marks the first stable release with a commitment to backward compatibility within the major version.

Version bumping is automated via Conventional Commits parsing. The CI pipeline calculates the next version from commit messages since the last release tag: any `feat` commit bumps MINOR, any `fix` or `perf` commit bumps PATCH, and any commit with `BREAKING CHANGE` in the footer or `!` after the type bumps MAJOR.

## Changelog

Every repository maintains a `CHANGELOG.md` following the Keep a Changelog format (keepachangelog.com). Changelog entries are generated automatically from Conventional Commits during the release process and reviewed by the release manager before publication. Each release entry includes the version, date, and categorized changes: Added (new features), Changed (modifications to existing functionality), Deprecated (features marked for removal), Removed (features removed), Fixed (bug fixes), and Security (vulnerability fixes).

## Release Process

For continuously deployed services (internal APIs, backend services), every merge to `main` that passes all quality gates is a potential release. The version is calculated, the changelog is updated, and a git tag is created automatically. Deployment to production follows the CI/CD pipeline (GOV-008).

For versioned artifacts (libraries, CLI tools, SDKs), releases are triggered manually by creating a release branch from `main`, generating the changelog, and tagging the release. The release artifact is built from the tag and published to the appropriate registry.

## Hotfix Process

Hotfixes follow the emergency change process in GOV-001. The hotfix branch is created from `main`, contains only the minimal fix, and is merged with expedited review (synchronous review by one peer). The hotfix increments the PATCH version. A post-incident retrospective documents the root cause and any preventive measures within 5 business days.

## Rollback Procedure

Every deployment must have a documented rollback path. For containerized services, rollback means redeploying the previous container image version. For database changes, rollback requires reversible migrations (every migration has an `up` and `down` path). Rollback is executed by reverting the deployment to the previous artifact version, not by reverting git commits and redeploying. The rollback procedure is tested in staging before it is needed in production.

## Feature Flags

Feature flags decouple deployment from release. Code can be deployed to production behind a flag and activated for specific users, percentages, or environments without redeployment. Feature flags are managed through application configuration (not a third-party SaaS service, to maintain FOSS alignment). The flag configuration is version-controlled and follows the same review process as code changes. Flags have an expiration date. Stale flags (older than 90 days after full rollout or abandonment) are cleaned up as technical debt per GOV-015.

## Compliance Notes

This policy supports FedRAMP CM-3 (Configuration Change Control), CM-4 (Security Impact Analysis through changelog review), and SA-10 (Developer Configuration Management through versioned and tagged releases).
