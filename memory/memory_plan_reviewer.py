#!/usr/bin/env python3
"""
Memory Plan Reviewer — iterates on the memory system improvement plan.
Reads MEMORY_PLAN.md, checks current state, logs iteration, suggests next step.

Run via cron: 0 6 * * 1  (every Monday at 6 AM CDT)
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
PLAN_PATH = MEMORY_DIR / "MEMORY_PLAN.md"
ENTITY_INDEX = MEMORY_DIR / "entity_index.json"
DEDUP_LOG = MEMORY_DIR / "dedup_log.jsonl"
STATS_LOG = MEMORY_DIR / "plan_iterations.jsonl"

# Add workspace to path
sys.path.insert(0, str(MEMORY_DIR))


def get_entity_stats():
    try:
        from entity_indexer import EntityIndexer
        idx = EntityIndexer()
        idx.load()
        return idx.stats()
    except Exception as e:
        return {"error": str(e)}


def get_memory_stats():
    try:
        from memory_manager import get_memory_manager
        mm = get_memory_manager()
        stats = mm.get_stats()
        return stats
    except Exception as e:
        return {"error": str(e)}


def count_dedup_events():
    """Count dedup events in log"""
    if not DEDUP_LOG.exists():
        return {"total": 0, "skipped": 0, "similar": 0}
    skipped = 0
    similar = 0
    with open(DEDUP_LOG) as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                if e.get("action") == "skipped":
                    skipped += 1
                elif "similar" in e.get("reason", ""):
                    similar += 1
    total = skipped + similar
    return {"total": total, "skipped": skipped, "similar": similar}


def current_phase() -> str:
    """Determine current active phase from plan"""
    plan = PLAN_PATH.read_text() if PLAN_PATH.exists() else ""
    if "Phase 1" in plan and "✅" in plan:
        if "Phase 2" in plan and "🔧" not in plan:
            return "Phase 2"
        return "Phase 1"
    if "Phase 2" in plan:
        return "Phase 2"
    return "Planning"


def next_action(phase: str, entity_count: int, total_notes: int) -> str:
    """Recommend next action based on current state"""
    if entity_count < 10:
        return "Build entity index from scratch (Phase 1)"

    if phase == "Phase 1":
        # Check if Phase 1 is complete (entity index built, dedup wired)
        if entity_count > 20:
            return "Phase 1 complete → move to Phase 2 (link generator integration)"
        return "Continue Phase 1: add more entity patterns, tune deduplication threshold"

    if phase == "Phase 2":
        return "Phase 2: wire link_generator into save flow, ensure evolution writes back to JSONL"

    return "Review MEMORY_PLAN.md for next priority"


def log_iteration(
    phase: str,
    entity_stats: dict,
    memory_stats: dict,
    dedup_stats: dict,
    next_step: str
) -> dict:
    """Log iteration to plan_iterations.jsonl"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "phase": phase,
        "entities_total": entity_stats.get("total_entities", 0),
        "entity_breakdown": entity_stats.get("by_type", {}),
        "total_notes": memory_stats.get("total_notes", 0),
        "notes_created": memory_stats.get("notes_created", 0),
        "duplicates_skipped": dedup_stats.get("skipped", 0),
        "similar_warned": dedup_stats.get("similar", 0),
        "next_action": next_step
    }

    with open(STATS_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')

    return entry


def print_report(entry: dict):
    print("=== Memory Plan Review ===")
    print(f"Phase: {entry['phase']}")
    print(f"Entities indexed: {entry['entities_total']} ({entry['entity_breakdown']})")
    print(f"Total notes: {entry['total_notes']}")
    print(f"Duplicates skipped: {entry['duplicates_skipped']}")
    print(f"Similar warned: {entry['similar_warned']}")
    print(f"Next action: {entry['next_action']}")


if __name__ == "__main__":
    entity_stats = get_entity_stats()
    memory_stats = get_memory_stats()
    dedup_stats = count_dedup_events()
    phase = current_phase()
    next_step = next_action(phase, entity_stats.get("total_entities", 0), memory_stats.get("total_notes", 0))

    entry = log_iteration(phase, entity_stats, memory_stats, dedup_stats, next_step)
    print_report(entry)
