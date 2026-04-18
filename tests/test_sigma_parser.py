"""Tests for zettelforge.sigma.parser.

Covers YAML safe-load discipline, happy-path parse_file on the vendored
public-spec fixtures, and schema-validation error surfacing with field
paths rather than opaque jsonschema internals.
"""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "sigma"


def test_parse_file_process_creation() -> None:
    from zettelforge.sigma.parser import parse_file

    rule = parse_file(FIXTURES / "process_creation_example.yml")
    assert rule["title"] == "Whoami Execution"
    assert rule["logsource"]["category"] == "process_creation"
    assert rule["logsource"]["product"] == "windows"
    # YAML-parsed dates must be coerced back to ISO strings so schema
    # validation (type=string) passes.
    assert isinstance(rule["date"], str)
    assert rule["date"] == "2019-10-23"


def test_parse_file_cloud_windows_security() -> None:
    from zettelforge.sigma.parser import parse_file

    rule = parse_file(FIXTURES / "cloud_example.yml")
    assert rule["logsource"]["product"] == "windows"
    assert rule["logsource"]["service"] == "security"
    assert rule["id"] == "929a690e-bef0-4204-a928-ef5e620d6fcb"


def test_parse_file_correlation() -> None:
    from zettelforge.sigma.parser import parse_file

    rule = parse_file(FIXTURES / "correlation_example.yml")
    assert rule["correlation"]["type"] == "event_count"
    assert rule["correlation"]["timespan"] == "1h"


def test_parse_yaml_inline_string() -> None:
    from zettelforge.sigma.parser import parse_yaml

    src = (FIXTURES / "process_creation_example.yml").read_text()
    rule = parse_yaml(src)
    assert rule["title"] == "Whoami Execution"


def test_parse_yaml_invalid_raises_parse_error() -> None:
    from zettelforge.sigma.parser import SigmaParseError, parse_yaml

    # Unclosed quote → YAML lexer fails.
    with pytest.raises(SigmaParseError):
        parse_yaml('title: "unterminated\n  logsource: foo')


def test_parse_yaml_non_mapping_raises() -> None:
    from zettelforge.sigma.parser import SigmaParseError, parse_yaml

    # Top-level scalar is legal YAML but illegal Sigma.
    with pytest.raises(SigmaParseError):
        parse_yaml("just a string\n")


def test_parse_yaml_schema_violation_surfaces_field_path() -> None:
    """Schema errors must name the offending field, not leak jsonschema
    internals. Required title is missing here."""
    from zettelforge.sigma.parser import SigmaValidationError, parse_yaml

    bad = (
        "id: 11111111-1111-1111-1111-111111111111\n"
        "logsource:\n  product: windows\n"
        "detection:\n  selection:\n    a: b\n  condition: selection\n"
    )
    with pytest.raises(SigmaValidationError) as exc:
        parse_yaml(bad)
    msg = str(exc.value)
    # Root-level required-field error mentions the field name.
    assert "title" in msg


def test_validate_returns_result_with_paths() -> None:
    """``validate`` exposes the raw result object so callers can inspect
    per-field errors without raising."""
    from zettelforge.sigma.parser import validate

    # Missing ``title`` AND ``logsource`` + bad level enum.
    rule = {
        "detection": {"selection": {"a": "b"}, "condition": "selection"},
        "level": "catastrophic",  # not in the enum
    }
    result = validate(rule)
    assert result.valid is False
    # There should be at least one error mentioning title, and an enum
    # error on ``level`` with the field path.
    joined = " | ".join(result.errors)
    assert "title" in joined
    assert any(e.startswith("level:") for e in result.errors)


def test_parse_file_raises_on_missing_path(tmp_path: Path) -> None:
    from zettelforge.sigma.parser import SigmaParseError, parse_file

    missing = tmp_path / "does_not_exist.yml"
    with pytest.raises(SigmaParseError):
        parse_file(missing)
