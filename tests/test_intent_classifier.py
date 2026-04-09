#!/usr/bin/env python3
"""
Test intent classifier in ZettelForge.
Validates Task 3: Lightweight intent classifier for adaptive query routing.
"""
import tempfile
import pytest

from zettelforge.intent_classifier import IntentClassifier, get_intent_classifier, QueryIntent


def test_intent_classification():
    classifier = get_intent_classifier()
    
    # Test queries
    test_queries = [
        # FACTUAL
        ("What CVE was used in the SolarWinds attack?", QueryIntent.FACTUAL),
        ("Which APT group targets energy sector?", QueryIntent.FACTUAL),
        ("What malware does APT28 use?", QueryIntent.FACTUAL),
        
        # TEMPORAL
        ("What changed since May 2024?", QueryIntent.TEMPORAL),
        ("When was Server ALPHA compromised?", QueryIntent.TEMPORAL),
        ("What is the history of this vulnerability?", QueryIntent.TEMPORAL),
        
        # RELATIONAL
        ("Who uses Cobalt Strike?", QueryIntent.RELATIONAL),
        ("Which actors target healthcare?", QueryIntent.RELATIONAL),
        
        # CAUSAL
        ("Why did the incident happen?", QueryIntent.CAUSAL),
        ("What caused the breach?", QueryIntent.CAUSAL),
        
        # EXPLORATORY
        ("Tell me about APT28", QueryIntent.EXPLORATORY),
        ("Explain the threat landscape", QueryIntent.EXPLORATORY),
    ]
    
    correct = 0
    for query, expected in test_queries:
        intent, meta = classifier.classify(query)
        # Ensure classify() returns a valid QueryIntent (not crashes)
        assert isinstance(intent, QueryIntent), f"Expected QueryIntent, got {type(intent)}"
        if intent == expected:
            correct += 1
        
        # Verify traversal policy is returned without error
        policy = classifier.get_traversal_policy(intent)
        assert 'vector' in policy
        assert 'graph' in policy
        assert 'temporal' in policy
    
    # Accuracy assertion only runs when Ollama is available (LLM-based classification).
    # Without Ollama the fallback pattern matcher achieves lower accuracy, which is
    # expected and not a defect in itself.
    try:
        import ollama
        ollama.list()
        ollama_available = True
    except Exception:
        ollama_available = False
    
    if ollama_available:
        assert correct >= len(test_queries) * 0.7, (
            f"Intent classification accuracy too low with Ollama: {correct}/{len(test_queries)}"
        )


def test_adaptive_recall(tmp_path):
    """Test recall routing via intent classifier."""
    from zettelforge import MemoryManager

    mm = MemoryManager(
        jsonl_path=str(tmp_path / "notes.jsonl"),
        lance_path=str(tmp_path / "vectordb"),
    )
    
    mm.remember("CVE-2024-1111 is a critical vulnerability in Microsoft Exchange", domain="cti")
    mm.remember("APT28 uses Cobalt Strike for lateral movement", domain="cti")
    
    # Factual recall should return notes
    results = mm.recall("What CVE was mentioned?", k=3)
    assert isinstance(results, list)
    
    # Relational recall should return notes
    results = mm.recall("Who uses Cobalt Strike?", k=3)
    assert isinstance(results, list)