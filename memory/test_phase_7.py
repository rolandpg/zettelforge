"""
Phase 7 Tests — Synthesis Layer (RAG-as-Answer)
================================================

Test suite for Phase 7 implementation:
- Synthesis schema validation
- Synthesis generation with LLM
- Hybrid retrieval (vector + graph)
- Response validation
- Integration with memory manager

Usage:
    python test_phase_7.py

Expected: All tests passing
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'memory'))

import unittest
from memory.synthesis_generator import SynthesisGenerator, get_synthesis_generator
from memory.synthesis_retriever import SynthesisRetriever, get_synthesis_retriever
from memory.synthesis_validator import SynthesisValidator, get_synthesis_validator
from memory_manager import get_memory_manager, MemoryManager


class TestSynthesisSchema(unittest.TestCase):
    """Test synthesis schema structure."""

    def test_schema_exists(self):
        """Schema file should exist."""
        schema_path = Path(__file__).parent / 'memory' / 'synthesis_schema.json'
        self.assertTrue(schema_path.exists())

    def test_response_formats_defined(self):
        """Schema should define all response formats."""
        schema_path = Path(__file__).parent / 'memory' / 'synthesis_schema.json'
        with open(schema_path) as f:
            schema = json.load(f)

        required_formats = [
            'direct_answer',
            'synthesized_brief',
            'timeline_analysis',
            'relationship_map'
        ]
        for fmt in required_formats:
            self.assertIn(fmt, schema.get('response_formats', {}))

    def test_validation_rules_defined(self):
        """Schema should define validation rules."""
        schema_path = Path(__file__).parent / 'memory' / 'synthesis_schema.json'
        with open(schema_path) as f:
            schema = json.load(f)

        rules = schema.get('validation_rules', {})
        self.assertIn('min_confidence', rules)
        self.assertIn('max_summary_length', rules)
        self.assertIn('max_answer_length', rules)


class TestSynthesisGenerator(unittest.TestCase):
    """Test synthesis generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.gen = SynthesisGenerator()

    def test_init(self):
        """Test generator initialization."""
        self.assertIsNotNone(self.gen)
        self.assertEqual(self.gen.llm_model, "nemotron-3-nano")

    def test_default_schema(self):
        """Test default schema when file missing."""
        gen = SynthesisGenerator(schema_file="/nonexistent/schema.json")
        self.assertIsNotNone(gen._schema)

    def test_get_json_format(self):
        """Test JSON format generation."""
        formats = ['direct_answer', 'synthesized_brief', 'timeline_analysis', 'relationship_map']
        for fmt in formats:
            json_schema = self.gen._get_json_format(fmt)
            self.assertIsInstance(json_schema, dict)
            self.assertIn('properties', json_schema)

    def test_build_prompt(self):
        """Test prompt building."""
        prompt = self.gen._build_prompt("test query", "test context", "direct_answer")
        self.assertIn("test query", prompt)
        self.assertIn("test context", prompt)

    def test_fallback_synthesis(self):
        """Test fallback synthesis when LLM unavailable."""
        fallback = self.gen._fallback_synthesis("test", "direct_answer")
        self.assertIn("answer", fallback)
        self.assertIn("confidence", fallback)
        self.assertIn("sources", fallback)

        brief = self.gen._fallback_synthesis("test", "synthesized_brief")
        self.assertIn("summary", brief)
        self.assertIn("confidence", brief)


class TestSynthesisRetriever(unittest.TestCase):
    """Test hybrid retrieval."""

    def setUp(self):
        """Set up test fixtures."""
        self.retriever = SynthesisRetriever()

    def test_init(self):
        """Test retriever initialization."""
        self.assertIsNotNone(self.retriever)

    def test_extract_entities(self):
        """Test entity extraction from text."""
        entities = self.retriever._extract_entities("CVE-2024-3094 was exploited by MuddyWater")
        self.assertIn('cve-2024-3094', [e.lower() for e in entities])

    def test_index_entities_by_type(self):
        """Test entity indexing."""
        entities = ['cve-2024-3094', 'muddywater', 'apt28', 'cobalt-strike']
        indexed = self.retriever._index_entities_by_type(entities)
        self.assertIn('cve', indexed)
        self.assertIn('actor', indexed)


