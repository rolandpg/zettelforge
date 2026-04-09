---
# GOV-023: Workspace and Artifact Lifecycle Policy

**Version:** 1.0
**Effective Date:** 2026-04-08
**Owner:** Patrick Roland, Director of SOC Services
**Classification:** Internal (Tier 2 per GOV-021)
**Review Cycle:** Annual or upon significant infrastructure change

---

## 1. Purpose

This policy establishes standards for organizing project directories, managing codebase structure, classifying project lifecycle state, and maintaining workspace hygiene across the Roland Fleet development environment. It ensures that all projects are discoverable, consistently structured, and actively managed through their lifecycle from creation to archival.

This policy complements GOV-002 (Version Control), GOV-013 (Environment Management), GOV-014 (Secrets Management), and GOV-021 (Data Classification). Where those policies govern what goes into repositories and how secrets are handled, this policy governs how projects are organized on the filesystem, when they transition between lifecycle states, and how artifacts are retained or removed.

---

## 2. Scope

This policy applies to all project directories, codebases, agent workspaces, and supporting artifacts on Roland Fleet infrastructure, including the DGX Spark (192.168.1.70), PRolan_Office (192.168.1.149), and any future compute nodes. It applies to human-authored and agent-authored code equally.

OpenClaw agent workspace internals (SOUL.md, AGENTS.md, MEMORY.md, etc.) are governed by OpenClaw's own workspace conventions and are excluded from reorganization under this policy. However, project repositories referenced by or contained within agent workspaces are in scope.

---

## 3. Definitions

**Project:** A directory containing source code, configuration, documentation, or build artifacts that serves a distinct purpose and could reasonably be described by a README.

**Workspace:** An OpenClaw agent's operational directory (e.g., `~/.openclaw/workspace-nexus/`). Workspaces contain agent identity files, memory, and may contain or reference projects.

**Artifact:** Any file produced by a build, test, or deployment process that is not source code (e.g., compiled binaries, Docker images, log files, coverage reports).

**Lifecycle State:** The current classification of a project's activity and relevance. See Section 5.

---

## 4. Project Directory Structure

### 4.1 Top-Level Organization

All project repositories reside under a consistent root. The recommended structure:

```
/home/rolandpg/
  projects/                    # Active project repositories
    <project-name>/            # One directory per project
  archive/                     # Compressed snapshots of retired projects
    YYYY-MM-DD/                # Date-stamped archive batches
  .openclaw/                   # OpenClaw config and agent workspaces (exempt from reorganization)
  tracker/                     # Planka data volume (exempt, Docker-managed)
```

Projects that are actively deployed as services (Docker Compose stacks, systemd units) may remain at their current paths if moving them would break volume mounts or service configurations. In such cases, a symlink from `projects/<name>` to the actual location is acceptable. Document the symlink in the project's README.

### 4.2 Per-Project Layout

Every project directory, regardless of language, must contain at minimum:

| File/Directory | Purpose | Required |
|---|---|---|
| `README.md` | Project purpose, setup instructions, current status | Yes |
| `LICENSE` or `LICENSE.md` | License terms (even for internal-only projects, state "Internal Use Only") | Yes |
| `.gitignore` | Exclusion rules per GOV-002 and GOV-014 | Yes (if git-tracked) |
| `src/` or language-equivalent | Source code, separated from project root | Recommended |
| `tests/` | Test suite | Recommended |
| `docs/` | Extended documentation, architecture decisions | Recommended |

### 4.3 Language-Specific Layout Standards

Projects must follow the idiomatic layout conventions of their primary language. These are not suggestions; they are the expected structure for any new project and the target structure for reorganization of existing projects.

**Python Projects** (reference: Real Python project layout best practices):

```
<project-name>/
  README.md
  LICENSE
  pyproject.toml             # Project metadata and build config (preferred over setup.py)
  .gitignore
  src/
    <package_name>/          # src/ layout for installable packages
      __init__.py
      core.py
      api.py
  tests/
    test_core.py
    test_api.py
  docs/
```

For simple scripts or internal tools that will not be packaged, the flat layout is acceptable:

```
<project-name>/
  README.md
  .gitignore
  <package_name>/
    __init__.py
    main.py
  tests/
```

Key principles: importable code in a package directory (not loose `.py` files at root), tests in a dedicated `tests/` directory mirroring package structure, configuration files at project root.

**Rust Projects** (reference: Cargo package layout):

```
<project-name>/
  README.md
  LICENSE
  Cargo.toml
  Cargo.lock
  .gitignore
  src/
    lib.rs                   # Library crate root
    main.rs                  # Binary crate root
    bin/                     # Additional binaries
  tests/                     # Integration tests
  benches/                   # Benchmarks
  examples/                  # Example programs
```

Follow Cargo conventions exactly. Cargo's auto-discovery relies on this structure.

**Multi-Language Projects** (e.g., Python backend + Rust extension via PyO3):

