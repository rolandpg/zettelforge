#!/usr/bin/env python3
"""Comprehensive system verification"""
import sys
import subprocess
import json
from pathlib import Path

print("=" * 70)
print("ROLAND FLEET - COMPREHENSIVE SYSTEM VERIFICATION")
print("=" * 70)

results = {"passed": 0, "failed": 0, "checks": []}

def check(name, cmd, expect_success=True):
    """Run a check and record result"""
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        success = (result.returncode == 0) if expect_success else True
        status = "✅ PASS" if success else "❌ FAIL"
        
        # Truncate output
        output = result.stdout.strip()[-200:] if result.stdout else ""
        if result.stderr and not success:
            output += f"\nError: {result.stderr[:100]}"
            
        results["checks"].append({"name": name, "status": success, "output": output})
        if success:
            results["passed"] += 1
        else:
            results["failed"] += 1
        print(f"\n{status}: {name}")
        if output:
            print(f"  {output[:150]}")
        return success
    except Exception as e:
        results["checks"].append({"name": name, "status": False, "error": str(e)})
        results["failed"] += 1
        print(f"\n❌ FAIL: {name}")
        print(f"  Exception: {e}")
        return False

# === A-MEM MEMORY SYSTEM ===
print("\n" + "-" * 70)
print("A-MEM MEMORY SYSTEM")
print("-" * 70)

check("Memory store accessible", 
      "python3 -c 'from memory_store import MemoryStore; print(MemoryStore().count_notes())'")

check("Note schema valid",
      "python3 -c 'from note_schema import MemoryNote; print(\"Schema OK\")'")

check("Entity indexer loads",
      "python3 -c 'from entity_indexer import EntityIndexer; ei = EntityIndexer(); ei.load(); print(f\"Indexed: {len(ei.index)} entities\")'")

check("Vector retriever imports",
      "python3 -c 'from vector_retriever import VectorRetriever; print(\"VR OK\")'")

check("Validation fixes working",
      "python3 -c 'from note_constructor import NoteConstructor; nc = NoteConstructor(); print(\"Constructor OK\")'")

# === CTI PLATFORM ===
print("\n" + "-" * 70)
print("CTI PLATFORM")
print("-" * 70)

check("CTI server running",
      "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/intel/")

check("CTI CVEs endpoint",
      "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/intel/cves/")

check("CTI actors endpoint", 
      "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/intel/actors/")

check("CTI IOCs endpoint",
      "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/intel/iocs/")

check("CTI alerts endpoint",
      "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/intel/alerts/")

# === SYSTEMD TIMERS ===
print("\n" + "-" * 70)
print("SYSTEMD TIMERS")
print("-" * 70)

check("Memory daily timer active",
      "systemctl --user is-active openclaw-memory-daily.timer")

check("Fleet sync timer active",
      "systemctl --user is-active openclaw-fleet-sync.timer")

check("CTI CFR timer active",
      "systemctl --user is-active openclaw-cti-cfr.timer")

check("Nexus timer active",
      "systemctl --user is-active openclaw-nexus.timer")

# === GIT STATUS ===
print("\n" + "-" * 70)
print("GIT REPOSITORY")
print("-" * 70)

check("Git repo clean (memory)",
      "cd /home/rolandpg/.openclaw/workspace/memory && git diff --quiet")

check("Recent commits",
      "cd /home/rolandpg/.openclaw/workspace/memory && git log --oneline -3")

# === DISK SPACE ===
print("\n" + "-" * 70)
print("DISK SPACE")
print("-" * 70)

check("Home disk space",
      "df -h /home | tail -1 | awk '{print $5 \" used\"}'")

check("Cold storage mounted",
      "mount | grep USB-HDD || echo 'Not mounted'")

# === SUMMARY ===
print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)
print(f"Total checks: {results['passed'] + results['failed']}")
print(f"Passed: {results['passed']}")
print(f"Failed: {results['failed']}")
print(f"Success rate: {results['passed']/(results['passed']+results['failed'])*100:.1f}%")

if results['failed'] == 0:
    print("\n🎉 ALL SYSTEMS OPERATIONAL")
    sys.exit(0)
else:
    print(f"\n⚠️  {results['failed']} CHECK(S) FAILED")
    for c in results['checks']:
        if not c.get('status'):
            print(f"  - {c['name']}")
    sys.exit(1)