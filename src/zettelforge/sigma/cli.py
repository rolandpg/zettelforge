"""
Sigma CLI — ``python -m zettelforge.sigma <path>``.

Phase 3 implementation: argparse wrapper around ``ingest_rule`` and
``ingest_rules_dir`` with ``--explain``, ``--dry-run``, ``--repo`` flags.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a POSIX exit code.

    Phase 3 implementation: dispatches single-file vs directory, prints
    ingest summary, exits non-zero on parser or schema validation errors.
    """
    raise NotImplementedError("zettelforge.sigma.cli.main: Phase 3")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
