"""
Synthesis Validator — Phase 7 Response Validation
==================================================

Validates synthesis responses against schema rules and quality thresholds.
Ensures responses meet confidence requirements and have adequate source coverage.

Usage:
    from synthesis_validator import SynthesisValidator

    validator = SynthesisValidator()
    valid, errors = validator.validate_response(synthesis_result)
"""

import json
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
SCHEMA_FILE = MEMORY_DIR / "memory/synthesis_schema.json"


class SynthesisValidator:
    """
    Validates synthesis responses against quality thresholds.
    """

    def __init__(
        self,
        schema_file: str = None,
        min_confidence: float = 0.3,
        min_sources: int = 1,
        max_sources: int = 20,
        max_summary_length: int = 500,
        max_answer_length: int = 200
    ):
        self.schema_file = Path(schema_file) if schema_file else SCHEMA_FILE
        self.min_confidence = min_confidence
        self.min_sources = min_sources
        self.max_sources = max_sources
        self.max_summary_length = max_summary_length
        self.max_answer_length = max_answer_length
        self._schema = None
        self._load_schema()

    def _load_schema(self) -> None:
        """Load validation schema."""
        try:
            with open(self.schema_file) as f:
                self._schema = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._schema = self._default_schema()

    def _default_schema(self) -> Dict:
        """Default schema if file not found."""
        return {
            "validation_rules": {
                "min_sources": 1,
                "max_sources": 20,
                "min_confidence": 0.3,
                "max_summary_length": 500,
                "max_answer_length": 200
            }
        }

    def validate_response(self, response: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a complete synthesis response.

        Args:
            response: Synthesis response dictionary

        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []

        # Validate format
        format_valid, format_errors = self._validate_format(response)
        if not format_valid:
            errors.extend(format_errors)

        # Validate synthesis content
        synthesis = response.get("synthesis", {})
        synthesis_valid, synthesis_errors = self._validate_synthesis(synthesis)
        if not synthesis_valid:
            errors.extend(synthesis_errors)

        # Validate metadata
        metadata = response.get("metadata", {})
        metadata_valid, metadata_errors = self._validate_metadata(metadata)
        if not metadata_valid:
            errors.extend(metadata_errors)

        # Validate sources
        sources = response.get("sources", [])
        sources_valid, sources_errors = self._validate_sources(sources)
        if not sources_valid:
            errors.extend(sources_errors)

        return len(errors) == 0, errors

    def _validate_format(self, response: Dict) -> Tuple[bool, List[str]]:
        """Validate response format structure."""
        errors = []

        if "query" not in response:
            errors.append("Missing 'query' field")

        if "format" not in response:
            errors.append("Missing 'format' field")
        elif response["format"] not in ["direct_answer", "synthesized_brief", "timeline_analysis", "relationship_map"]:
            errors.append(f"Invalid format: {response.get('format')}")

        if "synthesis" not in response:
            errors.append("Missing 'synthesis' field")

        if "metadata" not in response:
            errors.append("Missing 'metadata' field")

        return len(errors) == 0, errors

    def _validate_synthesis(self, synthesis: Dict) -> Tuple[bool, List[str]]:
        """Validate synthesis content based on format."""
        errors = []

        if not isinstance(synthesis, dict):
            errors.append("synthesis must be a dictionary")
            return False, errors

        # Format-specific validation
        if "answer" in synthesis:
            answer = synthesis["answer"]
            if not isinstance(answer, str):
                errors.append("answer must be a string")
            elif len(answer) > self.max_answer_length:
                errors.append(f"answer exceeds maximum length ({len(answer)} > {self.max_answer_length})")

        if "summary" in synthesis:
            summary = synthesis["summary"]
            if not isinstance(summary, str):
                errors.append("summary must be a string")
            elif len(summary) > self.max_summary_length:
                errors.append(f"summary exceeds maximum length ({len(summary)} > {self.max_summary_length})")

        if "confidence" in synthesis:
            confidence = synthesis["confidence"]
            if not isinstance(confidence, (int, float)):
                errors.append("confidence must be a number")
            elif confidence < self.min_confidence:
                errors.append(f"confidence below threshold: {confidence} < {self.min_confidence}")
            elif confidence > 1.0:
                errors.append("confidence must be <= 1.0")

        return len(errors) == 0, errors

    def _validate_metadata(self, metadata: Dict) -> Tuple[bool, List[str]]:
        """Validate response metadata."""
        errors = []

        if not isinstance(metadata, dict):
            errors.append("metadata must be a dictionary")
            return False, errors

        # Check required metadata fields
        required = ["query_id", "model_used", "latency_ms", "sources_count"]
        for field in required:
            if field not in metadata:
                errors.append(f"Missing metadata field: {field}")

        # Validate confidence threshold
        if "confidence_threshold" in metadata:
            threshold = metadata["confidence_threshold"]
            if not isinstance(threshold, (int, float)):
                errors.append("confidence_threshold must be a number")
            elif threshold < 0 or threshold > 1:
                errors.append("confidence_threshold must be between 0 and 1")

        # Validate latency
        if "latency_ms" in metadata:
            latency = metadata["latency_ms"]
            if not isinstance(latency, int):
                errors.append("latency_ms must be an integer")
            elif latency < 0:
                errors.append("latency_ms must be non-negative")

        return len(errors) == 0, errors

    def _validate_sources(self, sources: List) -> Tuple[bool, List[str]]:
        """Validate sources array."""
        errors = []

        if not isinstance(sources, list):
            errors.append("sources must be an array")
            return False, errors

        if len(sources) < self.min_sources:
            errors.append(f"sources count below minimum: {len(sources)} < {self.min_sources}")

        if len(sources) > self.max_sources:
            errors.append(f"sources count exceeds maximum: {len(sources)} > {self.max_sources}")

        # Validate each source
        for i, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"source[{i}] must be a dictionary")
                continue

            if "note_id" not in source:
                errors.append(f"source[{i}] missing note_id")

            if "relevance_score" in source:
                score = source["relevance_score"]
                if not isinstance(score, (int, float)):
                    errors.append(f"source[{i}].relevance_score must be a number")
                elif score < 0 or score > 1:
                    errors.append(f"source[{i}].relevance_score must be between 0 and 1")

            if "quote" in source and not isinstance(source["quote"], str):
                errors.append(f"source[{i}].quote must be a string")

        return len(errors) == 0, errors

    def validate_answer(
        self,
        answer: str,
        confidence: float = None,
        sources: List[str] = None
    ) -> Tuple[bool, List[str]]:
        """Validate a direct answer response."""
        errors = []

        if not isinstance(answer, str):
            errors.append("answer must be a string")
        elif len(answer) == 0:
            errors.append("answer is empty")
        elif len(answer) > self.max_answer_length:
            errors.append(f"answer exceeds maximum length ({len(answer)} > {self.max_answer_length})")

        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                errors.append("confidence must be a number")
            elif confidence < self.min_confidence:
                errors.append(f"confidence below threshold: {confidence} < {self.min_confidence}")
            elif confidence > 1.0:
                errors.append("confidence must be <= 1.0")

        if sources is not None:
            if not isinstance(sources, list):
                errors.append("sources must be an array")
            elif len(sources) < self.min_sources:
                errors.append(f"sources count below minimum: {len(sources)} < {self.min_sources}")

        return len(errors) == 0, errors

    def validate_brief(
        self,
        summary: str,
        themes: List[Dict] = None,
        confidence: float = None,
        evidence: List[Dict] = None
    ) -> Tuple[bool, List[str]]:
        """Validate a synthesized brief response."""
        errors = []

        if not isinstance(summary, str):
            errors.append("summary must be a string")
        elif len(summary) == 0:
            errors.append("summary is empty")
        elif len(summary) > self.max_summary_length:
            errors.append(f"summary exceeds maximum length ({len(summary)} > {self.max_summary_length})")

        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                errors.append("confidence must be a number")
            elif confidence < self.min_confidence:
                errors.append(f"confidence below threshold: {confidence} < {self.min_confidence}")

        if themes is not None:
            if not isinstance(themes, list):
                errors.append("themes must be an array")
            elif len(themes) == 0:
                errors.append("themes array is empty")

        if evidence is not None:
            if not isinstance(evidence, list):
                errors.append("evidence must be an array")

        return len(errors) == 0, errors

    def check_quality_score(self, response: Dict) -> Dict:
        """
        Compute a quality score for a response.

        Returns:
            {
                "score": float (0-1),
                "components": {
                    "confidence": float,
                    "sources": float,
                    "completeness": float
                }
            }
        """
        synthesis = response.get("synthesis", {})
        metadata = response.get("metadata", {})
        sources = response.get("sources", [])

        # Confidence score (weighted)
        confidence = synthesis.get("confidence", 0)
        confidence_score = min(1.0, confidence / 0.7)  # Scale: 0.7 = 1.0

        # Sources score
        source_count = len(sources)
        source_score = min(1.0, source_count / 5)  # 5+ sources = 1.0

        # Completeness score
        completeness = 1.0
        if "answer" not in synthesis and "summary" not in synthesis:
            completeness = 0.0
        elif "confidence" not in synthesis:
            completeness *= 0.8
        elif "sources" not in response:
            completeness *= 0.9

        # Weighted total
        score = (
            confidence_score * 0.4 +
            source_score * 0.3 +
            completeness * 0.3
        )

        return {
            "score": round(score, 3),
            "components": {
                "confidence": round(confidence_score, 3),
                "sources": round(source_score, 3),
                "completeness": round(completeness, 3)
            },
            "quality": "EXCELLENT" if score >= 0.8 else "GOOD" if score >= 0.5 else "NEEDS_WORK"
        }


