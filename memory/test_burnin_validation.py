#!/usr/bin/env python3
"""
Test burn-in with validation fix verification
"""
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from burnin_harness import BurnInHarness

# Test with content that previously caused validation errors
test_cases = [
    {
        "content": """CVE-2026-20131: Cisco Secure Firewall Management Center (FMC) SQL injection vulnerability. 
        A successful exploit could allow an attacker to execute arbitrary SQL queries.""",
        "source_type": "cisa_advisory",
        "source_ref": "CVE-2026-20131"
    },
    {
        "content": """Handala Hack (Void Manticore / Red Sandstorm / Banished Kitten) Iranian MOIS-linked threat actor. 
        Active since 2023 targeting Israel with destructive attacks. Uses custom wipers and supply chain compromises.""",
        "source_type": "threat_report", 
        "source_ref": "actor-handala-hack"
    },
    {
        "content": """Volt Typhoon Chinese APT targeting critical infrastructure. 
        Uses living-off-the-land techniques. CISA advisory AA24-038A. Affects DIB, communications sectors.""",
        "source_type": "cisa_advisory",
        "source_ref": "volt-typhoon-apt"
    }
]

print("=" * 70)
print("BURN-IN VALIDATION FIX TEST")
print("=" * 70)

harness = BurnInHarness()
errors = []
success = []

for i, test in enumerate(test_cases, 1):
    print(f"\n[{i}/{len(test_cases)}] Testing: {test['source_ref']}")
    try:
        result = harness.ingest(
            content=test['content'],
            source_type=test['source_type'],
            source_ref=test['source_ref']
        )
        
        if result.status == "error":
            print(f"  ✗ ERROR: {result.error}")
            errors.append((test['source_ref'], result.error))
        elif result.status == "created":
            print(f"  ✓ CREATED: {result.note_id}")
            print(f"    Entities extracted: {result.entities_extracted}")
            print(f"    Latency: {result.latency_ms:.1f}ms")
            success.append(test['source_ref'])
        elif result.status == "duplicate_skipped":
            print(f"  ⚠ DUPLICATE: {result.reason}")
            success.append(test['source_ref'])  # Not an error
        else:
            print(f"  ? STATUS: {result.status} - {result.reason}")
            
    except Exception as e:
        print(f"  ✗ EXCEPTION: {e}")
        errors.append((test['source_ref'], str(e)))

print("\n" + "=" * 70)
print(f"RESULTS: {len(success)} succeeded, {len(errors)} errors")
print("=" * 70)

if errors:
    print("\nErrors:")
    for ref, err in errors:
        print(f"  - {ref}: {err}")
    sys.exit(1)
else:
    print("\n✅ All burn-in tests passed!")
    print(f"\nFinal note count: {harness.store.count_notes()}")
    sys.exit(0)