```
<project-name>/
  README.md
  LICENSE
  .gitignore
  backend/                   # Python service
    pyproject.toml
    src/
    tests/
  extensions/                # Rust extension module
    Cargo.toml
    src/
  frontend/                  # If applicable (React/TS)
    package.json
    src/
  docker-compose.yml         # Orchestration at project root
  docs/
```

Each language subtree follows its own idiomatic layout. Shared orchestration (Docker Compose, Makefiles, CI) lives at the project root.

**Web/Frontend Projects** (React, TypeScript, Vite):

```
<project-name>/
  README.md
  LICENSE
  package.json
  tsconfig.json
  .gitignore
  src/
    components/
    pages/
    hooks/
    utils/
    App.tsx
  public/
  tests/
```

Structure by domain or feature rather than by file type. Colocate components with their tests and styles when the project grows beyond a handful of files.

### 4.4 Codebase Composition Principles

Reference: Schindler, "How to Structure Any Codebase" (andamp, 2024).

Every codebase, regardless of size, consists of three categories of code:

1. **Business logic:** Domain-specific rules and workflows particular to the problem being solved. This is the messy, mutable layer that changes with requirements.
2. **Library code:** Reusable, unopinionated utilities with minimal dependencies and simple APIs. Write these like you would write a library for others: stateless where possible, well-tested, loosely coupled.
3. **Data:** Models, schemas, configuration, and state definitions.

When organizing or refactoring code, keep tightly coupled code physically close. Move models into the same directory as the code that uses them, not into a global `models/` folder. The resulting directory structure should approximate the call graph of the application, grouping code by domain rather than by technical layer.

This means: prefer `orders/service.py`, `orders/models.py`, `orders/api.py` over `services/orders.py`, `models/orders.py`, `api/orders.py`.

---

## 5. Project Lifecycle States

Every project directory is classified into one of four lifecycle states:

| State | Definition | Criteria | Action |
|---|---|---|---|
| **Active** | Under development or running in production | Modified within 30 days, OR has a running service (Docker, systemd), OR referenced in current sprint/tracker | Maintain per this policy |
| **Stale** | Not actively developed but potentially useful | No modifications in 30+ days, no running service, no active tracker cards | Review monthly; propose archive or reactivation |
| **Deprecated** | Explicitly superseded by another project | Successor identified and documented, OR owner has declared end-of-life | Archive within 14 days of deprecation declaration |
| **Archived** | Compressed and stored for reference | Compressed tarball in `archive/YYYY-MM-DD/`, README preserved at archive root | Retain for 1 year minimum; delete after review |

### 5.1 State Transitions

State changes are documented in the project's README and in the Planka tracker.

- **Active to Stale:** Automatic classification when 30 days pass without modification and no running service exists. Flagged during monthly hygiene review.
- **Stale to Active:** Any meaningful commit, service deployment, or tracker card assignment reactivates the project.
- **Stale to Deprecated:** Owner (Patrick) declares deprecation with a reason and successor reference.
- **Active to Deprecated:** Immediate deprecation is permitted when a replacement is deployed.
- **Deprecated to Archived:** Archive within 14 days. Create `archive/YYYY-MM-DD/<project-name>.tar.gz`. Preserve the README as `archive/YYYY-MM-DD/<project-name>.README.md` alongside the tarball for discoverability without extraction.
- **Archived to Active:** Extract, move to `projects/`, update README, resume normal development. This should be rare.

### 5.2 Archival Procedure

1. Verify no running service depends on the directory (check `docker ps`, `systemctl --user list-units`, mounted volumes).
2. Verify all changes are committed if git-tracked. If uncommitted changes exist, commit with message `"pre-archive snapshot"` or stash.
3. Run GOV-014 secrets scan: ensure no plaintext credentials in the directory.
4. Create compressed archive: `tar czf archive/YYYY-MM-DD/<project-name>.tar.gz <project-path>/`
5. Copy README: `cp <project-path>/README.md archive/YYYY-MM-DD/<project-name>.README.md`
6. Log the archive action to a manifest: `archive/YYYY-MM-DD/MANIFEST.md`
7. Remove the original directory (use `trash` or move to a staging location; never `rm -rf` without the archive confirmed).
8. Update Planka tracker and agent workspace TOOLS.md files with the path change.

---

## 6. Environment Separation

Reference: Statsig, "Dev vs. Staging vs. Production" (2025); GOV-013 (Environment Management).

This policy reinforces GOV-013's requirement that changes flow through defined environments before reaching production. The minimum viable environment set:

| Environment | Purpose | Data Policy (per GOV-021) |
|---|---|---|
| **Development** | Local experimentation, feature work, debugging | Synthetic or anonymized data only for Tier 3+. Real data permitted for Tier 1 (Public). |
| **Staging** | Pre-production validation, integration testing | Mirrors production config with synthetic data. No Tier 3/4 data. |
| **Production** | Live services, real users, real data | Full data classification enforcement per GOV-021. |

For homelab projects where full environment parity is impractical, the minimum requirement is:

