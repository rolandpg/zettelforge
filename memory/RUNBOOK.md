# Roland Fleet Memory System - Operational Runbook

## Quick Start

```bash
# Check memory system status
cd /home/rolandpg/.openclaw/workspace/memory
python3 memory_manager.py stats

# Manually trigger maintenance
python3 daily_maintenance.py
python3 weekly_maintenance.py

# Enable systemd timers (run once)
sudo cp openclaw-memory-*.service /etc/systemd/system/
sudo cp openclaw-memory-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-memory-daily.timer
sudo systemctl enable --now openclaw-memory-weekly.timer

# Check timer status
systemctl list-timers | grep openclaw-memory
```

---

## Memory Manager CLI

```bash
# View stats
python3 memory_manager.py stats

# Create memory
python3 memory_manager.py remember "Content to remember"

# Recall memories
python3 memory_manager.py recall "query string"

# Get formatted context
python3 memory_manager.py context "query string"

# Manual snapshot
python3 memory_manager.py snapshot
```

---

## Memory System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Primary Agent (Patton)                                      │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│ │ Remember    │ │ Recall      │ │ Evolve      │            │
│ │ Construct   │ │ Retrieve    │ │ Link Gen    │            │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘            │
│        │               │               │                    │
│        └───────────────┼───────────────┘                    │
│                        ↓                                    │
│              ┌─────────────────┐                           │
│              │ Memory Manager  │                           │
│              └────────┬────────┘                           │
│                       ↓                                    │
│        ┌─────────────┴─────────────┐                      │
│        ↓                           ↓                      │
│ ┌──────────────┐           ┌──────────────┐              │
│ │ JSONL Store  │           │  LanceDB     │              │
│ │ (notes.jsonl)│           │  (vectors)  │              │
│ └──────────────┘           └──────────────┘              │
│        │                                                   │
│        └─────────────────────┬─────────────────────────────┘
│                              ↓
│                    ┌──────────────────┐
│                    │ COLD STORAGE     │
│                    │ /media/rolandpg/ │
│                    │ USB-HDD/         │
│                    │ ├── archive/     │
│                    │ ├── snapshots/   │
│                    │ ├── backups/     │
│                    │ └── daily/       │
│                    └──────────────────┘
└─────────────────────────────────────────────────────────────┘
```

---

## File Locations

| File | Location |
|------|----------|
| Active notes | `/home/rolandpg/.openclaw/workspace/memory/notes.jsonl` |
| Vector DB | `/home/rolandpg/.openclaw/workspace/vectordb/` |
| Archive (evolved notes) | `/media/rolandpg/USB-HDD/archive/` |
| Snapshots | `/media/rolandpg/USB-HDD/snapshots/` |
| Daily logs | `/media/rolandpg/USB-HDD/daily/` |
| Weekly backups | `/media/rolandpg/USB-HDD/backups/weekly/` |
| Maintenance logs | `/media/rolandpg/USB-HDD/weekly/` |

---

## Python API

```python
from memory import get_memory_manager

mm = get_memory_manager()

# Create memory with auto-linking and evolution
note = mm.remember(
    content="Important information to remember",
    source_type="conversation",  # conversation|task_output|ingestion|observation
    source_ref="session_123",
    domain="security_ops",       # security_ops|project|personal|research
    auto_evolve=True
)

# Retrieve relevant memories
results = mm.recall(
    query="search terms",
    domain="security_ops",       # Optional filter
    k=10,                         # Number of results
    include_links=True            # Expand via linked notes
)

# Get formatted context for agent prompt
context = mm.get_context(
    query="task description",
    domain="security_ops",
    k=10,
    token_budget=4000             # Characters (not tokens)
)

# Get scoped context for subagent
sub_context = mm.get_subagent_context(
    task="task description",
    domain="security_ops",
    k=5,
    token_budget=2000
)

# Ingest subagent output
note = mm.ingest_subagent_output(
    task_id="task_123",
    output="subagent results",
    observations="what subagent learned",
    domain="security_ops"
)

# Get system stats
stats = mm.get_stats()
print(stats)