class TestSynthesisValidator(unittest.TestCase):
    """Test response validation."""

    def setUp(self):
        """Set up validator."""
        self.validator = SynthesisValidator()

    def test_init(self):
        """Test validator initialization."""
        self.assertIsNotNone(self.validator)

    def test_validate_valid_response(self):
        """Test validation of valid response."""
        valid_response = {
            "query": "test query",
            "format": "direct_answer",
            "synthesis": {
                "answer": "This is a test answer.",
                "confidence": 0.85,
                "sources": ["note_1", "note_2"]
            },
            "metadata": {
                "query_id": "abc123",
                "model_used": "test-model",
                "latency_ms": 150,
                "sources_count": 2,
                "confidence_threshold": 0.3
            },
            "sources": [
                {"note_id": "note_1", "relevance_score": 0.8},
                {"note_id": "note_2", "relevance_score": 0.7}
            ]
        }
        valid, errors = self.validator.validate_response(valid_response)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_validate_low_confidence(self):
        """Test validation of low confidence response."""
        invalid_response = {
            "query": "test",
            "format": "direct_answer",
            "synthesis": {
                "answer": "Answer",
                "confidence": 0.15,
                "sources": ["note_1"]
            },
            "metadata": {
                "query_id": "abc",
                "model_used": "model",
                "latency_ms": 100,
                "sources_count": 1,
                "confidence_threshold": 0.3
            },
            "sources": [{"note_id": "note_1"}]
        }
        valid, errors = self.validator.validate_response(invalid_response)
        self.assertFalse(valid)
        self.assertTrue(any('confidence' in e.lower() for e in errors))

    def test_check_quality_score(self):
        """Test quality score computation."""
        valid_response = {
            "query": "test",
            "format": "direct_answer",
            "synthesis": {
                "answer": "Answer",
                "confidence": 0.85,
                "sources": ["note_1", "note_2"]
            },
            "metadata": {
                "query_id": "abc",
                "model_used": "model",
                "latency_ms": 100,
                "sources_count": 2,
                "confidence_threshold": 0.3
            },
            "sources": [
                {"note_id": "note_1", "relevance_score": 0.8},
                {"note_id": "note_2", "relevance_score": 0.7}
            ]
        }
        score = self.validator.check_quality_score(valid_response)
        self.assertIn('score', score)
        self.assertIn('quality', score)
        self.assertIn('components', score)
        self.assertGreater(score['score'], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests with MemoryManager."""

    def test_synthesize_with_mm(self):
        """Test synthesize() through MemoryManager."""
        mm = get_memory_manager()

        # Should work even with no notes
        result = mm.synthesize(
            query="What do we know about threat actors?",
            format="synthesized_brief",
            k=3
        )

        self.assertIn('query', result)
        self.assertIn('format', result)
        self.assertIn('synthesis', result)
        self.assertIn('metadata', result)

    def test_retrieve_context_with_mm(self):
        """Test retrieve_synthesis_context() through MemoryManager."""
        mm = get_memory_manager()

        context = mm.retrieve_synthesis_context(
            query="test query",
            k=3
        )

        self.assertIn('query', context)
        self.assertIn('notes', context)
        self.assertIn('entities', context)

    def test_validate_through_mm(self):
        """Test validate_synthesis() through MemoryManager."""
        mm = get_memory_manager()

        response = {
            "query": "test",
            "format": "direct_answer",
            "synthesis": {
                "answer": "Test answer",
                "confidence": 0.5,
                "sources": ["note_1"]
            },
            "metadata": {
                "query_id": "test123",
                "model_used": "test",
                "latency_ms": 100,
                "sources_count": 1,
                "confidence_threshold": 0.3
            },
            "sources": [{"note_id": "note_1"}]
        }

        valid, errors = mm.validate_synthesis(response)
        # Just check method exists and runs
        self.assertIsNotNone(valid)


class TestGlobalAccessors(unittest.TestCase):
    """Test global accessor functions."""

    def test_get_synthesis_generator(self):
        """Test global generator accessor."""
        gen = get_synthesis_generator()
        self.assertIsInstance(gen, SynthesisGenerator)

    def test_get_synthesis_retriever(self):
        """Test global retriever accessor."""
        retriever = get_synthesis_retriever()
        self.assertIsInstance(retriever, SynthesisRetriever)

    def test_get_synthesis_validator(self):
        """Test global validator accessor."""
        validator = get_synthesis_validator()
        self.assertIsInstance(validator, SynthesisValidator)


def run_all_tests():
    """Run all Phase 7 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestSynthesisSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestSynthesisGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestSynthesisRetriever))
    suite.addTests(loader.loadTestsFromTestCase(TestSynthesisValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestGlobalAccessors))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
