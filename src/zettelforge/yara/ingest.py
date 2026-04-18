"""
YARA ingest — high-level Python API.

Phase 3 implementation: parse → CCCS validate → entity mapping →
``MemoryManager.remember`` + ``ontology_store.create_entity`` + relation
creation. Idempotent on ``content_sha256``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def ingest_rule(
    yara_or_path: str | Path,
    memory_manager: Optional[Any] = None,
    *,
    source_repo: Optional[str] = None,
    source_path: Optional[str] = None,
    explain: str = "auto",
) -> list[str]:
    """Ingest one or more YARA rules from a file or text. Returns rule_ids.

    Phase 3 implementation: accepts YARA text, a ``Path`` to a ``.yar``
    file, or a rule dict. Returns a list because one file may contain
    multiple rules.
    """
    raise NotImplementedError("zettelforge.yara.ingest.ingest_rule: Phase 3")


def ingest_rules_dir(
    path: str | Path,
    memory_manager: Optional[Any] = None,
    *,
    explain: str = "auto",
) -> list[str]:
    """Recursively ingest every ``.yar``/``.yara`` rule in a directory.

    Phase 3 implementation: walk the tree, call ``ingest_rule`` per file,
    batch explainer enqueues, return flat list of rule_ids ingested.
    """
    raise NotImplementedError("zettelforge.yara.ingest.ingest_rules_dir: Phase 3")
