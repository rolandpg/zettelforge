# A-MEM Development Guide

**Version:** 1.3  
**Date:** 2026-04-02  
**Project:** A-MEM (Agentic Memory)

---

## 1. Development Environment Setup

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.12+ | Runtime environment |
| pip | latest | Package management |
| Ollama | latest | Local LLM server |
| Local GPU (optional) | CUDA-capable | Accelerated embeddings |

### Quick Start

```bash
# 1. Clone repository
cd /home/rolandpg/.openclaw/workspace/memory

# 2. Install Python dependencies
pip install pydantic ollama lancedb pyarrow requests

# 3. Start Ollama (if not running)
ollama serve

# 4. Initialize memory system
python3 -c "from memory_manager import get_memory_manager; mm = get_memory_manager(); print(mm.get_stats())"
```

### Directory Structure

```
memory/
├── memory/                      # Core module
│   ├── __init__.py             # Package init
│   ├── note_schema.py          # Pydantic data models
│   ├── memory_store.py         # JSONL storage + LanceDB
│   ├── entity_indexer.py       # Entity extraction/indexing
│   ├── link_generator.py       # LLM-based linking
│   ├── memory_evolver.py       # Evolution & archival
│   ├── alias_resolver.py       # Canonical name resolution
│   ├── alias_manager.py        # Auto-update tracking
│   ├── reasoning_logger.py     # Decision audit trail
│   ├── note_constructor.py     # LLM enrichment
│   ├── vector_retriever.py     # Semantic search
│   ├── vector_memory.py        # Cross-session embeddings
│   └── alias_maps/             # Entity alias mappings
│       ├── actors.json
│       ├── tools.json
│       └── campaigns.json
├── embedding_utils.py          # Embedding generation
├── memory_init.py             # Global initialization
├── test_memory_system.py      # Main test suite
├── test_phase_3_5.py          # Alias resolution tests
├── test_phase_4_5.py          # Tiering tests
├── test_phase_5_5.py          # Reasoning tests
├── notes.jsonl                # Primary storage
├── entity_index.json          # Entity index
├── reasoning_log.jsonl        # Decision audit
├── dedup_log.jsonl            # Deduplication events
├── alias_observations.json    # Auto-update tracking
├── plan_iterations.jsonl      # PRD history
├── daily_maintenance.py       # Daily maintenance
├── weekly_maintenance.py      # Weekly maintenance
├── *.sh                       # Maintenance wrappers
└── docs/                      # Documentation
    ├── PRD.md
    ├── ARCHITECTURE.md
    ├── DATAFLOW.md
    ├── COMPONENTS.md
    ├── TECH_STACK.md
    ├── SBOM.md
    ├── API_REFERENCE.md
    ├── SECURITY.md
    ├── DEVELOPMENT.md
    └── LLM_CONTEXT.md
```

---

## 2. Code Style Guidelines

### Python Style

| Rule | Style | Example |
|------|-------|---------|
| Indentation | 4 spaces | `    def function():` |
| Line length | 100 characters | Max 100 chars per line |
| Naming | snake_case | `def my_function():` |
| Classes | PascalCase | `class MyClass:` |
| Constants | UPPER_CASE | `MAX_SIZE = 100` |
| Type hints | Required | `def func(x: int) -> str:` |

### Documentation Style

| Element | Format | Example |
|---------|--------|---------|
| Docstrings | Google style | See `note_schema.py` |
| Comments | Inline, minimal | `# Check duplicate` |
| Markdown | GitHub flavored | Used in docs/ |

### LLM Prompt Style

| Pattern | Purpose | Example |
|---------|---------|---------|
| SYSTEM_PROMPT | System-level instructions | In LinkGenerator, EvolutionDecider |
| User prompts | Direct task description | "Generate links between notes" |
| JSON format | Structured output | `format='json'` |

---

## 3. Core Development Workflows

### Adding a New Note

```python
from memory_manager import get_memory_manager

mm = get_memory_manager()

# Basic note
note, status = mm.remember(
    content="Threat actor X targeted Y using Z technique",
    source_type="conversation",
    source_ref="agent:task_123",
    domain="security_ops"
)

print(f"Created: {note.id} with status: {status}")
```

### Querying Memories

```python
# Semantic search
results = mm.recall("threat actors targeting DIB", k=10)

# Entity lookup
cve_notes = mm.recall_cve("CVE-2024-3094", k=5)
actor_notes = mm.recall_actor("volt typhoon", k=5)

# Context for LLM prompt
context = mm.get_context(
    query="What do we know about recent attacks?",
    domain="security_ops",
    k=10,
    token_budget=4000
)
```

### Working with Entity Index

```python
# Build/refresh entity index
results = mm.rebuild_entity_index()
print(f"Indexed {results['entities']} entity mappings")

# Get entity statistics
stats = mm.get_entity_stats()
print(f"Actors: {stats['by_type']['actor']}")
```

---

## 4. Testing

### Test Suite Structure

| Test File | Phases | Tests | Purpose |
|-----------|--------|-------|---------|
| `test_memory_system.py` | 1-5.5 | 33 | Core functionality |
| `test_phase_3_5.py` | 3.5 | 7 | Alias resolution |
| `test_phase_4_5.py` | 4.5 | 10 | Epistemic tiering |
| `test_phase_5_5.py` | 5.5 | 9 | Reasoning memory |
| `test_phase_6.py` | 6 | 36 | Knowledge graph & IEP |
| `test_phase_7.py` | 7 | 21 | Synthesis layer |

