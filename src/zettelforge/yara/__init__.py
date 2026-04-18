"""
ZettelForge YARA ingest module.

Phase 3 implementation. See phase-1c-detection-rule-architecture.md §1.5
and §2 for the design rationale. Public surface mirrors
:mod:`zettelforge.sigma` for parity — callers can ``from zettelforge.yara
import parse_file, ingest_rule, ...`` without reaching into submodules.
"""

from zettelforge.yara.cccs_metadata import YaraValidationError, validate_metadata
from zettelforge.yara.entities import YaraRule, rule_to_entities
from zettelforge.yara.ingest import ingest_rule, ingest_rules_dir
from zettelforge.yara.parser import YaraParseError, parse_file, parse_yara
from zettelforge.yara.tags import resolve_yara_tag

__all__ = [
    "YaraParseError",
    "YaraRule",
    "YaraValidationError",
    "ingest_rule",
    "ingest_rules_dir",
    "parse_file",
    "parse_yara",
    "resolve_yara_tag",
    "rule_to_entities",
    "validate_metadata",
]
