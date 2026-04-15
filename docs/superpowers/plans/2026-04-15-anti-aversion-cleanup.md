# Anti-Aversion Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all 70+ commercial signals from the ZettelForge open source repo so it feels like a genuine community project, not a sales funnel.

**Architecture:** Replace the `edition.py` gating system with a lightweight `extensions.py` loader that checks for optional packages. Ungate all features that have working JSONL implementations. Change error handling from "pay to unlock" (EditionError) to "install extension for enhanced version" (info log + graceful fallback). Remove all commercial URLs, branding, and license files from the community repo.

**Tech Stack:** Python (existing codebase), no new dependencies.

**Repo:** `/home/rolandpg/zettelforge` (the `zettelforge` standalone repo, NOT the monorepo)

---

## File Structure

### Files to Create
- `src/zettelforge/extensions.py` — Clean extension loader replacing `edition.py` gating
- `GOVERNANCE.md` — Licensing commitment and extension boundary policy
- `ARCHITECTURE.md` — Extension points documentation

### Files to Modify (grouped by task)
- `src/zettelforge/edition.py` — Gut and rewrite as thin shim over extensions.py
- `src/zettelforge/knowledge_graph.py:187-209,414-435` — Ungate temporal queries, simplify backend routing
- `src/zettelforge/memory_manager.py:323-330,848-855,886-893` — Ungate remember_report, traverse_graph, synthesize
- `src/zettelforge/__init__.py:18-25,102-125` — Remove commercial language from docstring, simplify imports
- `web/app.py:2,37,43-44,151,176-205,233,274,297,307` — Remove ThreatRecall branding, 402 responses, upgrade_url
- `web/auth.py:39,47` — Change to single-tenant mode framing
- `web/mcp_server.py:3,9-15,130-132,253` — Rename tools from threatrecall_* to zettelforge_*
- `src/zettelforge/config.py:313` — Remove THREATENGRAM_LICENSE_KEY reference
- `src/zettelforge/ocsf.py:76` — Change vendor_name from "threatengram" to "zettelforge"
- `README.md:167-210` — Replace "Community vs Enterprise" with "Extensions", remove Threatengram footer
- `CONTRIBUTING.md:25-32` — Replace edition boundary with "where to contribute"
- `CHANGELOG.md:107-112` — Soften open-core language
- `pyproject.toml:43-46` — Rename optional dep group from "enterprise" to "extensions"
- `mkdocs.yml:1-3` — Update site name to ZettelForge
- `docs/index.md:1,2,11,86,129` — Replace ThreatRecall branding with ZettelForge
- `skills/claude-code-skill.md:1-2,14-16` — Rename from ThreatRecall to ZettelForge
- `.github/ISSUE_TEMPLATE/bug_report.md:25` — Remove edition field
- `.github/ISSUE_TEMPLATE/feature_request.md:17-19` — Remove edition section
- `.github/pull_request_template.md:18` — Remove enterprise gate checkbox

### Files to Delete
- `LICENSE-ENTERPRISE` — Move to enterprise repo
- `src/zettelforge/enterprise/__init__.py` — Stub directory removed
- `src/zettelforge/enterprise/` — Directory removed
- `MANIFEST.in` line referencing LICENSE-ENTERPRISE

---

## Task 1: Create extensions.py (replaces edition gating)

**Files:**
- Create: `src/zettelforge/extensions.py`
- Test: `tests/test_extensions.py`

This is the foundation — all other tasks depend on it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_extensions.py
"""Tests for extension loader."""
import pytest
from zettelforge.extensions import has_extension, get_extension, load_extensions


class TestExtensions:
    def test_no_extensions_by_default(self):
        """Without enterprise package installed, no extensions available."""
        load_extensions()
        assert has_extension("enterprise") is False

    def test_get_missing_extension_returns_none(self):
        """Getting a missing extension returns None."""
        assert get_extension("enterprise") is None

    def test_has_extension_returns_bool(self):
        assert isinstance(has_extension("enterprise"), bool)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_extensions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'zettelforge.extensions'`

- [ ] **Step 3: Write extensions.py**

```python
# src/zettelforge/extensions.py
"""
Extension loader for optional packages.

ZettelForge checks for installed extension packages at startup.
Extensions provide alternative backends (TypeDB), integrations
(OpenCTI), and operational features (multi-tenant auth).

If no extensions are installed, all features use built-in backends.
"""
import logging
from typing import Any, Optional

