#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

print("Simulating burnin script imports...")

# Exact same imports as burnin_ingest_real_data.py
from burnin_harness import BurnInHarness
from memory_manager import get_memory_manager

print("✓ BurnInHarness imported")
print("✓ memory_manager imported")

# Now try to use memory manager which uses entity_indexer
mm = get_memory_manager()
print(f"✓ MemoryManager initialized: {mm}")

# Check if entity_indexer is accessible
if hasattr(mm, 'indexer'):
    print(f"✓ MemoryManager has indexer: {type(mm.indexer).__name__}")
else:
    print("⚠ MemoryManager does not have 'indexer' attribute")

print("\n✅ Burnin-style imports working!")