# =============================================================================
# Global Access
# =============================================================================

_validator: Optional[SynthesisValidator] = None
_validator_lock = threading.Lock()


def get_synthesis_validator() -> SynthesisValidator:
    """Get or create the global synthesis validator instance."""
    global _validator
    if _validator is None:
        with _validator_lock:
            if _validator is None:
                _validator = SynthesisValidator()
    return _validator


# =============================================================================
# CLI / Quick Test
# =============================================================================

if __name__ == "__main__":
    print("Synthesis Validator CLI")
    print("=" * 50)

    validator = SynthesisValidator()

    # Test valid response
    print("\n1. Valid response test:")
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

    valid, errors = validator.validate_response(valid_response)
    print(f"   Valid: {valid}")
    if errors:
        for e in errors:
            print(f"      - {e}")

    # Test invalid response (low confidence)
    print("\n2. Invalid response (low confidence):")
    invalid_response = valid_response.copy()
    invalid_response["synthesis"]["confidence"] = 0.15

    valid, errors = validator.validate_response(invalid_response)
    print(f"   Valid: {valid}")
    if errors:
        for e in errors:
            print(f"      - {e}")

    # Test quality score
    print("\n3. Quality score test:")
    score = validator.check_quality_score(valid_response)
    print(f"   Score: {score['score']}")
    print(f"   Quality: {score['quality']}")
    print(f"   Components: {score['components']}")

    print("\n4. Synthesis Validator initialized successfully.")