_logger = logging.getLogger("zettelforge.extensions")
_extensions: dict[str, Any] = {}
_loaded = False


def load_extensions() -> None:
    """Discover and load installed extension packages."""
    global _loaded
    if _loaded:
        return
    try:
        import zettelforge_enterprise
        _extensions["enterprise"] = zettelforge_enterprise
        _logger.info("Loaded zettelforge-enterprise extensions")
    except ImportError:
        pass
    _loaded = True


def has_extension(name: str) -> bool:
    """Check if an extension is available."""
    if not _loaded:
        load_extensions()
    return name in _extensions


def get_extension(name: str) -> Optional[Any]:
    """Get a loaded extension module, or None."""
    if not _loaded:
        load_extensions()
    return _extensions.get(name)


def reset_extensions() -> None:
    """Reset extension state (for testing)."""
    global _loaded
    _extensions.clear()
    _loaded = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_extensions.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/zettelforge/extensions.py tests/test_extensions.py
git commit -m "feat: add extensions.py — clean extension loader replacing edition gating"
```

---

## Task 2: Ungate knowledge graph temporal queries

**Files:**
- Modify: `src/zettelforge/knowledge_graph.py:187-209`
- Test: `tests/test_core.py` (existing temporal tests should now pass without enterprise)

The JSONL implementations of `get_entity_timeline()` and `get_changes_since()` already exist right below the gates. Just remove the gates.

- [ ] **Step 1: Read the current gated code**

Read `src/zettelforge/knowledge_graph.py` lines 185-225 to see the exact gate pattern and the existing JSONL implementations below them.

- [ ] **Step 2: Remove the gate from get_entity_timeline()**

Find the `is_enterprise()` check and `EditionError` raise in `get_entity_timeline()`. Remove the entire gate block (the import, the check, and the raise). Keep the implementation that follows. Update the docstring to remove "[Enterprise]" and describe the community behavior.

- [ ] **Step 3: Remove the gate from get_changes_since()**

Same pattern. Find the `is_enterprise()` check and `EditionError` raise in `get_changes_since()`. Remove the gate block entirely. Keep the implementation. Update the docstring.

- [ ] **Step 4: Simplify get_knowledge_graph() backend routing**

Read `src/zettelforge/knowledge_graph.py` lines 414-435. Replace `is_enterprise()` with `has_extension("enterprise")` from the new extensions module. Change the log message from "Community edition, TypeDB requires Enterprise" to "TypeDB backend available via zettelforge-enterprise extension". The routing logic stays the same — just the gate check and messaging change.

- [ ] **Step 5: Run tests**

Run: `CI=true PYTHONPATH=src pytest tests/test_core.py tests/test_temporal_graph.py -v`
Expected: All pass. Temporal tests should now work without enterprise flag.

- [ ] **Step 6: Commit**

```bash
git add src/zettelforge/knowledge_graph.py
git commit -m "feat: ungate temporal KG queries — community gets full JSONL timeline support"
```

---

## Task 3: Ungate memory manager features

**Files:**
- Modify: `src/zettelforge/memory_manager.py:323-330,848-855,886-893`

Three features to ungate: `remember_report()`, `traverse_graph()`, `synthesize()` advanced formats.

- [ ] **Step 1: Read the gated methods**

Read `src/zettelforge/memory_manager.py` lines 318-340, 843-860, 880-900 to see the exact gate patterns.

- [ ] **Step 2: Ungate remember_report()**

Remove the `is_enterprise()` check and `EditionError` raise from `remember_report()`. The chunking implementation below the gate already works. Update docstring to describe what it does without mentioning Enterprise.

- [ ] **Step 3: Ungate traverse_graph()**

Replace the `EditionError` raise with a depth cap and info log:
```python
if max_depth > 2 and not has_extension("enterprise"):
    max_depth = 2
    self._logger.info(
        "Capping traversal at 2 hops (JSONL graph). "
        "Install zettelforge-enterprise for deeper TypeDB traversal."
    )
```
Import `has_extension` from `zettelforge.extensions` at the top of the file.

- [ ] **Step 4: Ungate synthesize() advanced formats**

Replace the `EditionError` raise with a graceful fallback:
```python
_EXTENDED_FORMATS = {"synthesized_brief", "timeline_analysis", "relationship_map"}
if format in _EXTENDED_FORMATS and not has_extension("enterprise"):
    self._logger.info(
        "Format '%s' benefits from zettelforge-enterprise. Falling back to direct_answer.",
        format,
    )
    format = "direct_answer"
