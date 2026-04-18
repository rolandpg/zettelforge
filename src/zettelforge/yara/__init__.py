"""
ZettelForge YARA ingest module.

Phase 2 scaffold: exports only. Phase 3 fills implementations.
See: phase-1c-detection-rule-architecture.md §1.5 and §2.
"""

from zettelforge.yara.entities import YaraRule
from zettelforge.yara.ingest import ingest_rule, ingest_rules_dir

__all__ = ["YaraRule", "ingest_rule", "ingest_rules_dir"]
