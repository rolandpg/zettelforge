"""Test skeletons for zettelforge.yara.ingest.

Phase 2: xfail placeholders for Phase 3 implementation.
"""

from pathlib import Path

import pytest

XFAIL_REASON = "Phase 3 implementation pending — feat/detection-rules-first-class"
FIXTURES = Path(__file__).parent / "fixtures" / "yara"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_ingest_rule_single_file() -> None:
    from zettelforge.yara.ingest import ingest_rule

    ids = ingest_rule(FIXTURES / "technique_loader.yar")
    assert len(ids) == 1


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_ingest_rules_dir_walks_tree() -> None:
    from zettelforge.yara.ingest import ingest_rules_dir

    ids = ingest_rules_dir(FIXTURES)
    assert len(ids) >= 3


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_ingest_rule_idempotent_on_content_sha256() -> None:
    from zettelforge.yara.ingest import ingest_rule

    first = ingest_rule(FIXTURES / "technique_loader.yar")
    second = ingest_rule(FIXTURES / "technique_loader.yar")
    assert first == second
