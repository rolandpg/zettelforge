#!/usr/bin/env python3
"""Backward-compat shim — use `python -m zettelforge.mcp` instead.

This entry point is retained so existing ``.mcp.json`` configurations that
reference ``web/mcp_server.py`` keep working. New installations should wire
up ``python -m zettelforge.mcp`` which ships with the installed package.
"""

import sys
from pathlib import Path

# Ensure the src/ layout is importable when invoked from a repo clone.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zettelforge.mcp.server import run_stdio

if __name__ == "__main__":
    run_stdio()