```

- [ ] **Step 5: Clean up imports**

Remove `from zettelforge.edition import EditionError, is_enterprise` imports from memory_manager.py. Add `from zettelforge.extensions import has_extension` instead.

- [ ] **Step 6: Run tests**

Run: `CI=true PYTHONPATH=src pytest tests/test_core.py tests/test_edition.py -v`
Expected: All pass. Edition tests may need updating — check next.

- [ ] **Step 7: Commit**

```bash
git add src/zettelforge/memory_manager.py
git commit -m "feat: ungate remember_report, traverse_graph, synthesize — all work in community"
```

---

## Task 4: Rewrite edition.py as thin shim

**Files:**
- Modify: `src/zettelforge/edition.py`
- Modify: `tests/test_edition.py`

`edition.py` currently defines `is_enterprise()`, `EditionError`, `require_enterprise()` decorator, and license key validation. Rewrite it to delegate to `extensions.py` and remove all commercial language.

- [ ] **Step 1: Read current edition.py and test_edition.py**

Read both files in full to understand what tests exist and what they assert.

- [ ] **Step 2: Rewrite edition.py**

```python
"""
Edition detection for ZettelForge.

Checks whether the zettelforge-enterprise extension package is installed.
"""
from zettelforge.extensions import has_extension


class EditionError(Exception):
    """Raised when a feature requires an extension that is not installed."""
    pass


def is_enterprise() -> bool:
    """Check if enterprise extensions are available."""
    return has_extension("enterprise")


def edition_name() -> str:
    """Return the edition display name."""
    if is_enterprise():
        return "ZettelForge + Extensions"
    return "ZettelForge"


def reset_edition() -> None:
    """Reset edition cache (for testing)."""
    from zettelforge.extensions import reset_extensions
    reset_extensions()
