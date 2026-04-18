"""
Sigma ingest — high-level Python API.

Phase 3 implementation: parse → entity mapping → ``MemoryManager.remember``
+ ``ontology_store.create_entity`` + relation creation. Idempotent on
``content_sha256``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def ingest_rule(
    yaml_or_path: str | Path,
    memory_manager: Optional[Any] = None,
    *,
    source_repo: Optional[str] = None,
    source_path: Optional[str] = None,
    explain: str = "auto",
) -> str:
    """Ingest a single Sigma rule. Returns the new ``rule_id``.

    Phase 3 implementation: accepts a YAML string, ``Path`` to a ``.yml``
    file, or already-parsed dict. Enqueues an explainer job based on
    ``explain`` policy (``auto`` | ``always`` | ``never``).
    """
    raise NotImplementedError("zettelforge.sigma.ingest.ingest_rule: Phase 3")


def ingest_rules_dir(
    path: str | Path,
    memory_manager: Optional[Any] = None,
    *,
    explain: str = "auto",
) -> list[str]:
    """Recursively ingest every ``.yml``/``.yaml`` rule in a directory.

    Phase 3 implementation: walk the tree, call ``ingest_rule`` per file,
    batch explainer enqueues, return the list of rule_ids ingested.
    """
    raise NotImplementedError("zettelforge.sigma.ingest.ingest_rules_dir: Phase 3")
