#!/usr/bin/env python3
"""Test the entity normalization fix"""
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from note_constructor import NoteConstructor

# Test with problematic entity formats
test_cases = [
    {
        "name": "Dict entities (CVE)",
        "content": "CVE-2026-20131 critical vulnerability in Cisco"
    },
    {
        "name": "Dict entities (actor)",
        "content": "Volt Typhoon Chinese APT targeting DIB"
    },
    {
        "name": "Long keywords list",
        "content": "Security research threat intelligence analysis vulnerability assessment penetration testing red team blue team incident response forensics malware analysis"
    }
]

constructor = NoteConstructor(llm_model="qwen2.5:3b")

print("Testing entity normalization and keyword slicing...\n")

for test in test_cases:
    print(f"Test: {test['name']}")
    try:
        note = constructor.enrich(
            raw_content=test['content'],
            source_type="test",
            source_ref="test",
            domain="security_ops"
        )
        print(f"  ✓ Note created: {note.id}")
        print(f"    Keywords ({len(note.semantic.keywords)}): {note.semantic.keywords}")
        print(f"    Entities ({len(note.semantic.entities)}): {note.semantic.entities[:3]}...")
        print(f"    Tags ({len(note.semantic.tags)}): {note.semantic.tags}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    print()

print("Test complete!")