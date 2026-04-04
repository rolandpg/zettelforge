#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')
from memory_store import MemoryStore
store = MemoryStore()
print(f"Total notes in store: {store.count_notes()}")