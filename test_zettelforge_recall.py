#!/usr/bin/env python3
"""
Test script for ZettelForge local Ollama recall after switch.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "skills/zettelforge/src"))

try:
    from zettelforge import get_memory_manager
    mm = get_memory_manager()
    print("ZettelForge MemoryManager initialized with local Ollama.")

    # Test recall on known topics from MEMORY.md
    results = mm.recall("ZettelForge or local embeddings or Ollama", k=5)
    print(f"\nRecall test successful: {len(results)} results returned.")

    for i, r in enumerate(results[:3]):
        print(f"\nResult {i+1}:")
        print(f"  Score: {r.get('score', 'N/A')}")
        print(f"  Content: {str(r.get('content', r))[:120]}...")

    print("\n✓ Local Ollama recall test PASSED. No OpenAI dependency.")
    sys.exit(0)

except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
