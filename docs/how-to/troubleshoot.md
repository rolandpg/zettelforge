---
title: "Troubleshoot ZettelForge"
description: "Diagnose the most common ZettelForge install, ingest, and recall issues — LanceDB init failures, slow embeddings, missing LLM backend, supersession over-reach, and enrichment queue backpressure."
diataxis_type: "how-to"
audience: "Operator / Developer"
tags: [troubleshooting, debugging, errors, performance]
last_updated: "2026-04-16"
version: "2.2.0"
---

# Troubleshoot ZettelForge

A short decision tree for the most common failures, grouped by the
phase they occur in. Each entry links back to the authoritative
behaviour in code or config.

## Install / first run

### `ModuleNotFoundError: No module named 'zettelforge.mcp'`

You installed a version older than v2.2.0. The MCP server only became
importable as `zettelforge.mcp` starting in v2.2.0. Upgrade:

```bash
pip install -U 'zettelforge>=2.2.0'
python -m zettelforge.mcp   # should now start the stdio server
```

### `fastembed` download stalls on first use

fastembed pulls its ONNX model on first call. If you are behind a
proxy:

```bash
export HTTPS_PROXY=http://proxy:3128
export HF_HUB_ENABLE_HF_TRANSFER=0
```

Pre-download the model outside ZettelForge:

```python
from fastembed import TextEmbedding
TextEmbedding(model_name="nomic-embed-text-v1.5-Q")
```

### Ollama backend returns empty strings

Ollama is running but the requested model is not pulled:

```bash
ollama list                       # confirm model presence
ollama pull qwen2.5:3b             # or whatever ZETTELFORGE_LLM_MODEL points to
```

## `remember()` problems

### `GovernanceViolationError: content too short`

`GovernanceValidator` enforces `governance.min_content_length` (default
1 character). Strip-then-check: the validator rejects pure whitespace
too. For benchmark or replay scenarios, set
`governance.enabled: false` in `config.yaml`.

### `remember()` is slow (> 1 s per call)

The fast path should return in ~45 ms as of v2.1.1. If you are seeing
multi-second latencies:

- You are on a version older than v2.1.1 and `_check_supersession` is
  running linearly. **Upgrade.** See CHANGELOG v2.1.1 P0-1.
- You passed `sync=True`. That is expected — it blocks until the
  background enrichment queue (causal triples, LLM NER, A-Mem
  evolution) finishes.
- `llm_ner.enabled` is `true` and the LLM backend is slow. LLM NER
  runs asynchronously, so it should not block your `remember()` call
  — but if the enrichment queue fills up (`maxsize=500`), writes
  back-pressure. Either scale the LLM or set
  `ZETTELFORGE_LLM_NER_ENABLED=false`.

### Entities I expect are not extracted

Regex-only extraction covers 13 types (CVE, ATT&CK technique, actor,
intrusion_set, tool, campaign, IPv4, domain, URL, MD5, SHA1, SHA256,
email). Conversational types (`person`, `location`, `organization`,
`event`, `activity`, `temporal`) require LLM NER. Check:

- `llm_ner.enabled` is `true` in your config (it is by default).
- Your LLM backend is reachable.
- Wait for enrichment to complete (or pass `sync=True`).

## `recall()` problems

### Zero results on obvious queries

- Check that the backend matches the data directory:
  `ZETTELFORGE_BACKEND=sqlite` (v2.2.0 default). A mismatched backend
  points at an empty database.
- The cross-encoder reranker drops low-similarity hits. Lower
  `retrieval.similarity_threshold` or raise `retrieval.default_k`.
- Notes may be superseded. Retry with `exclude_superseded=False`.

### Results include stale notes

Raise `retrieval.entity_boost` or set a tighter
`retrieval.similarity_threshold`. Notes with `tier="C"` can be
excluded with `synthesis.tier_filter: ["A", "B"]`.

### "Too many supersessions" on conversational data

Known behaviour — `_check_supersession()` is entity-overlap driven and
LOCOMO-style dialogue shares speakers. Pass
`exclude_superseded=False` on `recall()` or disable evolution via
`mm.remember(..., evolve=False)` for the ingest pass.

## MCP

### Claude Code cannot find the server

Confirm the invocation:

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

Then test the server by hand:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m zettelforge.mcp
```

You should see a JSON-RPC response listing seven tools. If the call
hangs for more than ~10 seconds on first use, the MemoryManager is
initialising embeddings/models — this only happens once per process.

### `zettelforge_sync` returns "requires zettelforge-enterprise"

The community build does not include OpenCTI sync. Install the
extension:

```bash
pip install zettelforge-enterprise
```

## Logs and diagnostics

ZettelForge writes structured JSON logs to rotating files under the
data directory (never to stdout by design — see GOV-012). Typical
locations:

```bash
tail -f ~/.amem/zettelforge.log
tail -f ~/.amem/audit.log
```

Useful log events to grep:

| Event | Meaning |
|-------|---------|
| `remember_completed` | Fast-path finished; includes note_id, duration_ms |
| `enrichment_queue_full` | Write back-pressure — scale the LLM or disable LLM NER |
| `supersession_applied` | A note was marked superseded; includes old_note_id, new_note_id |
| `lance_index_failed` | LanceDB write failed (check rebuild and disk space) |
| `governance_violation` | Input validation rejected a write |

Set `logging.level: DEBUG` in `config.yaml` for verbose output.

## Related

- [Configuration Reference](../reference/configuration.md)
- [Governance Controls Reference](../reference/governance-controls.md)
- [Retrieval Policies Reference](../reference/retrieval-policies.md)