### Running Tests

```bash
# Run all tests
python3 test_memory_system.py

# Run specific phase
python3 test_memory_system.py --phase 1

# Verbose output
python3 test_memory_system.py --verbose

# Run Phase 6 tests
python3 test_phase_6.py

# Run Phase 7 tests
python3 test_phase_7.py
```

### Writing New Tests

```python
# Add to test_memory_system.py
def test_phase_6_1():
    """Test: [Requirement description]"""
    # Setup
    mm = get_memory_manager()
    
    # Execute
    note, status = mm.remember("Test content", "test")
    
    # Assert
    assert status == "created"
    assert note is not None
    assert "Test content" in note.content.raw
    
    return TestResult(phase=6, requirement="Test description", passed=True)
```

---

## 5. Debugging

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Ollama connection failed | Ollama not running | `ollama serve` |
| LanceDB initialization failed | Path not writable | Create directory, check permissions |
| Alias collision error | Duplicate aliases | Update alias_maps/*.json |
| Embedding generation slow | Using Ollama instead of Llama server | Set up GPU server on port 8080 |
| Entity index stale | Not rebuilt after schema changes | Run `mm.rebuild_entity_index()` |

### Logging & Tracing

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check memory stats
mm = get_memory_manager()
print(json.dumps(mm.get_stats(), indent=2))

# View reasoning log
from reasoning_logger import get_reasoning_logger
logger = get_reasoning_logger()
recent = logger.get_recent(limit=10)
```

### Development Mode

```bash
# Run in development mode (no daemon)
python3 -c "
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')
from memory_manager import get_memory_manager
mm = get_memory_manager()
print('Memory system ready')
print(f'Stats: {mm.get_stats()}')
"
```

---

## 6. Maintenance Operations

### Daily Maintenance

**Schedule:** 06:00 CDT daily

**Runs:**
1. Rebuild entity index
2. Export memory snapshot
3. Flag low-confidence notes
4. Export maintenance log

```bash
# Manual execution
./run_daily.sh
```

### Weekly Maintenance

**Schedule:** Friday 23:00 CDT

**Runs:**
1. Weekly maintenance report
2. Full backup to cold storage
3. Archive retention check
4. VectorDB health check

```bash
# Manual execution
./run_weekly.sh
```

### Archive Management

```python
from pathlib import Path

archive_dir = Path("/media/rolandpg/USB-HDD/archive")
archives = list(archive_dir.glob("*.jsonl"))
print(f"Archived notes: {len(archives)}")

# Prune old archives (>90 days)
from datetime import datetime, timedelta
cutoff = datetime.now() - timedelta(days=90)
old = [a for a in archives if datetime.fromtimestamp(a.stat().st_mtime) < cutoff]
print(f"Old archives to purge: {len(old)}")
```

---

## 7. Configuration Options

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLAMA_SERVER_URL` | `http://localhost:8080/embedding` | Embedding server endpoint |

### Path Configuration

| Path | Purpose | Override via |
|------|---------|--------------|
| notes.jsonl | Main storage | `MemoryManager(jsonl_path=...)` |
| entity_index.json | Entity index | `EntityIndexer(index_path=...)` |
| LanceDB | Vector store | `MemoryStore(lance_path=...)` |
| Archive | Cold storage | `MemoryManager(cold_path=...)` |
| Reasoning log | Audit trail | `ReasoningLogger(log_path=...)` |
| Alias maps | Entity resolution | `AliasResolver(alias_map_dir=...)` |

---

## 8. Performance Optimization

### Current Benchmarks

| Operation | Typical Time | Notes |
|-----------|--------------|-------|
| Embedding (GPU) | ~5ms | Llama server |
| Embedding (CPU) | ~73ms | Ollama |
| Link generation | ~2s | LLM analysis |
| Evolution cycle | ~3s | Multiple LLM calls |
| Entity extraction | ~10ms | Regex matching |

### Optimization Tips

1. **Batch Embeddings**
   ```python
   # Better: Batch embed
   embs = generator.embed_batch(texts)
   
   # Avoid: Loop
   for text in texts:
       embs.append(generator.embed(text))
   ```

2. **Limit Evolution Candidates**
   - Default: 20 candidates (configurable in `MemoryEvolver`)
   - Adjust based on note volume

3. **Index Rebuild Strategy**
   - Rebuild after bulk imports
   - Not needed for single-note adds

---

## 9. Version Control

### Git Workflow

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases |
| `development` | Active development |
| `feature/*` | New features |

### Release Process

1. Update version in docs/*.md files
2. Run test suite: `python3 test_memory_system.py --verbose`
3. Tag release: `git tag -a v1.3 -m "Release v1.3"`
4. Push: `git push origin main --tags`

---

## 10. Contributing

### Code Review Checklist

- [ ] Tests pass (`python3 test_memory_system.py`)
- [ ] No hardcoded secrets
- [ ] Type hints present
- [ ] Documentation updated
- [ ] LLM prompts are clear and tested

### Pull Request Process

1. Fork repository
2. Create feature branch (`git checkout -b feature/xyz`)
3. Implement changes with tests
4. Run test suite
5. Submit PR with description

---

## 11. Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Single-machine only | No distributed deployment | Use local hardware |
| No encryption at rest | Sensitive data risk | Use filesystem encryption |
| No authentication | Local access only | Use OS permissions |
| No hot backup | Downtime during backup | Run during maintenance |
| 180-day retention | Long-term data loss | Manual archive export |

---

*End of Development Guide*
