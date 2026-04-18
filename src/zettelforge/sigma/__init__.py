"""
ZettelForge Sigma ingest module.

Phase 2 scaffold: exports only. Phase 3 fills implementations.
See: phase-1c-detection-rule-architecture.md §1.4 and phase-1b-sigma-architecture.md.
"""

from zettelforge.sigma.entities import SigmaRule
from zettelforge.sigma.ingest import ingest_rule, ingest_rules_dir

__all__ = ["SigmaRule", "ingest_rule", "ingest_rules_dir"]
