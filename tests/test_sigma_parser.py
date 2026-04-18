"""Test skeletons for zettelforge.sigma.parser.

Phase 2: xfail placeholders for Phase 3 implementation.
"""

from pathlib import Path

import pytest

XFAIL_REASON = "Phase 3 implementation pending — feat/detection-rules-first-class"
FIXTURES = Path(__file__).parent / "fixtures" / "sigma"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_parse_file_process_creation() -> None:
    from zettelforge.sigma.parser import parse_file

    rule = parse_file(FIXTURES / "process_creation_example.yml")
    assert rule["title"] == "Whoami Execution"
    assert rule["logsource"]["category"] == "process_creation"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_parse_file_cloud_windows_security() -> None:
    from zettelforge.sigma.parser import parse_file

    rule = parse_file(FIXTURES / "cloud_example.yml")
    assert rule["logsource"]["product"] == "windows"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_parse_file_correlation() -> None:
    from zettelforge.sigma.parser import parse_file

    rule = parse_file(FIXTURES / "correlation_example.yml")
    assert rule["correlation"]["type"] == "event_count"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_parse_yaml_inline_string() -> None:
    from zettelforge.sigma.parser import parse_yaml

    src = (FIXTURES / "process_creation_example.yml").read_text()
    rule = parse_yaml(src)
    assert rule["title"] == "Whoami Execution"
