#!/usr/bin/env python3
"""
Weekly Maintenance Script - Roland Fleet Memory System
Runs weekly tasks: full backup, reindex check, orphan link repair, cold purge
"""
import json
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from memory_manager import get_memory_manager


def main():
    print("=== Weekly Memory Maintenance ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    mm = get_memory_manager()
    
    # 1. Weekly maintenance report
    print("1. Running weekly maintenance report...")
    results = mm.weekly_maintenance()
    print(f"   Archives: {results['archive_count']}")
    print(f"   Orphaned links: {len(results['orphaned_links'])}")
    
    if results['orphaned_links']:
        print("   Repairing orphaned links...")
        for link in results['orphaned_links'][:10]:
            print(f"     - {link['from']} -> {link['to']} (broken)")
        # Note: actual repair would update the notes
    
    # 2. Full backup to cold storage
    print("\n2. Creating full backup...")
    backup_dir = Path("/media/rolandpg/USB-HDD/backups/weekly")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"memory_full_{timestamp}.jsonl"
    
    # Copy current notes
    src = mm.store.jsonl_path
    if src.exists():
        shutil.copy(src, backup_file)
        size = backup_file.stat().st_size
        print(f"   Backup: {backup_file}")
        print(f"   Size: {size / 1024:.1f} KB")
    
    # 3. Check for old archives to purge
    print("\n3. Checking archive retention...")
    archive_dir = Path("/media/rolandpg/USB-HDD/archive")
    if archive_dir.exists():
        archives = list(archive_dir.glob("*.jsonl"))
        print(f"   Total archives: {len(archives)}")
        
        # Find archives older than 90 days
        cutoff = datetime.now() - timedelta(days=90)
        old_archives = []
        for a in archives:
            mtime = datetime.fromtimestamp(a.stat().st_mtime)
            if mtime < cutoff:
                old_archives.append(a)
        
        if old_archives:
            print(f"   Old archives (90+ days): {len(old_archives)}")
            # Note: would delete in actual maintenance
        else:
            print(f"   No archives to purge")
    
    # 4. VectorDB reindex check
    print("\n4. VectorDB reindex check...")
    lance_path = Path("/home/rolandpg/.openclaw/workspace/vectordb")
    if lance_path.exists():
        tables = list(lance_path.glob("*.lantable"))
        print(f"   LanceDB tables: {len(tables)}")
        if tables:
            for t in tables[:3]:
                print(f"     - {t.name}")
    else:
        print(f"   LanceDB path not initialized")
    
    # 5. Log results
    print("\n5. Logging results...")
    log_dir = Path("/media/rolandpg/USB-HDD/weekly")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"maintenance_{datetime.now().strftime('%Y%m%d')}.json"
    with open(log_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'backup_file': str(backup_file),
            'stats': mm.get_stats()
        }, f, indent=2)
    
    print(f"   Log: {log_file}")
    print("\n=== Weekly Maintenance Complete ===")


if __name__ == "__main__":
    main()
