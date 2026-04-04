#!/usr/bin/env python3
"""Quick validation test - check for remaining validation errors"""
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from note_constructor import NoteConstructor
from note_schema import Semantic

# Test cases that previously caused validation errors
test_cases = [
    {
        "name": "Too many keywords",
        "content": "A B C D E F G H I J K L M N O P"  # 16 words
    },
    {
        "name": "Dict entities in content",
        "content": "CVE-2026-20131 vulnerability found in Cisco systems"
    },
    {
        "name": "Long content with many entities",
        "content": """Security Alert: Threat actor 'Volt Typhoon' (associated with PRC) 
        has been targeting networking equipment from Asus, Cisco, Netgear, and others. 
        The actor uses 'living off the land' techniques. CISA released advisory AA24-038A."""
    }
]

constructor = NoteConstructor(llm_model="qwen2.5:3b")
errors = []
success = []

print("=" * 60)
print("VALIDATION ERROR FIX TEST")
print("=" * 60)

for test in test_cases:
    print(f"\nTest: {test['name']}")
    try:
        note = constructor.enrich(
            raw_content=test['content'],
            source_type="test",
            source_ref="test_validation",
            domain="security_ops"
        )
        
        # Validate the note can be serialized/deserialized
        note_json = note.model_dump_json()
        
        # Check constraints
        kw_count = len(note.semantic.keywords)
        tag_count = len(note.semantic.tags)
        ent_count = len(note.semantic.entities)
        
        issues = []
        if kw_count > 7:
            issues.append(f"keywords={kw_count} (max 7)")
        if tag_count > 5:
            issues.append(f"tags={tag_count} (max 5)")
            
        if issues:
            print(f"  ✗ CONSTRAINT VIOLATION: {', '.join(issues)}")
            errors.append((test['name'], issues))
        else:
            print(f"  ✓ PASS")
            print(f"    Keywords ({kw_count}): {note.semantic.keywords}")
            print(f"    Tags ({tag_count}): {note.semantic.tags}")
            print(f"    Entities ({ent_count}): {note.semantic.entities}")
            success.append(test['name'])
            
    except Exception as e:
        print(f"  ✗ VALIDATION ERROR: {e}")
        errors.append((test['name'], str(e)))

print("\n" + "=" * 60)
print(f"RESULTS: {len(success)} passed, {len(errors)} failed")
print("=" * 60)

if errors:
    print("\nErrors:")
    for name, err in errors:
        print(f"  - {name}: {err}")
    sys.exit(1)
else:
    print("\n✅ All validation tests passed!")
    sys.exit(0)