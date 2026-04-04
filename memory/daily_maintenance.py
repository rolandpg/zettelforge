#!/usr/bin/env python3
"""
Daily Maintenance Script - Roland Fleet Memory System
Runs daily tasks: snapshot, stats, confidence decay, prune
"""
import json
import sys
from pathlib import Path

# Add memory module to path
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from memory_manager import get_memory_manager


def main():
    print("=== Daily Memory Maintenance ===")
    print(f"Timestamp: {__import__('datetime').datetime.now().isoformat()}")
    print()
    
    mm = get_memory_manager()
    
    # 1. Run daily maintenance
    print("1. Running daily maintenance...")
    results = mm.daily_maintenance()
    print(f"   Snapshot created: {results['snapshot_created']}")
    print(f"   Total notes: {results['notes_count']}")
    print(f"   Low confidence notes: {len(results['low_confidence_notes'])}")
    
    if results['low_confidence_notes']:
        print("   Flagged for review:")
        for note in results['low_confidence_notes'][:5]:
            print(f"     - {note['id']}: confidence={note['confidence']}, evolutions={note['evolution_count']}")
    
    # 2. Confidence decay for stale notes
    print("\n2. Applying confidence decay...")
    decay_count = 0
    for note in mm.store.iterate_notes():
        # Decay confidence by 0.01 for notes not accessed in 30 days
        from datetime import datetime, timedelta
        try:
            last_accessed = datetime.fromisoformat(note.metadata.last_accessed or note.created_at)
            days_since_access = (datetime.now() - last_accessed).days
            
            if days_since_access > 30 and note.metadata.confidence > 0.3:
                note.metadata.confidence = max(0.3, note.metadata.confidence - 0.01)
                mm.store._rewrite_note(note)
                decay_count += 1
        except:
            pass
    
    print(f"   Decayed: {decay_count} notes")
    
    # 3. Export stats
    print("\n3. Exporting stats...")
    stats = mm.get_stats()
    print(f"   Total notes: {stats['total_notes']}")
    print(f"   Notes created: {stats['notes_created']}")
    print(f"   Links generated: {stats['links_generated']}")
    print(f"   Evolutions run: {stats['evolutions_run']}")
    
    # 4. Log to cold storage
    log_dir = Path("/media/rolandpg/USB-HDD/daily")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"maintenance_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.json"
    with open(log_file, 'w') as f:
        json.dump({
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'results': results,
            'stats': stats
        }, f, indent=2)
    
    print(f"\n   Logged to: {log_file}")
    
    # 5. Cold archive low-confidence notes (Phase 5)
    print("\n5. Archiving low-confidence notes to cold storage...")
    try:
        archive_result = mm.archive_low_confidence_notes(confidence_threshold=0.3, dry_run=False)
        print(f"   Archived: {archive_result.get('archived_count', 0)} notes")
        print(f"   Cold storage path: {archive_result.get('archive_path', 'N/A')}")
    except Exception as e:
        print(f"   Archive error (non-critical): {e}")
    
    print("\n=== Daily Maintenance Complete ===")


if __name__ == "__main__":
    main()
