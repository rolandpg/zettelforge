"""Test skeletons for zettelforge.yara.parser.

Phase 2: xfail placeholders for Phase 3 implementation.
"""

from pathlib import Path

import pytest

XFAIL_REASON = "Phase 3 implementation pending — feat/detection-rules-first-class"
FIXTURES = Path(__file__).parent / "fixtures" / "yara"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_parse_file_plain_yara() -> None:
    from zettelforge.yara.parser import parse_file

    rules = parse_file(FIXTURES / "malware_hash.yar")
    assert rules[0]["rule_name"] == "silent_banker"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_parse_file_cccs_technique_rule() -> None:
    from zettelforge.yara.parser import parse_file

    rules = parse_file(FIXTURES / "technique_loader.yar")
    assert rules[0]["rule_name"] == "MemoryModule"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_parse_file_webshell_with_import() -> None:
    from zettelforge.yara.parser import parse_file

    rules = parse_file(FIXTURES / "webshell.yar")
    assert "pe" in rules[0].get("imports", [])


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_parse_text_inline_string() -> None:
    from zettelforge.yara.parser import parse_text

    src = (FIXTURES / "malware_hash.yar").read_text()
    rules = parse_text(src)
    assert rules[0]["rule_name"] == "silent_banker"
