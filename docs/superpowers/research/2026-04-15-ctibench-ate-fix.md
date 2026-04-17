# CTIBench ATE Fix Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement.

**Goal:** Root-cause and fix the CTI-ATE benchmark failure where 18/20 samples return `retrieved_count: 0`, achieving F1 >= 0.30.

**Architecture:** The benchmark creates a fresh temp MemoryManager, ingests ATT&CK techniques via `mm.remember()` into domain `attack_techniques`, ingests CTI descriptions into domain `cti`, then queries `mm.recall(query, k=25, domain="attack_techniques")`. The zero-retrieval problem means notes ingested into `attack_techniques` are not being found by the retriever at query time -- this is an ingestion/indexing pipeline failure, not a recall parameter issue.

---

### Task 1: Diagnostic Script (Root Cause Analysis)

**Files:**
- Create: `benchmarks/ctibench_ate_diagnosis.py`

This task validates each stage of the ingestion-to-retrieval pipeline for a single sample.

- [ ] Step 1: Write a diagnostic script that ingests 5 ATT&CK techniques into a temp MemoryManager, then checks each layer:

```python
#!/usr/bin/env python3
"""
End-to-end diagnosis of CTI-ATE retrieval failure.
Tests each layer: JSONL write, LanceDB index, vector retrieval.
"""
import tempfile, json
from zettelforge import MemoryManager
from zettelforge.vector_memory import get_embedding

def diagnose():
    tmpdir = tempfile.mkdtemp(prefix="ctibench_diag_")
    mm = MemoryManager(
        jsonl_path=f"{tmpdir}/notes.jsonl",
        lance_path=f"{tmpdir}/vectordb",
    )

    # Ingest a known technique
    content = "T1071 Application Layer Protocol: Adversaries may communicate using OSI application layer protocols to avoid detection."
    note, status = mm.remember(
        content=content,
        source_type="mitre_attack",
        source_ref="https://attack.mitre.org/techniques/T1071/",
        domain="attack_techniques",
    )
    print(f"[1] Ingest: note_id={note.id}, status={status}")
    print(f"    Embedding dims: {len(note.embedding.vector)}")
    print(f"    Embedding non-zero: {any(v != 0 for v in note.embedding.vector)}")

    # Check JSONL
    with open(f"{tmpdir}/notes.jsonl") as f:
        lines = [l for l in f if l.strip()]
    print(f"[2] JSONL: {len(lines)} lines written")

    # Check LanceDB table
    tables = mm.store.lancedb.list_tables()
    table_list = tables.tables if hasattr(tables, 'tables') else (tables if isinstance(tables, list) else [])
    print(f"[3] LanceDB tables: {table_list}")
    expect_table = "notes_attack_techniques"
    if expect_table in table_list:
        tbl = mm.store.lancedb.open_table(expect_table)
        rows = tbl.to_pandas()
        print(f"    Table '{expect_table}': {len(rows)} rows")
        # Check vector validity
        first_vec = rows.iloc[0]['vector'] if len(rows) > 0 else None
        if first_vec is not None:
            print(f"    First vector dims: {len(first_vec)}, non-zero: {any(v != 0 for v in first_vec)}")
    else:
        print(f"    MISSING TABLE: '{expect_table}' not in {table_list}")

    # Direct vector search on LanceDB
    query = "command and control communication over HTTP HTTPS"
    query_vec = get_embedding(query)
    print(f"[4] Query embedding dims: {len(query_vec)}")
    try:
        tbl = mm.store.lancedb.open_table(expect_table)
        search_results = tbl.search(query_vec).limit(5).to_list()
        print(f"    LanceDB search results: {len(search_results)}")
        for r in search_results:
            print(f"      id={r['id']}, distance={r.get('_distance', '?')}")
    except Exception as e:
        print(f"    LanceDB search FAILED: {e}")

    # Full recall pipeline
    results = mm.recall(query, k=10, domain="attack_techniques")
    print(f"[5] mm.recall() returned: {len(results)} notes")
    for r in results:
        print(f"      {r.id}: {r.content.raw[:80]}...")

if __name__ == "__main__":
    diagnose()
```

- [ ] Step 2: Run `python benchmarks/ctibench_ate_diagnosis.py` and record which layer breaks:
  - If `[2]` shows 0 lines: `write_note()` failed silently
  - If `[3]` shows missing table: `_index_in_lance()` failed (likely embedding dim mismatch at line 169 of `memory_store.py`)
  - If `[4]` shows 0 search results: LanceDB indexing succeeded but search fails (schema/type mismatch)
  - If `[5]` shows 0 but `[4]` works: the `recall()` pipeline (domain filter, blender, reranker) is dropping results

- [ ] Step 3: Check the embedding dimension mismatch path specifically. The `_index_in_lance()` at `src/zettelforge/memory_store.py:169` silently returns if `len(vec) != self.embedding_dim`. If the configured dimension differs from the actual model output, every note is silently dropped from LanceDB with only a log error.

```bash
# Check what dimension the config expects vs what the model produces
python -c "
from zettelforge.config import get_config
from zettelforge.vector_memory import get_embedding
cfg = get_config()
print(f'Config expects: {cfg.embedding.dimensions}')
vec = get_embedding('test')
print(f'Model produces: {len(vec)}')
print(f'Match: {cfg.embedding.dimensions == len(vec)}')
"
```

**Test:** `python benchmarks/ctibench_ate_diagnosis.py` should print clear pass/fail at each layer.