```

This preserves backward compatibility — `is_enterprise()` still works for any code that calls it, but the gating pattern shifts from "raise EditionError" to "check and degrade gracefully" in the callers.

- [ ] **Step 3: Update test_edition.py**

Update tests to match the simplified API. Remove tests for license key validation (no longer in this module). Keep tests for `is_enterprise()`, `edition_name()`, `reset_edition()`.

- [ ] **Step 4: Run tests**

Run: `CI=true PYTHONPATH=src pytest tests/test_edition.py tests/test_extensions.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/zettelforge/edition.py tests/test_edition.py
git commit -m "refactor: simplify edition.py — delegates to extensions.py, no license key validation"
```

---

## Task 5: Clean web layer (app.py, auth.py, mcp_server.py)

**Files:**
- Modify: `web/app.py`
- Modify: `web/auth.py`
- Modify: `web/mcp_server.py`

Remove all ThreatRecall branding, 402 responses, upgrade URLs, and commercial messaging from the web layer.

- [ ] **Step 1: Read all three web files**

Read `web/app.py`, `web/auth.py`, `web/mcp_server.py` in full.

- [ ] **Step 2: Clean app.py**

Changes:
- Line 2 docstring: "ThreatRecall Web UI" → "ZettelForge Web UI"
- Line 43: FastAPI title always "ZettelForge" (remove conditional)
- Line 44: FastAPI description always `edition_name()` (which now returns "ZettelForge")
- Line 192: Remove `upgrade_url` field entirely from `/api/edition` response
- Lines 198-205: Change `/api/sync` from 402 to 501:
  ```python
  return JSONResponse(
      status_code=501,
      content={
          "error": "OpenCTI sync requires the zettelforge-enterprise package.",
          "docs": "https://github.com/rolandpg/zettelforge#extensions",
      },
  )
  ```
- Lines 233, 274, 307: All HTML references to "ThreatRecall" → "ZettelForge"
- Line 297: "Pull latest from OpenCTI into ThreatRecall memory" → "Pull latest from OpenCTI into ZettelForge memory"

- [ ] **Step 3: Clean auth.py**

- Line 39: Change to `"message": "Running in single-tenant mode. Multi-tenant auth available via zettelforge-enterprise."`
- Line 47: Change 402 to 501, remove `upgrade_url`, use same messaging pattern

- [ ] **Step 4: Clean mcp_server.py**

- Line 3 docstring: "ThreatRecall MCP Server" → "ZettelForge MCP Server"
- Lines 9-15: Rename all tool functions from `threatrecall_*` to `zettelforge_*`:
  - `threatrecall_remember` → `zettelforge_remember`
  - `threatrecall_recall` → `zettelforge_recall`
  - `threatrecall_entity` → `zettelforge_entity`
  - `threatrecall_graph` → `zettelforge_graph`
  - `threatrecall_stats` → `zettelforge_stats`
  - `threatrecall_sync` → `zettelforge_sync`
  - `threatrecall_synthesize` → `zettelforge_synthesize`
- Line 132: Change commercial URL to: `"error": "OpenCTI sync requires the zettelforge-enterprise package."`
- Line 253: Server name "threatrecall" → "zettelforge"

- [ ] **Step 5: Run tests**

Run: `CI=true PYTHONPATH=src pytest tests/ -v --ignore=tests/test_cti_integration.py --ignore=tests/test_typedb_client.py --tb=short 2>&1 | tail -5`
Expected: All pass (or same xfail/skip count as before).

- [ ] **Step 6: Commit**

```bash
git add web/app.py web/auth.py web/mcp_server.py
git commit -m "refactor: remove ThreatRecall branding from web layer — always ZettelForge"
```

---

## Task 6: Clean config, ocsf, __init__

**Files:**
- Modify: `src/zettelforge/config.py:313`
- Modify: `src/zettelforge/ocsf.py:76`
- Modify: `src/zettelforge/__init__.py:18-25,102-125`

- [ ] **Step 1: Read the three files**

Read the relevant sections of each file.

- [ ] **Step 2: Clean config.py**

Line 313: Change `THREATENGRAM_LICENSE_KEY` handling. Keep the env var check for backward compat but make it silent — no error messages referencing commercial entities. If the env var is set, it still activates extensions (for existing enterprise users).

- [ ] **Step 3: Clean ocsf.py**

Line 76: Change `"vendor_name": "threatengram"` → `"vendor_name": "zettelforge"`.

- [ ] **Step 4: Clean __init__.py**

Lines 18-25: Rewrite the docstring to remove "Enterprise edition (ThreatRecall by Threatengram)" language. Describe ZettelForge as a single product with optional extensions.

Lines 102-125: Simplify conditional imports from `zettelforge_enterprise`. Use `has_extension("enterprise")` pattern instead of try/except ImportError scattered through the module.

- [ ] **Step 5: Run tests**

Run: `CI=true PYTHONPATH=src pytest tests/test_config.py tests/test_governance.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/zettelforge/config.py src/zettelforge/ocsf.py src/zettelforge/__init__.py
git commit -m "refactor: remove Threatengram branding from config, OCSF, and package init"
```

---

## Task 7: Delete enterprise artifacts

**Files:**
- Delete: `LICENSE-ENTERPRISE`
- Delete: `src/zettelforge/enterprise/__init__.py`
- Delete: `src/zettelforge/enterprise/` directory
- Modify: `MANIFEST.in` — remove LICENSE-ENTERPRISE line

- [ ] **Step 1: Read MANIFEST.in**

Read the file to find the LICENSE-ENTERPRISE line.

- [ ] **Step 2: Remove enterprise directory**

```bash
rm -rf src/zettelforge/enterprise/
rm LICENSE-ENTERPRISE
```

- [ ] **Step 3: Update MANIFEST.in**

Remove the `include LICENSE-ENTERPRISE` line.

- [ ] **Step 4: Run tests**

Run: `CI=true PYTHONPATH=src pytest tests/test_edition.py tests/test_extensions.py -v`
Expected: All pass (edition.py no longer imports from enterprise/).

- [ ] **Step 5: Commit**

```bash
git rm -r src/zettelforge/enterprise/ LICENSE-ENTERPRISE
git add MANIFEST.in
git commit -m "chore: remove LICENSE-ENTERPRISE and enterprise stub — lives in separate repo"
```

---

## Task 8: Clean README, CONTRIBUTING, CHANGELOG

**Files:**
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read all three files**

Read README.md (focus on lines 160-210), CONTRIBUTING.md, CHANGELOG.md.

- [ ] **Step 2: Rewrite README "Community vs Enterprise" section**

Replace lines 167-210 with an "Extensions" section:

```markdown
## Extensions

