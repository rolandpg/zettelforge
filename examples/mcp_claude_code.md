# Using ZettelForge with Claude Code (MCP)

Add to your `.claude.json`:

```json
{
  "mcpServers": {
    "zettelforge": {
      "command": "python3",
      "args": ["-m", "zettelforge.mcp"]
    }
  }
}
```

Now Claude Code can:
- `zettelforge_remember` — Store threat intelligence
- `zettelforge_recall` — Search memories
- `zettelforge_entity` — Look up specific entities
- `zettelforge_synthesize` — Get answers from your CTI knowledge base
