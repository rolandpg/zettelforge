#!/usr/bin/env python3
"""
Load Testing Script - Memory System Performance
Tests retrieval latency, evolution accuracy, storage growth
"""
import sys
import time
import random
from pathlib import Path

sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from memory_manager import get_memory_manager
from note_constructor import NoteConstructor


def test_retrieval_latency(mm, queries, iterations=10):
    """Test retrieval latency across multiple queries"""
    print("\n=== Retrieval Latency Test ===")
    
    results = {}
    for query in queries:
        times = []
        for _ in range(iterations):
            start = time.time()
            mm.recall(query, k=10)
            elapsed = (time.time() - start) * 1000  # ms
            times.append(elapsed)
        
        avg = sum(times) / len(times)
        p95 = sorted(times)[int(len(times) * 0.95)]
        results[query] = {'avg_ms': avg, 'p95_ms': p95}
        print(f"  '{query[:40]}...' avg: {avg:.1f}ms, p95: {p95:.1f}ms")
    
    return results


def test_note_construction_latency(constructor, content_templates, iterations=5):
    """Test note construction latency"""
    print("\n=== Note Construction Latency Test ===")
    
    times = []
    for i in range(iterations):
        content = random.choice(content_templates).format(i=i)
        start = time.time()
        constructor.enrich(content, domain="test")
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
    
    avg = sum(times) / len(times)
    print(f"  Average: {avg:.1f}ms")
    print(f"  Min: {min(times):.1f}ms, Max: {max(times):.1f}ms")
    
    return {'avg_ms': avg, 'min_ms': min(times), 'max_ms': max(times)}


def test_storage_growth():
    """Analyze storage growth patterns"""
    print("\n=== Storage Growth Analysis ===")
    
    notes_file = Path("/home/rolandpg/.openclaw/workspace/memory/notes.jsonl")
    if notes_file.exists():
        size_kb = notes_file.stat().st_size / 1024
        print(f"  notes.jsonl: {size_kb:.1f} KB")
    
    archive_dir = Path("/media/rolandpg/USB-HDD/archive")
    if archive_dir.exists():
        archives = list(archive_dir.glob("*.jsonl"))
        archive_size = sum(a.stat().st_size for a in archives) / 1024
        print(f"  Archives: {len(archives)} files, {archive_size:.1f} KB")
    
    vectordb_dir = Path("/home/rolandpg/.openclaw/workspace/vectordb")
    if vectordb_dir.exists():
        files = list(vectordb_dir.rglob("*"))
        vd_size = sum(f.stat().st_size for f in files if f.is_file()) / 1024
        print(f"  VectorDB: {vd_size:.1f} KB")
    
    return {
        'notes_kb': size_kb if notes_file.exists() else 0,
        'archives': len(archives) if archive_dir.exists() else 0
    }


def test_evolution_accuracy():
    """Test evolution decision accuracy with known contradictions"""
    print("\n=== Evolution Accuracy Test ===")
    
    from memory_evolver import EvolutionDecider
    from note_schema import MemoryNote, Content, Semantic, Embedding, Metadata
    
    evolver = EvolutionDecider()
    
    # Test cases: (original_context, new_info, should_evolve)
    test_cases = [
        (
            "Threat actor uses TTP1 for initial access",
            "Updated intel shows actor now uses TTP2, not TTP1",
            True
        ),
        (
            "Product X has vulnerability Y",
            "Vendor patched vulnerability Y in latest update",
            True
        ),
        (
            "Market research shows 10% growth",
            "Weather forecast for tomorrow",
            False
        ),
    ]
    
    correct = 0
    for original, new_info, expected in test_cases:
        # Create mock notes
        orig_note = MemoryNote(
            id="test_orig",
            version=1,
            created_at="2026-03-20T00:00:00",
            updated_at="2026-03-20T00:00:00",
            content=Content(raw=original, source_type="test", source_ref="test"),
            semantic=Semantic(context=original[:100], keywords=[], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[], dimensions=768),
            metadata=Metadata()
        )
        
        new_note = MemoryNote(
            id="test_new",
            version=1,
            created_at="2026-03-20T01:00:00",
            updated_at="2026-03-20T01:00:00",
            content=Content(raw=new_info, source_type="test", source_ref="test"),
            semantic=Semantic(context=new_info[:100], keywords=[], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[], dimensions=768),
            metadata=Metadata()
        )
        
        decision, reason = evolver.assess(new_note, orig_note)
        evolved = decision != 'NO_CHANGE'
        
        if evolved == expected:
            correct += 1
            status = "✓"
        else:
            status = "✗"
        
        print(f"  {status} Original vs New: {decision}")
    
    accuracy = (correct / len(test_cases)) * 100
    print(f"\n  Accuracy: {accuracy:.0f}% ({correct}/{len(test_cases)})")
    
    return {'accuracy': accuracy}


def main():
    print("=" * 60)
    print("Roland Fleet Memory System Load Test")
    print("=" * 60)
    
    mm = get_memory_manager()
    constructor = NoteConstructor()
    
    # Get current stats
    print("\nCurrent Stats:")
    stats = mm.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # Test queries
    test_queries = [
        "threat actor targeting network equipment",
        "Volt Typhoon espionage",
        "critical vulnerability CVE",
        "MSSP market consolidation",
        "CISA advisory recommendations"
    ]
    
    # Run tests
    retrieval_results = test_retrieval_latency(mm, test_queries, iterations=10)
    construction_results = test_note_construction_latency(
        constructor,
        ["Test content {i}", "Another test {i}"],
        iterations=5
    )
    storage_results = test_storage_growth()
    evolution_results = test_evolution_accuracy()
    
    # Summary
    print("\n" + "=" * 60)
    print("Load Test Summary")
    print("=" * 60)
    print(f"Total notes: {stats['total_notes']}")
    print(f"Storage: {storage_results.get('notes_kb', 0):.1f} KB")
    print(f"Evolution accuracy: {evolution_results.get('accuracy', 0):.0f}%")
    print("\nRetrieval latency (avg):")
    for q, r in retrieval_results.items():
        print(f"  {q[:40]}: {r['avg_ms']:.1f}ms")
    print("\n=== Load Test Complete ===")


if __name__ == "__main__":
    main()
