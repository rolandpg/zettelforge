#!/usr/bin/env python3
"""Quick test for vector_retriever import fix"""
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

print("Testing import chain...")

# Test 1: Can we import memory.vector_retriever?
try:
    from memory.vector_retriever import VectorRetriever
    print("✓ memory.vector_retriever imported successfully")
except Exception as e:
    print(f"✗ memory.vector_retriever import failed: {e}")
    sys.exit(1)

# Test 2: Can we import synthesis_retriever which uses vector_retriever?
try:
    from memory.synthesis_retriever import SynthesisRetriever
    print("✓ memory.synthesis_retriever imported successfully")
except Exception as e:
    print(f"✗ memory.synthesis_retriever import failed: {e}")
    sys.exit(1)

# Test 3: Can we import memory_manager which uses both?
try:
    from memory_manager import get_memory_manager
    print("✓ memory_manager imported successfully")
except Exception as e:
    print(f"✗ memory_manager import failed: {e}")
    sys.exit(1)

# Test 4: Can we create memory manager and run dedup?
try:
    mm = get_memory_manager()
    print(f"✓ MemoryManager created ({len(list(mm.store.iterate_notes()))} notes)")
    
    # Test deduplicator which uses vector_retriever
    indexer = mm.indexer
    dedup = mm.dedup
    print("✓ Deduplicator accessible")
    
except Exception as e:
    print(f"✗ Memory manager setup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All imports working! Burn-in test should succeed now.")
