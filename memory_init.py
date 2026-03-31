#!/usr/bin/env python3
"""
memory_init.py — Bootstraps all memory modules for Patton agent

Usage:
    from memory_init import init_all
    ems, nm, sm = init_all()  # returns tuple of (EnhancedMemoryStore, NudgeManager, SkillManager)
    
    # Or separately:
    from memory_init import enhanced_memory, nudge_manager, skill_manager
    store = enhanced_memory()
    ...
"""

import sys
from pathlib import Path
from typing import Tuple

# Ensure memory/ is on path
_MEMORY_DIR = Path(__file__).parent / "memory"
if str(_MEMORY_DIR) not in sys.path:
    sys.path.insert(0, str(_MEMORY_DIR))


def enhanced_memory():
    """Initialize EnhancedMemoryStore with correct workspace path."""
    from enhanced_memory import EnhancedMemoryStore
    # MEMORY.md lives at workspace root, not in memory/ subdirectory
    store = EnhancedMemoryStore(memory_dir=Path(__file__).parent)
    store.load()
    return store


def nudge_manager():
    """Initialize NudgeManager."""
    from nudge_manager import NudgeManager
    return NudgeManager()


def skill_manager():
    """Initialize SkillManager."""
    from skill_manager import SkillManager
    return SkillManager()


def memory_manager():
    """Initialize A-MEM MemoryManager with cross-session vector recall."""
    from memory.memory_manager import get_memory_manager
    return get_memory_manager()


def init_all() -> Tuple:
    """
    Initialize all memory modules.
    Returns: (EnhancedMemoryStore, NudgeManager, SkillManager, MemoryManager)
    """
    store = enhanced_memory()
    nm = nudge_manager()
    sm = skill_manager()
    mm = memory_manager()
    return store, nm, sm, mm


if __name__ == "__main__":
    print("=== Memory Module Bootstrap ===\n")
    
    # Init all
    store, nm, sm, mm = init_all()
    
    # EMS stats
    stats = store.get_stats()
    print("EnhancedMemoryStore:")
    for key, vals in stats.items():
        print(f"  {key}: {vals['entries']} entries, {vals['used_pct']}% used ({vals['total_chars']}/{vals['limit']} chars)")
    
    # NudgeManager stats
    n_stats = nm.get_stats()
    print(f"\nNudgeManager:")
    print(f"  Memory nudge interval: every {n_stats['memory_nudge_threshold']} turns")
    print(f"  Skill nudge interval: every {n_stats['skill_nudge_threshold']} tasks")
    print(f"  Context warning at: {int(n_stats['context_warning_70']*100)}%")
    print(f"  Context critical at: {int(n_stats['context_critical_90']*100)}%")
    
    # SkillManager
    skills = sm.list_skills()
    print(f"\nSkillManager: {len(skills)} skills loaded")
    for s in skills:
        print(f"  - {s.identifier}: {s.description[:60]}")

    # MemoryManager
    mm_stats = mm.get_stats()
    print(f"\nMemoryManager:")
    print(f"  Total notes: {mm_stats.get('notes_created', mm.store.count_notes())}")
    # Test cross-session recall
    recall_test = mm.recall('threat actors', k=3)
    print(f"  Cross-session recall (threat actors): {len(recall_test)} results")
