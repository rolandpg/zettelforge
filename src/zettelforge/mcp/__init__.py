"""
ZettelForge MCP server — Model Context Protocol interface.

Exposes ZettelForge's memory system as MCP tools that any AI agent
(Claude Code, OpenClaw, etc.) can call via stdio transport.

Tools:
    zettelforge_remember    — Store threat intelligence
    zettelforge_recall      — Search and retrieve memories
    zettelforge_synthesize  — RAG synthesis over memories
    zettelforge_entity      — Fast entity lookup (actor, CVE, tool)
    zettelforge_graph       — Knowledge graph traversal
    zettelforge_stats       — Memory system statistics
    zettelforge_sync        — Trigger OpenCTI sync (enterprise)

Run with::

    python -m zettelforge.mcp

Wire into Claude Code via ``.claude.json`` or ``.mcp.json``::

    {
      "mcpServers": {
        "zettelforge": {
          "command": "python3",
          "args": ["-m", "zettelforge.mcp"]
        }
      }
    }
"""

from zettelforge.mcp.server import TOOLS, handle_tool_call, run_stdio

__all__ = ["TOOLS", "handle_tool_call", "run_stdio"]
