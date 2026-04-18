"""
Sigma CLI — ``python -m zettelforge.sigma.ingest <path>``.

Thin argparse wrapper that walks a file or directory and drives
``ingest_rule`` / ``ingest_rules_dir``. In ``--dry-run`` mode the parser
runs but nothing is persisted — handy for CI fixture validation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from zettelforge.sigma.entities import from_rule_dict
from zettelforge.sigma.parser import (
    SigmaParseError,
    SigmaValidationError,
    parse_file,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m zettelforge.sigma.ingest",
        description="Parse and ingest Sigma detection rules into ZettelForge.",
    )
    p.add_argument("path", type=Path, help="Sigma rule file or directory")
    p.add_argument(
        "--domain",
        default="detection",
        help="Memory domain for ingested notes (default: detection)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse + validate + map without persisting to memory.",
    )
    p.add_argument(
        "--glob",
        default="**/*.yml",
        help="Glob used when path is a directory (default: **/*.yml).",
    )
    return p


def _iter_files(root: Path, glob: str) -> list[Path]:
    if root.is_file():
        return [root]
    # Pick up both .yml and .yaml without double-counting.
    files = {*root.glob(glob), *root.glob(glob.replace(".yml", ".yaml"))}
    return sorted(f for f in files if f.is_file())


def _dry_run(files: list[Path]) -> int:
    """Parse + map every file; return non-zero if any file failed."""
    failed = 0
    for f in files:
        try:
            rule = parse_file(f)
            entity, relations = from_rule_dict(rule)
            print(
                f"OK  {f}  id={entity.rule_id}  type={entity.rule_type}  "
                f"tags={len(entity.tags)}  edges={len(relations)}"
            )
        except (SigmaParseError, SigmaValidationError) as exc:
            print(f"FAIL {f}  {exc}", file=sys.stderr)
            failed += 1
    total = len(files)
    ok = total - failed
    print(f"\nDry-run summary: {ok}/{total} parsed, {failed} failed.")
    return 0 if failed == 0 else 1


def _ingest(files: list[Path], domain: str) -> int:
    """Persist every file via ``ingest_rule``. Non-zero exit on any failure."""
    # Lazy import — MemoryManager pulls in embeddings, LanceDB, etc.
    from zettelforge.memory_manager import MemoryManager
    from zettelforge.sigma.ingest import ingest_rule

    mm = MemoryManager()
    failed = 0
    ingested = 0
    for f in files:
        try:
            ingest_rule(f, mm, domain=domain)
            ingested += 1
            print(f"OK  {f}")
        except (SigmaParseError, SigmaValidationError) as exc:
            print(f"FAIL {f}  {exc}", file=sys.stderr)
            failed += 1
        except Exception as exc:  # pragma: no cover — defensive
            print(f"ERR  {f}  {exc}", file=sys.stderr)
            failed += 1
    print(f"\nIngest summary: {ingested}/{len(files)} ingested, {failed} failed.")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    path: Path = args.path
    if not path.exists():
        print(f"path not found: {path}", file=sys.stderr)
        return 1

    files = _iter_files(path, args.glob)
    if not files:
        print(f"no Sigma rule files matched under {path}", file=sys.stderr)
        return 1

    if args.dry_run:
        return _dry_run(files)
    return _ingest(files, domain=args.domain)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
