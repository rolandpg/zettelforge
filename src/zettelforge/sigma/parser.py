"""
Sigma rule parser — YAML load + JSON-schema validation.

Uses ``yaml.safe_load`` + ``jsonschema.validate`` against the vendored
SigmaHQ schemas in ``zettelforge/sigma/schemas/``.

Dispatch picks the right schema:
- ``correlation:`` key present → correlation schema
- ``filter:`` key present      → filters schema
- otherwise                    → detection-rule schema
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


class SigmaParseError(ValueError):
    """Raised when a Sigma rule cannot be parsed (bad YAML)."""


class SigmaValidationError(ValueError):
    """Raised when a Sigma rule fails JSON-schema validation."""


@dataclass
class ValidationResult:
    """Return value of :func:`validate`."""

    valid: bool
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return self.valid


def _load_schema(name: str) -> dict[str, Any]:
    """Load a vendored schema JSON by filename (cached)."""
    if name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[name]
    schema_files = resources.files("zettelforge.sigma.schemas")
    with schema_files.joinpath(name).open("rb") as fh:
        schema = json.load(fh)
    _SCHEMA_CACHE[name] = schema
    return schema


def _pick_schema(rule: dict[str, Any]) -> dict[str, Any]:
    """Pick the right vendored schema based on rule shape."""
    if isinstance(rule, dict):
        if "correlation" in rule:
            return _load_schema("sigma-correlation-rules-schema.json")
        if "filter" in rule:
            return _load_schema("sigma-filters-schema.json")
    return _load_schema("sigma-detection-rule-schema.json")


def _stringify_dates(obj: Any) -> Any:
    """Recursively coerce YAML-parsed ``date``/``datetime`` values back to
    ISO-8601 strings. The Sigma schema requires ``date``/``modified`` to
    be strings, but PyYAML's default resolver turns ``2019-10-23`` into a
    :class:`datetime.date` automatically."""
    if isinstance(obj, _dt.datetime):
        return obj.date().isoformat()
    if isinstance(obj, _dt.date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(v) for v in obj]
    return obj


def parse_yaml(text: str) -> dict[str, Any]:
    """Parse Sigma YAML text into a validated dict.

    Raises :class:`SigmaParseError` on YAML error and
    :class:`SigmaValidationError` on schema-validation error.
    """
    try:
        rule = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SigmaParseError(f"invalid YAML: {exc}") from exc

    if not isinstance(rule, dict):
        raise SigmaParseError(
            f"expected Sigma rule to be a YAML mapping, got {type(rule).__name__}"
        )

    rule = _stringify_dates(rule)

    result = validate(rule)
    if not result.valid:
        raise SigmaValidationError(
            "Sigma rule failed schema validation: " + "; ".join(result.errors)
        )
    return rule


def parse_file(path: str | Path) -> dict[str, Any]:
    """Parse a Sigma rule file into a validated dict."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise SigmaParseError(f"cannot read {p}: {exc}") from exc
    try:
        return parse_yaml(text)
    except SigmaParseError as exc:
        raise SigmaParseError(f"{p}: {exc}") from exc
    except SigmaValidationError as exc:
        raise SigmaValidationError(f"{p}: {exc}") from exc


def validate(rule: dict[str, Any]) -> ValidationResult:
    """Validate a parsed Sigma rule dict against the appropriate schema.

    Returns a :class:`ValidationResult` listing each violation with a
    dotted path to the offending field (``detection.condition``, etc.)
    rather than opaque jsonschema internals.
    """
    schema = _pick_schema(rule)
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for err in validator.iter_errors(rule):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message}")
    return ValidationResult(valid=not errors, errors=errors)
