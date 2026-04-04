---
document_id: GOV-008
title: CI/CD Pipeline Standards
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [cicd, pipeline, continuous-integration, continuous-deployment, github-actions, gitea-actions, quality-gates, automation]
compliance_mapping: [FedRAMP-CM-3, FedRAMP-SA-10, FedRAMP-SA-11, FedRAMP-SI-7, NIST-800-171-3.4.3, NIST-800-171-3.14.2]
---

# CI/CD Pipeline Standards

## Purpose

This document defines the mandatory CI/CD pipeline stages, quality gates, artifact management, and deployment automation for all projects. The CI/CD pipeline is the automated enforcement mechanism for the governance standards. It is the authoritative check that code meets quality, security, and compliance requirements before it reaches any environment.

## Scope

Every repository with deployable code or infrastructure definitions must have a CI/CD pipeline. This includes application services, libraries, CLI tools, infrastructure-as-code, and container image builds.

## Pipeline Platform

The organization uses Gitea Actions (compatible with GitHub Actions workflow syntax) as the primary CI/CD platform. Gitea Actions is self-hosted, FOSS, and runs on the organization's own infrastructure. For projects that require Azure DevOps integration (Azure-specific deployments), Azure Pipelines (free tier, 1 parallel job) is used as a secondary deployment trigger, with Gitea Actions handling the build and test stages.

## Pipeline Stages

### Stage 1: Lint and Format Check

Runs on every push to any branch and on every PR. This stage executes: `ruff check` and `ruff format --check` for Python, `cargo fmt --check` and `cargo clippy -- -D warnings` for Rust, and any project-specific linters. This stage must complete in under 2 minutes. Failure blocks all subsequent stages.

### Stage 2: Type Check

Runs on every push and PR. Executes `mypy --strict` for Python. Rust's compiler provides this inherently during the build stage. Must complete in under 3 minutes.

### Stage 3: Unit Tests

Runs on every push and PR. Executes the full unit test suite with coverage measurement. For Python: `pytest tests/unit/ --cov --cov-report=xml --cov-fail-under=80`. For Rust: `cargo test --lib` with `cargo-tarpaulin` for coverage. Must complete in under 5 minutes for most projects. Coverage below the threshold blocks merging.

### Stage 4: Security Scanning (SAST)

Runs on every PR targeting `main`. Executes: `bandit` rules (via Ruff `S` rules) for Python, `cargo-audit` for Rust dependency vulnerabilities, `cargo-deny` for license compliance, and Semgrep (community rules) for cross-language pattern matching. Findings classified as HIGH or CRITICAL severity block merging. MEDIUM findings are logged and must be triaged within 5 business days.

### Stage 5: Build

Runs on every PR targeting `main` and on merge to `main`. Compiles the application, builds container images (if applicable), and produces versioned artifacts. Container images use multi-stage builds with minimal base images (distroless or alpine). Build artifacts are tagged with the git commit SHA for traceability.

### Stage 6: Integration Tests

Runs on merge to `main` (not on every PR push, to conserve CI resources). Spins up dependent services (database, cache, message queue) using containerized instances and runs the integration test suite against the built artifact. Must complete in under 15 minutes.

### Stage 7: Deploy to Staging

Runs automatically on successful completion of all preceding stages for the `main` branch. Deploys the built artifact to the staging environment. Staging mirrors production configuration as closely as possible per GOV-013.

### Stage 8: Smoke Tests

Runs automatically after staging deployment. Executes a lightweight suite of health checks and critical path validations against the staging environment. Verifies: the service starts and responds to health check endpoints, authentication flows work, and at least one primary API operation succeeds end-to-end.

### Stage 9: Deploy to Production

Triggered manually after staging validation (for now). As the organization matures and confidence in automated testing increases, this may be automated with a canary or blue-green deployment strategy. Production deployments are logged with the deployer identity, timestamp, artifact version, and commit SHA.

## Quality Gates Summary

A quality gate is a hard stop. If it fails, the pipeline halts and the change does not proceed.

PR quality gates (must pass before merge is allowed): lint and format check, type check, unit tests with coverage threshold, SAST scan (no HIGH/CRITICAL findings), and minimum reviewer approvals per GOV-006.

Main branch quality gates (must pass before staging deployment): all PR gates plus successful build and integration test passage.

Staging quality gates (must pass before production deployment): smoke tests pass, and no new HIGH/CRITICAL alerts in monitoring for 30 minutes post-deploy.

## Artifact Management

Built artifacts (container images, compiled binaries, Python wheels) are stored in a container registry. For homelab, this is a self-hosted registry (Docker Registry v2, FOSS) or Azure Container Registry (free tier, Basic SKU). Artifacts are tagged with both the git commit SHA (for traceability) and the semantic version (for human reference). Artifact retention: keep the latest 10 versions and any version currently deployed. Older artifacts are pruned automatically.

## Pipeline Security

Pipeline definitions are code and are subject to the same review requirements as application code (GOV-006). Secrets used in pipelines (registry credentials, deployment keys) are stored in the CI platform's secrets management, never in pipeline definition files. Pipeline logs must not contain secrets, and steps that handle secrets use masking. Pipeline execution uses ephemeral runners that are destroyed after each job to prevent state leakage between builds.

## Pipeline as Code

All pipeline definitions live in the repository they serve (`.gitea/workflows/` or `.github/workflows/`). Changes to pipeline definitions require code review. Shared pipeline templates (reusable workflow definitions) live in a dedicated `ci-templates` repository and are versioned.

## Compliance Notes

CI/CD pipeline logs serve as evidence for FedRAMP CM-3 (automated change control enforcement), SA-10 (developer configuration management), SA-11 (developer security testing integration), and SI-7 (integrity verification through automated build and test). Pipeline logs are retained for 1 year to satisfy audit evidence requirements.