# Manual maintenance
mm.daily_maintenance()
mm.weekly_maintenance()
mm.snapshot()
```

---

## Note Schema

```json
{
  "id": "note_20260320_143022_a7f3",
  "version": 1,
  "created_at": "2026-03-20T14:30:22-05:00",
  "updated_at": "2026-03-20T14:30:22-05:00",
  "content": {
    "raw": "Full text content",
    "source_type": "conversation",
    "source_ref": "session_123"
  },
  "semantic": {
    "context": "One-sentence summary",
    "keywords": ["key1", "key2"],
    "tags": ["security_ops", "cti"],
    "entities": ["CVE-2024-1234"]
  },
  "embedding": {
    "model": "nomic-embed-text-v2-moe",
    "vector": [0.1, -0.2, ...],
    "dimensions": 768
  },
  "links": {
    "related": ["note_id_1", "note_id_2"],
    "causal_chain": []
  },
  "metadata": {
    "access_count": 5,
    "last_accessed": "2026-03-20T15:00:00-05:00",
    "evolution_count": 0,
    "confidence": 1.0,
    "domain": "security_ops"
  }
}
```

---

## Troubleshooting

### Memory system not responding

```bash
# Check if notes.jsonl exists
ls -la /home/rolandpg/.openclaw/workspace/memory/notes.jsonl

# Check Python module imports
cd /home/rolandpg/.openclaw/workspace/memory
python3 -c "from memory import get_memory_manager; mm = get_memory_manager(); print(mm.get_stats())"

# Check cold storage
ls -la /media/rolandpg/USB-HDD/
```

### High retrieval latency

- Check if vector DB is on SSD (not HDD)
- Reduce k value for retrieval
- Check LanceDB table status
- Consider reindexing

### Evolution not triggering

- Check evolution_count in notes
- Verify linked notes exist
- Check memory_evolver logs

### Disk space issues

```bash
# Check storage usage
df -h /home/rolandpg/.openclaw/workspace/
df -h /media/rolandpg/USB-HDD/

# Check archive size
du -sh /media/rolandpg/USB-HDD/archive/

# Manual cleanup
python3 weekly_maintenance.py
```

### Restore from backup

```bash
# Find latest backup
ls -la /media/rolandpg/USB-HDD/backups/weekly/

# Copy backup to notes location
cp /media/rolandpg/USB-HDD/backups/weekly/memory_full_YYYYMMDD_HHMMSS.jsonl \
   /home/rolandpg/.openclaw/workspace/memory/notes.jsonl
```

---

## systemd Timer Management

```bash
# View timer status
systemctl status openclaw-memory-daily.timer
systemctl status openclaw-memory-weekly.timer

# View next run time
systemctl list-timers | grep openclaw-memory

# Manual trigger
sudo systemctl start openclaw-memory-daily.service
sudo systemctl start openclaw-memory-weekly.service

# Disable timers (if needed)
sudo systemctl disable openclaw-memory-daily.timer
sudo systemctl disable openclaw-memory-weekly.timer

# View logs
journalctl -u openclaw-memory-daily.service
journalctl -u openclaw-memory-weekly.service
```

---

## Maintenance Windows

### Daily (automatic - 6:00 AM)
- Snapshot memory state to cold storage
- Log stats and low-confidence notes
- Apply confidence decay to stale notes

### Weekly (automatic - Monday 6:00 AM)
- Full backup to cold storage
- Check for orphaned links
- Archive retention check

### Monthly (manual)
- Review flagged notes (confidence < 0.5)
- Purge archives older than 90 days
- Performance tuning based on load test results

---

## Performance Benchmarks

From load testing (2026-03-20):

| Metric | Value |
|--------|-------|
| Retrieval latency (avg) | 100-270ms |
| Retrieval latency (p95) | 130-1800ms |
| Note construction | 2700ms (1.2-4.8s range) |
| Evolution accuracy | 100% (3/3 test cases) |
| Storage per note | ~17 KB |

---

## Emergency Procedures

### Complete memory loss
1. Stop all memory operations
2. Check backups: `ls /media/rolandpg/USB-HDD/backups/weekly/`
3. Restore from latest backup
4. Verify with `python3 memory_manager.py stats`

### Corrupted notes.jsonl
1. Check if LanceDB is intact
2. Use archive to reconstruct
3. Run reindex from archive

### Cold storage unavailable
- Memory system continues working with hot tier only
- Manual operations may fail
- Check mount: `mount | grep USB-HDD`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-03-20 | Removed LUKS encryption (homelab) |
| 1.0 | 2026-03-20 | Initial architecture |