1. Configuration files must support environment-specific overrides (e.g., `config.development.json`, `config.production.json`, or environment variables).
2. No live-editing of production configuration without validation in a non-production context first. At minimum: edit locally, validate, then apply.
3. Service-affecting changes (OpenClaw config, Docker Compose, systemd units) require a pre-change backup and a documented rollback plan per the Infrastructure Change Protocol in AGENTS.md.

This does not conflict with GOV-013. It extends GOV-013's implied requirements with specific implementation guidance for the homelab context.

---

## 7. Build Artifacts and Ephemeral Files

Build artifacts, caches, and ephemeral files must not be committed to version control (reinforcing GOV-002) and should be regularly cleaned from the filesystem.

### 7.1 Standard Exclusions

Every `.gitignore` must exclude at minimum:

```
# Build artifacts
__pycache__/
*.pyc
*.pyo
target/                    # Rust
build/
dist/
node_modules/
.venv/
*.egg-info/

# IDE and editor files
.vscode/
.idea/
*.swp
*.swo

# Environment and secrets (per GOV-014)
.env
.env.*
!.env.example
*.key
*.pem
*.p12
*-credentials.json
*-secrets.json

# OS artifacts
.DS_Store
Thumbs.db
```

### 7.2 Cleanup Schedule

During the monthly hygiene review (Section 8), check for and remove:

- Orphaned Docker volumes: `docker volume ls -f dangling=true`
- Stale Docker images: `docker image prune --filter "until=720h"` (30 days)
- Build artifacts in project directories older than 30 days
- Log files in `/tmp/` or project directories exceeding 100MB
- Stale git branches: branches with no commits in 60+ days (list, do not auto-delete)

---

## 8. Monthly Hygiene Review

A lightweight audit runs on the first Sunday of each month. This is a standing task assigned to the designated operations agent (currently Nexus) with review by the fleet lead (currently Patton).

### 8.1 Review Checklist

1. Scan all project directories for lifecycle state changes (new, newly stale, newly deprecated).
2. Verify every Active project has a README and .gitignore.
3. Check total disk usage and flag directories exceeding 5GB.
4. Run GOV-014 secrets scan across all project directories.
5. Check for orphaned Docker volumes and stale images.
6. Check for uncommitted changes across all git repositories.
7. Verify no stale git branches have accumulated (60+ days without commit).
8. Produce a hygiene report: `~/.openclaw/workspace-nexus/reports/hygiene-YYYY-MM.md`

### 8.2 Review Output

The hygiene report proposes actions (archive, clean, restructure) but does not execute them. Patrick reviews and approves before any filesystem changes occur. Approved actions follow the archival procedure in Section 5.2 or the reorganization safety protocol in the Nexus task directive.

---

## 9. Governance Cross-References

| Policy | Relationship to GOV-023 |
|---|---|
| GOV-002 (Version Control) | GOV-002 governs repository hygiene, branch protection, and commit standards. GOV-023 governs filesystem organization and project lifecycle. GOV-023's .gitignore requirements (Section 7.1) are additive to GOV-002's existing .gitignore mandate. |
| GOV-013 (Environment Management) | GOV-013 requires non-production validation before production changes. GOV-023 Section 6 provides specific implementation guidance for the homelab context without overriding GOV-013. |
| GOV-014 (Secrets Management) | GOV-014 prohibits secrets in version control and defines storage requirements. GOV-023 reinforces this through mandatory secrets scanning during archival (Section 5.2) and monthly hygiene (Section 8.1). |
| GOV-021 (Data Classification) | GOV-021 defines data tiers and storage requirements. GOV-023 Section 6 references GOV-021's tier system for environment data policy. No conflict. |

---

## 10. Exceptions

Directories managed by external tools with their own layout requirements (e.g., `~/.openclaw/` internals, Docker volume mounts, Planka data directories) are exempt from the per-project layout standards in Section 4.2. They are still subject to lifecycle classification (Section 5) and secrets scanning (Section 8.1).

Temporary experimental directories (one-off scripts, quick tests) are exempt from full project structure requirements if they are removed within 7 days. If retained beyond 7 days, they must be promoted to a proper project structure or archived.

---

## 11. Enforcement

This policy is enforced through the monthly hygiene review (Section 8) and the agent workspace behavioral rules (AGENTS.md Infrastructure Change Protocol). Agents creating new projects are expected to scaffold the correct structure from the start. Agents reorganizing existing projects must follow the three-phase audit/propose/execute protocol and obtain Patrick's approval before any filesystem changes.

Violations are tracked in the Planka Governance Compliance board.

---

## 12. References

- Real Python, "Project Layout Best Practices" (2026). Python project structure conventions.
- Rust/Cargo, "Package Layout" (doc.rust-lang.org). Cargo's canonical directory structure.
- Schindler, F., "How to Structure Any Codebase" (andamp, 2024). Business logic / library code / data decomposition.
- Statsig, "Dev vs. Staging vs. Production: Key Differences" (2025). Environment separation rationale and implementation.
- GOV-002: Version Control Policy
- GOV-013: Environment Management Policy
- GOV-014: Secrets Management Policy
- GOV-021: Data Classification Policy

---

**Document History:**

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-04-08 | Patrick Roland / Claude (draft) | Initial release |
