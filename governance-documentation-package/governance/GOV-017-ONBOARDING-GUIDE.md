---
document_id: GOV-017
title: Engineering Onboarding Guide
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [onboarding, setup, new-hire, access, development-environment, first-week, tooling]
compliance_mapping: [FedRAMP-PS-4, FedRAMP-PS-7, FedRAMP-AT-2, NIST-800-171-3.2.1, NIST-800-171-3.2.2]
---

# Engineering Onboarding Guide

## Purpose

This document provides the step-by-step process for new engineering team members to get from zero to productive. It covers system access provisioning, development environment setup, required tooling installation, and the first-week task plan. Follow each section in order. If you get stuck, note where you are and ask for help referencing this document so the team can resolve your blocker and improve this guide for the next person.

## Day 1: Access Provisioning

The CTO/CIO or designated admin provisions the following accounts before or on the new hire's start date:

Version control access: Gitea account with appropriate group memberships. Write access to assigned project repositories. Read access to all other repositories.

Azure access: Azure AD account in the organization's tenant. Contributor role on the development resource group. Reader role on the staging resource group. No production access initially (granted after 90 days and demonstrated competence, per GOV-013).

Secrets access: HashiCorp Vault AppRole credentials for local development. Documentation on which secret paths your assigned project uses (see GOV-014).

Communication: Team chat access, email, issue tracker account with project board access.

## Day 1: Development Environment Setup

### System Requirements

A development workstation with a minimum of 16GB RAM (32GB recommended for running containerized services locally), 256GB SSD, and a Linux-based OS (Ubuntu 24.04 LTS recommended) or macOS. Windows with WSL2 is acceptable but not preferred.

### Required Tooling Installation

Install in this order, as later tools depend on earlier ones:

Git (latest stable version) configured with your organizational email and GPG/SSH signing per GOV-002. Podman (FOSS container runtime, replaces Docker) or Docker Community Edition. Python 3.12+ via pyenv (manages multiple Python versions). Rust toolchain via rustup (installs rustc, cargo, and components per GOV-004). Node.js LTS via nvm (required for some build tooling, not for application development). The HashiCorp Vault CLI. The Azure CLI (`az`) configured for your tenant. OpenTofu (FOSS Terraform fork) for infrastructure work. Pre-commit framework (`pip install pre-commit`).

### Project Setup

Clone your assigned project repository. Run `pre-commit install` in the repo root. Copy `.env.example` to `.env` and fill in development values (secrets come from your local Vault instance). Run the project's setup script or follow the README's local development section. Run the test suite to verify your environment: `pytest` for Python, `cargo test` for Rust. If all tests pass, your environment is correctly configured.

## Day 2-3: Read the Governance Documents

Read the governance documents in the order specified in the New Engineer reading list (GOV-000 INDEX.md). Focus on understanding the process rather than memorizing details. These documents exist to be referenced during work, not memorized. Key takeaways to internalize: how to name branches and write commit messages (GOV-002), what your code must include before opening a PR (GOV-003 or GOV-004), where secrets go and where they never go (GOV-014), and what happens when you open a PR (GOV-006, GOV-008).

## Day 3-5: First Contribution

Your first task is a deliberately small change to a real codebase: fixing a typo in documentation, adding a missing test case, improving an error message, or resolving a "good first issue" from the backlog. The goal is to exercise the full workflow (branch, commit, PR, review, merge) in a low-stakes context. Your tech lead or assigned buddy reviews your first PR with extra guidance on process adherence.

## Offboarding Checklist

When a team member departs, the following must be completed within 24 hours: revoke Gitea access, revoke Azure AD account, rotate any shared secrets the departing member had access to, revoke Vault AppRole credentials, remove from communication channels, and document the offboarding in the access log. This checklist is maintained by the CTO/CIO or designated admin.

## Compliance Notes

This guide supports FedRAMP PS-4 (Personnel Termination through the offboarding checklist), PS-7 (Third-Party Personnel Security through access provisioning documentation), and AT-2 (Security Awareness Training through the governance document reading requirement).