---

### Task 2: Fix Ingestion Pipeline (Based on Root Cause)

**Files:**
- Modify: `src/zettelforge/memory_store.py` (lines 160-248 -- `_index_in_lance`)
- Modify: `benchmarks/ctibench_benchmark.py` (lines 325-424 -- `run_ate_benchmark`)

Apply fixes based on diagnosis. The most likely root causes and their fixes:

- [ ] Step 1 (Most Likely -- Embedding Dim Mismatch): If `config.embedding.dimensions` does not match actual model output, the `_index_in_lance` method silently skips indexing for every note. Fix: make `_index_in_lance` auto-detect dimensions from the first valid vector rather than comparing against config.

```python
# In _index_in_lance, replace the dimension check (line 169) with:
vec = note.embedding.vector
if vec and len(vec) > 0:
    # Auto-detect: update embedding_dim on first real vector
    if self.embedding_dim != len(vec):
        _logger.warning(
            "embedding_dim_auto_corrected",
            configured=self.embedding_dim,
            actual=len(vec),
            note_id=note.id,
        )
        self.embedding_dim = len(vec)
```

- [ ] Step 2 (LanceDB Table Not Found): The `_retrieve_via_lancedb` in `vector_retriever.py:127` constructs the table name as `f"notes_{domain}"`. If the ingestion used a different domain string (case sensitivity, whitespace), the table won't be found. Add logging to `_retrieve_via_lancedb` when no table matches.

- [ ] Step 3 (Benchmark Config): The saved results show `"k": 10` in metadata but `run_ate_benchmark` defaults to `k=25`. The results.json was generated with the old `k=10` default from `run_benchmark()` at line 508 which overrode the function-level default. Fix `run_benchmark` to pass through the k parameter correctly:

```python
# benchmarks/ctibench_benchmark.py line 531
# Was: output["tasks"]["CTI-ATE"] = run_ate_benchmark(max_samples, k)
# The k=10 default at line 508 overrides the k=25 default at line 325
# Fix: change run_benchmark default to k=25
def run_benchmark(task: str = "both", max_samples: Optional[int] = None, k: int = 25) -> Dict:
```

**Test:** After fix, run `python benchmarks/ctibench_ate_diagnosis.py` -- all 5 checkpoints should pass.

---

### Task 3: Apply Remaining PRD Fixes (After Ingestion Is Verified)

**Files:**
- Modify: `benchmarks/ctibench_benchmark.py`

Only apply these AFTER Task 2 confirms notes are actually in the vector store.

- [ ] Step 1: Verify ATT&CK matrix coverage. The diagnosis task already identified that `mobile-attack.json` and `ics-attack.json` were missing. The current `ctibench_benchmark.py` lines 43-47 already reference all three files and `_download_attack_files()` downloads them. Verify all three exist:

```bash
ls -la benchmarks/enterprise-attack.json benchmarks/mobile-attack.json benchmarks/ics-attack.json
```

If any are missing, run the benchmark once to trigger download, or run:
```python
from benchmarks.ctibench_benchmark import _download_attack_files
_download_attack_files()
```

- [ ] Step 2: Confirm domain isolation is working. The benchmark ingests techniques into `domain="attack_techniques"` (line 133) and queries with `domain="attack_techniques"` (line 380). This is correct. The CTI descriptions go into `domain="cti"` (line 363). Verify LanceDB creates separate tables by checking the diagnostic output from Task 1.

- [ ] Step 3: Confirm query uses raw description (no wrapper). Line 378 already uses `query = sample["description"][:500]` -- this is correct per the diagnosis. No change needed.

**Test:** `python benchmarks/ctibench_benchmark.py --task ate --samples 20 --k 25`

---

### Task 4: Benchmark Validation Run

**Files:**
- Output: `benchmarks/ctibench_results.json` (overwritten by benchmark)

- [ ] Step 1: Run the full ATE benchmark with fixes applied:
```bash
cd /home/rolandpg/zettelforge
python benchmarks/ctibench_benchmark.py --task ate --samples 20 --k 25
```

- [ ] Step 2: Validate results against targets:
  - `retrieved_count > 0` for at least 15/20 samples (was 2/20)
  - `f1 >= 0.30` aggregate (was 0.00)
  - `p50_latency_ms < 5000` (was 68,635 -- the 67s latencies suggest the query was timing out or running the full recall pipeline with LLM enrichment)

- [ ] Step 3: If F1 < 0.30 but retrieval is now working (retrieved_count > 0), investigate whether the extract_technique_ids regex at line 278 is matching T-codes in the retrieved content. The technique notes are formatted as `"T1071 Application Layer Protocol: ..."` so the regex `r"T\d{4}(?:\.\d{3})?"` should match.

- [ ] Step 4: If latency is still >60s per query, profile whether the bottleneck is:
  - LLM calls during `recall()` (intent classifier, reranker)
  - Embedding generation (`get_embedding()`)
  - Full note iteration (should be fast with LanceDB but falls back to in-memory scan)

  The 67s latencies in the current results strongly suggest the `_enrichment_loop` or LLM-based intent classification is blocking. For benchmark runs, consider bypassing the full `recall()` pipeline and using `retriever.retrieve()` directly.

**Test:** `cat benchmarks/ctibench_results.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'F1: {d[\"tasks\"][\"CTI-ATE\"][\"f1\"]}')"` should print `F1: 0.3` or higher.
