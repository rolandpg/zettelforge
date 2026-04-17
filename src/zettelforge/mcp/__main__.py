"""Run the ZettelForge MCP server over stdio.

Usage::

    python -m zettelforge.mcp
"""

from zettelforge.mcp.server import run_stdio

if __name__ == "__main__":
    run_stdio()
