#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

print("Testing import chain...")

# Step 1: Can we import entity_indexer?
try:
    from entity_indexer import EntityIndexer, Deduplicator
    print("✓ entity_indexer imported successfully")
except Exception as e:
    print(f"✗ entity_indexer import failed: {e}")
    sys.exit(1)

# Step 2: Can we create an indexer and deduplicator?
try:
    indexer = EntityIndexer()
    print("✓ EntityIndexer created")
    dedup = Deduplicator(indexer)
    print("✓ Deduplicator created")
except Exception as e:
    print(f"✗ Deduplicator creation failed: {e}")
    sys.exit(1)

# Step 3: Can we call find_similar?
try:
    # This should trigger the vector_retriever import
    results = dedup.find_similar("CVE-2024-1234 test content", k=1)
    print(f"✓ find_similar returned: {len(results)} results")
except Exception as e:
    print(f"✗ find_similar failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All imports working correctly!")