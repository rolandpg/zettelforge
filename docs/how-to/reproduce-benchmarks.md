---
title: "Reproduce the Published Benchmarks"
description: "Run the CTI Retrieval, LOCOMO, MemPalace, RAGAS, and CTIBench benchmarks locally and compare your numbers against the published report."
diataxis_type: "how-to"
audience: "Researcher / Benchmark reviewer"
tags: [benchmarks, reproducibility, cti, locomo, ragas, ctibench]
last_updated: "2026-04-16"
version: "2.2.0"
---

# Reproduce the Published Benchmarks

Every benchmark referenced in [BENCHMARK_REPORT.md](https://github.com/rolandpg/zettelforge/blob/master/benchmarks/BENCHMARK_REPORT.md)
ships as an adapter script in `benchmarks/`. This guide shows how to
run each one against a fresh install and compare your results.

## Prerequisites

- A clone of the repo (the benchmarks live under `benchmarks/`, not in
  the installed package).
- `pip install -e .[dev]` from the repo root.
- Optional: Ollama running locally if you want to reproduce the v2.1.1
  LOCOMO 22 % result with a cloud judge.

## Shared setup

```bash
git clone https://github.com/rolandpg/zettelforge
cd zettelforge
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

Each benchmark writes a JSON results file alongside its script so your
output can be diffed against the reference files already in the repo.

## 1. CTI Retrieval (domain benchmark)

```bash
python benchmarks/cti_retrieval_benchmark.py
# writes benchmarks/cti_retrieval_results.json
```

Published reference: **75.0 %** accuracy, p50 620 ms over 8 reports / 20 queries.

## 2. LOCOMO (ACL 2024)

```bash
# Baseline with the local llama-cpp judge
python benchmarks/locomo_benchmark.py

# v2.1.1 cloud-judge run (requires Ollama + a suitable model pulled)
LLM_JUDGE=ollama python benchmarks/locomo_benchmark.py
```

Published references: **18.0 %** with the local judge, **22.0 %** with
the Ollama cloud judge. Both runs emit `benchmarks/locomo_results.json`.

## 3. MemPalace comparison

```bash
python benchmarks/mempalace_benchmark.py
# writes benchmarks/mempalace_results.json
```

Published reference: MemPalace 26.0 % vs ZettelForge 18.0 % on LOCOMO.

## 4. RAGAS retrieval quality

```bash
python benchmarks/ragas_benchmark.py
# writes benchmarks/ragas_results.json
```

Published reference: **78.1 %** keyword presence.

## 5. CTIBench ATE (NeurIPS 2024)

```bash
python benchmarks/ctibench_benchmark.py
# writes benchmarks/ctibench_results.json
```

Published reference: **F1 = 0.146** (v2.2.0, after fixing the ingestion
pipeline and dropping ICS matrix noise). The v2.0.0 result was
**F1 = 0.000** — see [BENCHMARK_REPORT §5](../../benchmarks/BENCHMARK_REPORT.md)
for the methodology change.

## 6. MemoryAgentBench (ICLR 2026, optional)

```bash
python benchmarks/memoryagentbench.py
# writes benchmarks/memoryagentbench_results.json
```

Requires a cloud-grade judge (we used `nemotron-3-super:cloud` via
Ollama). Expect a day-scale run on larger splits.

## Interpreting differences

If your numbers differ from the published ones, check:

- **LLM backend** — local llama-cpp runs will underperform cloud
  judges on LOCOMO by a wide margin (see
  [BENCHMARK_REPORT §6](../../benchmarks/BENCHMARK_REPORT.md)).
- **Embedding dimensions** — all published runs use 768-dim
  `nomic-embed-text-v1.5-Q`. Switching to another embedding changes
  the vector store and invalidates results until you
  `python scripts/rebuild_index.py`.
- **Backend** — SQLite vs a lingering JSONL data directory changes
  entity-index behaviour. Ensure `ZETTELFORGE_BACKEND=sqlite` (the
  v2.2.0 default).
- **Governance** — set `governance.enabled: false` in `config.yaml`
  for benchmark runs; otherwise some permissive inputs will raise
  `GovernanceViolationError`.

## Related

- [BENCHMARK_REPORT.md](https://github.com/rolandpg/zettelforge/blob/master/benchmarks/BENCHMARK_REPORT.md) — full methodology and published numbers
- [LOCOMO_BENCHMARK_COMPARISON.md](https://github.com/rolandpg/zettelforge/blob/master/benchmarks/LOCOMO_BENCHMARK_COMPARISON.md) — head-to-head vs MemPalace / Mem0 / LangMem