ZettelForge is a complete, production-ready agentic memory system.
Everything documented above works out of the box.

For teams that need TypeDB-scale graph storage, OpenCTI integration,
or multi-tenant deployment, optional extensions are available:

| Extension | What it adds |
|-----------|-------------|
| TypeDB STIX 2.1 backend | Schema-enforced ontology with inference rules |
| OpenCTI sync | Bi-directional sync with OpenCTI instances |
| Multi-tenant auth | OAuth/JWT with per-tenant isolation |
| Sigma rule generation | Detection rules from extracted IOCs |

Extensions are installed separately:
```bash
pip install zettelforge-enterprise
```

**Hosted option:** [ThreatRecall](https://threatrecall.ai) provides
managed ZettelForge with all extensions, so you don't have to run
infrastructure yourself.

## License

MIT — See [LICENSE](LICENSE).
```

Also:
- Remove "Built by [Threatengram](https://threatengram.com)" from footer → "Made by Patrick Roland"
- Remove the architecture diagram `[Enterprise: TypeDB STIX 2.1]` tag → `JSONL (TypeDB via extension)`
- Remove `THREATENGRAM_LICENSE_KEY` example

- [ ] **Step 3: Rewrite CONTRIBUTING.md**

Replace the "Community vs Enterprise" section with:

```markdown
## Where to contribute

All of `src/zettelforge/` is MIT-licensed and open to contributions.
Feature ideas, bug fixes, documentation, benchmarks — all welcome.

If your contribution needs TypeDB or OpenCTI, open an issue to discuss.
We keep the extension boundary clear so contributors know their work
will always remain open source.
```

- [ ] **Step 4: Soften CHANGELOG.md**

Replace "Open-core edition system" language with neutral descriptions. Change "License key validation" to "Extension detection". Remove BSL-1.1 references.

- [ ] **Step 5: Commit**

```bash
git add README.md CONTRIBUTING.md CHANGELOG.md
git commit -m "docs: replace 'Community vs Enterprise' with 'Extensions' — community-first framing"
```

---

## Task 9: Clean docs site and MCP skill

**Files:**
- Modify: `mkdocs.yml:1-3`
- Modify: `docs/index.md`
- Modify: `skills/claude-code-skill.md`

- [ ] **Step 1: Read the three files**

Read mkdocs.yml lines 1-10, docs/index.md in full, skills/claude-code-skill.md in full.

- [ ] **Step 2: Update mkdocs.yml**

- Line 1: `site_name: ZettelForge Documentation`
- Line 2: Keep `site_url: https://docs.threatrecall.ai` (this is the hosted docs URL, it's fine)
- Line 3: `description: "ZettelForge — agentic memory for cyber threat intelligence"`

- [ ] **Step 3: Update docs/index.md**

Replace all "ThreatRecall" references with "ZettelForge". Remove "[Enterprise]" tags from feature tables. Change "ThreatRecall is a production-grade..." to "ZettelForge is a production-grade...".

- [ ] **Step 4: Update skills/claude-code-skill.md**

Rename from "ThreatRecall: CTI Agentic Memory" to "ZettelForge: CTI Agentic Memory". Update all tool references from `threatrecall_*` to `zettelforge_*` to match the MCP server rename in Task 5.

- [ ] **Step 5: Update pyproject.toml**

Rename the optional dependency group:
```toml
[project.optional-dependencies]
extensions = ["zettelforge-enterprise>=2.1.0"]
```

- [ ] **Step 6: Commit**

```bash
git add mkdocs.yml docs/index.md skills/claude-code-skill.md pyproject.toml
git commit -m "docs: rebrand docs site and MCP skill from ThreatRecall to ZettelForge"
```

---

## Task 10: Clean issue templates and PR template

**Files:**
- Modify: `.github/ISSUE_TEMPLATE/bug_report.md`
- Modify: `.github/ISSUE_TEMPLATE/feature_request.md`
- Modify: `.github/pull_request_template.md`

- [ ] **Step 1: Read all three templates**

- [ ] **Step 2: Update bug_report.md**

Remove `Edition: (community / enterprise)` field. Replace with:
```markdown
- Extensions installed: (none / zettelforge-enterprise)
```

- [ ] **Step 3: Update feature_request.md**

Remove the "Should this be a Community or Enterprise feature?" section. Replace with:
```markdown
## Scope
Does this feature need external infrastructure (TypeDB, OpenCTI)?
- [ ] No — works with built-in backends
- [ ] Yes — describe what infrastructure is needed
```

- [ ] **Step 4: Update pull_request_template.md**

Remove "No enterprise features added to community code without discussion". Replace with:
```markdown
- [ ] No new external infrastructure dependencies without discussion
```

- [ ] **Step 5: Commit**

```bash
git add .github/
git commit -m "chore: remove edition framing from issue and PR templates"
```

---

## Task 11: Add governance and architecture docs

**Files:**
- Create: `GOVERNANCE.md`
- Create: `ARCHITECTURE.md`

- [ ] **Step 1: Write GOVERNANCE.md**

```markdown
# Governance

## Maintainer

ZettelForge is maintained by Patrick Roland (@rolandpg).

## Licensing Commitment

ZettelForge is MIT licensed. This will not change.

## Extension Boundary

The extension package (`zettelforge-enterprise`) provides features
that require external infrastructure (TypeDB, OpenCTI, multi-tenant
OAuth). The open source project will never be degraded to create
commercial incentive.

Rule: if a feature works with JSONL + local embeddings, it belongs
in this repo.

## Contributions

Community contributions are reviewed on their technical merits.
All contributions to this repository remain MIT licensed.
```

- [ ] **Step 2: Write ARCHITECTURE.md**

```markdown
# Architecture

## Storage Backends

ZettelForge uses a backend abstraction for the knowledge graph:

- **JSONL** (default): File-based, zero-config, works everywhere.
- **TypeDB** (via extension): STIX 2.1 ontology with inference rules.

Set `ZETTELFORGE_BACKEND` environment variable to select.

## Extension Points

Extensions are optional packages discovered at startup via
`src/zettelforge/extensions.py`. If installed, they provide
alternative backends and integrations.

### Knowledge Graph
- Default: JSONL (`src/zettelforge/knowledge_graph.py`)
- Extension: TypeDB STIX 2.1 (`zettelforge-enterprise`)

### Authentication
- Default: Single-tenant, no auth
- Extension: Multi-tenant OAuth/JWT (`zettelforge-enterprise`)

### Integrations
- OpenCTI sync: extension (requires running OpenCTI instance)
- Sigma generation: extension

## Why These Boundaries

TypeDB requires a running server. OpenCTI is a complex platform.
These dependencies should not be required to try ZettelForge.

The JSONL backends are not toy implementations — they are
production-capable for single-user and small-team deployments.
```

- [ ] **Step 3: Commit**

```bash
git add GOVERNANCE.md ARCHITECTURE.md
git commit -m "docs: add GOVERNANCE.md (MIT commitment) and ARCHITECTURE.md (extension points)"
```

---

## Task 12: Full verification and final commit

- [ ] **Step 1: Run full test suite**

```bash
CI=true PYTHONPATH=src pytest tests/ -v --ignore=tests/test_cti_integration.py --ignore=tests/test_typedb_client.py --tb=short
```

Expected: Same pass/skip/xfail count as before cleanup (155 pass, 5 skip, 1 xfail, 1 xpass or similar). Zero new failures.

- [ ] **Step 2: Verify zero commercial signals remain**

```bash
grep -rli "threatengram" src/ web/ docs/ README.md CONTRIBUTING.md CHANGELOG.md mkdocs.yml .github/ skills/ --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" --include="*.toml" --include="*.txt" 2>/dev/null
```

Expected: Zero results (except possibly docs.threatrecall.ai URL in mkdocs.yml which is the hosted docs site).

```bash
grep -rli "EditionError" src/ web/ --include="*.py" 2>/dev/null
```

Expected: Only `edition.py` (class definition) and possibly test files. No raises in feature code.

```bash
grep -rli "upgrade_url" src/ web/ --include="*.py" 2>/dev/null
```

Expected: Zero results.

```bash
grep -rli "402" web/ --include="*.py" 2>/dev/null
```

Expected: Zero results (all changed to 501).

- [ ] **Step 3: Rebuild docs site**

```bash
mkdocs build --clean
grep -rli "threatengram\|ThreatRecall" site/ 2>/dev/null | wc -l
```

Expected: Zero results (except possibly the docs URL in navigation).

- [ ] **Step 4: Push**

```bash
git push origin master
```

- [ ] **Step 5: Verify CI passes**

Monitor the CI run. Expected: green across lint, test, governance, build.
