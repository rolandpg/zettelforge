"""
YARA CLI — ``python -m zettelforge.yara.ingest <path> [flags]``.

Usage
-----
Dry-run a directory (no writes; prints a per-rule summary)::

    python -m zettelforge.yara.ingest tests/fixtures/yara/ --dry-run

Ingest a directory into a MemoryManager::

    python -m zettelforge.yara.ingest rules/ --tier warn --domain detection

Exit codes
----------
0  — success, no errors
1  — parse errors, validation rejections in strict tier, or I/O failure
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from zettelforge.yara.entities import rule_to_entities
from zettelforge.yara.parser import parse_file


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m zettelforge.yara.ingest",
        description="Ingest YARA rules into ZettelForge memory.",
    )
    p.add_argument("path", help="Path to a .yar file or directory of rules")
    p.add_argument(
        "--tier",
        choices=["strict", "warn", "non_cccs"],
        default="warn",
        help="CCCS metadata validation tier (default: warn)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse, validate, and summarise — do not write to memory",
    )
    p.add_argument(
        "--domain",
        default="detection",
        help="Memory domain for ingested notes (default: detection)",
    )
    p.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit machine-readable JSON output instead of a human summary",
    )
    return p


def _dry_run(path: Path, tier: str) -> tuple[int, list[dict[str, Any]]]:
    """Parse and summarise every rule under ``path`` without writing."""
    targets: list[Path] = []
    if path.is_dir():
        targets = sorted({*path.rglob("*.yar"), *path.rglob("*.yara")})
    elif path.is_file():
        targets = [path]
    else:
        print(f"error: path not found: {path}", file=sys.stderr)
        return 1, []

    summaries: list[dict[str, Any]] = []
    had_error = False
    for yar_path in targets:
        try:
            rules = parse_file(yar_path)
        except Exception as exc:
            summaries.append({"file": str(yar_path), "error": str(exc)})
            had_error = True
            continue
        for rule_dict in rules:
            entity, relations = rule_to_entities(rule_dict, tier=tier)
            if tier == "strict" and entity.extra.get("cccs_compliant") != "strict":
                had_error = True
            summaries.append(
                {
                    "file": str(yar_path),
                    "rule_name": entity.rule_name,
                    "rule_id": entity.rule_id,
                    "cccs_tier": entity.extra.get("cccs_compliant"),
                    "category": entity.category,
                    "n_relations": len(relations),
                    "mitre_att": [
                        (r.get("properties") or {}).get("technique_id")
                        for r in relations
                        if r.get("rel") == "detects" and r.get("to_type") == "AttackPattern"
                    ],
                    "warnings": entity.extra.get("cccs_warnings", []),
                    "errors": entity.extra.get("cccs_errors", []),
                }
            )

    exit_code = 1 if (tier == "strict" and had_error) else 0
    # Parse errors always cause a non-zero exit code.
    if any("error" in s for s in summaries):
        exit_code = 1
    return exit_code, summaries


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    path = Path(args.path).expanduser()

    if args.dry_run:
        code, summaries = _dry_run(path, tier=args.tier)
        if args.json_out:
            print(json.dumps(summaries, indent=2))
        else:
            for s in summaries:
                if "error" in s:
                    print(f"[ERROR] {s['file']}: {s['error']}")
                    continue
                print(
                    f"[{s['cccs_tier']}] {s['rule_name']}  "
                    f"({Path(s['file']).name})  "
                    f"relations={s['n_relations']}  "
                    f"mitre={','.join(s['mitre_att']) or '-'}"
                )
                for w in s["warnings"]:
                    print(f"    warn: {w}")
                for e in s["errors"]:
                    print(f"    err : {e}")
        return code

    # Live ingest path.
    from zettelforge.memory_manager import MemoryManager
    from zettelforge.yara.ingest import ingest_rule, ingest_rules_dir

    mm = MemoryManager()
    if path.is_dir():
        result = ingest_rules_dir(path, mm, tier=args.tier, domain=args.domain)
    elif path.is_file():
        note, _rels = ingest_rule(path, mm, tier=args.tier, domain=args.domain)
        result = {
            "ingested": 1 if note is not None else 0,
            "skipped": 0 if note is not None else 1,
            "errors": [],
        }
    else:
        print(f"error: path not found: {path}", file=sys.stderr)
        return 1

    if args.json_out:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"ingested={result['ingested']} "
            f"skipped={result['skipped']} "
            f"errors={len(result['errors'])}"
        )
        for err in result["errors"]:
            print(f"  - {err}")

    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
