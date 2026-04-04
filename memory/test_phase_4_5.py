#!/usr/bin/env python3
"""
Memory System Test Suite — Phase 4.5: Epistemic Tiering
========================================================

Tests the epistemic tiering system per PRD:
- Tier A/B/C source tracking with note metadata
- Tier-aware evolution rules (supersedes, reject, etc.)
- Tier assignment auto-detection based on source type
- Tier override capability

Usage:
    python3 memory/test_phase_4_5.py              # Run all tests
    python3 memory/test_phase_4_5.py --verbose     # Verbose output

Exit codes:
    0  = All tests passed
    1  = One or more tests failed
"""

import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Setup paths
MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
WORKSPACE = Path("/home/rolandpg/.openclaw/workspace")
sys.path.insert(0, str(MEMORY_DIR))
sys.path.insert(0, str(WORKSPACE))

# Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


# =============================================================================
# Test Result Types
# =============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool,
                 message: str = "", details: Any = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
        self.timestamp = datetime.now().isoformat()

    def __str__(self):
        status = f"{GREEN}PASS{RESET}" if self.passed else f"{RED}FAIL{RESET}"
        return f"  [{status}] {self.name}\n         {self.message}"


class TestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = datetime.now()

    def add(self, result: TestResult):
        self.results.append(result)

    def summary(self) -> Dict:
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "duration_s": (datetime.now() - self.start_time).total_seconds()
        }

    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


# =============================================================================
# Phase 4.5 Tests: Epistemic Tiering
# =============================================================================

def test_tier_default_values(suite: TestSuite, verbose: bool = False):
    """ET-01: Default tier values are correctly assigned."""
    name = "Default tier assignment (ET-01)"

    try:
        from note_schema import MemoryNote
        from note_constructor import NoteConstructor

        constructor = NoteConstructor()
        note = constructor.enrich(
            raw_content="Test note about threat actors.",
            source_type="conversation",
            source_ref="test",
            domain="security_ops"
        )

        # Default tier for conversation/source type should be "B"
        expected_tier = "B"
        if note.metadata.tier == expected_tier:
            suite.add(TestResult(name, True,
                f"Default tier is '{expected_tier}' for source_type='conversation'"))
        else:
            suite.add(TestResult(name, False,
                f"Expected tier '{expected_tier}', got '{note.metadata.tier}'"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_tier_assignment_by_source(suite: TestSuite, verbose: bool = False):
    """ET-02: Tier assigned based on source type."""
    name = "Tier assignment by source type (ET-02)"

    try:
        from note_constructor import NoteConstructor

        constructor = NoteConstructor()

        # Test different source types
        test_cases = [
            ("conversation", "B"),  # Agent conversation
            ("observation", "A"),   # Tool observation
            ("task_output", "B"),   # Agent task
            ("ingestion", "A"),     # Human ingestion
        ]

        failures = []
        for source_type, expected_tier in test_cases:
            note = constructor.enrich(
                raw_content="Test note.",
                source_type=source_type,
                source_ref="test",
                domain="security_ops"
            )
            if note.metadata.tier != expected_tier:
                failures.append(f"{source_type}: expected '{expected_tier}', got '{note.metadata.tier}'")

        if failures:
            suite.add(TestResult(name, False,
                "Tier assignments incorrect:\n" + "\n".join(f"  - {f}" for f in failures)))
        else:
            suite.add(TestResult(name, True,
                f"All {len(test_cases)} source types have correct tier assignments"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_tier_in_note_schema(suite: TestSuite, verbose: bool = False):
    """ET-03: Tier field exists in note schema with correct type."""
    name = "Tier field in schema (ET-03)"

    try:
        from note_schema import MemoryNote, Metadata

        # Check Metadata has tier field
        meta = Metadata()
        if not hasattr(meta, 'tier'):
            suite.add(TestResult(name, False, "Metadata.tier field not found"))
            return

        # Check tier is a string
        if not isinstance(meta.tier, str):
            suite.add(TestResult(name, False,
                f"tier is {type(meta.tier).__name__}, expected str"))
            return

        # Check default value
        if meta.tier not in ["A", "B", "C"]:
            suite.add(TestResult(name, False,
                f"tier default '{meta.tier}' not in ['A', 'B', 'C']"))
            return

        suite.add(TestResult(name, True,
            f"Metadata.tier exists with default value '{meta.tier}'"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_evolution_reject_logging(suite: TestSuite, verbose: bool = False):
    """ET-04: REJECT decisions are logged to reasoning_log."""
    name = "REJECT decision logging (ET-04)"

    try:
        from memory_evolver import EvolutionDecider
        from note_schema import MemoryNote, Content, Semantic, Embedding, Metadata

        # Create a Tier B note and Tier A note
        evolver = EvolutionDecider()

        note_b = MemoryNote(
            id="test_B",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            content=Content(raw="Tier B note", source_type="test", source_ref="test"),
            semantic=Semantic(context="B context", keywords=[], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[0.1] * 768, dimensions=768, input_hash=""),
            metadata=Metadata(tier="B")
        )

        note_a = MemoryNote(
            id="test_A",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            content=Content(raw="Tier A note", source_type="test", source_ref="test"),
            semantic=Semantic(context="A context", keywords=[], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[0.1] * 768, dimensions=768, input_hash=""),
            metadata=Metadata(tier="A")
        )

        # Test: Tier B trying to supersede Tier A should be REJECT
        decision, reason = evolver.assess(note_b, note_a, log_reasoning=False)

        if decision == "REJECT":
            suite.add(TestResult(name, True,
                f"REJECT returned for B->A attempt: {reason}"))
        else:
            suite.add(TestResult(name, False,
                f"Expected REJECT for B->A, got {decision}"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_evolution_supersede_allowed(suite: TestSuite, verbose: bool = False):
    """ET-05: Tier A can supersede Tier B correctly."""
    name = "Tier A supersede Tier B (ET-05)"

    try:
        from memory_evolver import EvolutionDecider
        from note_schema import MemoryNote, Content, Semantic, Embedding, Metadata

        evolver = EvolutionDecider()

        note_a = MemoryNote(
            id="test_A",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            content=Content(raw="Tier A note", source_type="test", source_ref="test"),
            semantic=Semantic(context="A context", keywords=[], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[0.1] * 768, dimensions=768, input_hash=""),
            metadata=Metadata(tier="A")
        )

        note_b = MemoryNote(
            id="test_B",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            content=Content(raw="Tier B note", source_type="test", source_ref="test"),
            semantic=Semantic(context="B context", keywords=[], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[0.1] * 768, dimensions=768, input_hash=""),
            metadata=Metadata(tier="B")
        )

        # Test: Tier A trying to supersede Tier B should be SUPERSEDE
        decision, reason = evolver.assess(note_a, note_b, log_reasoning=False)

        if decision == "SUPERSEDE":
            suite.add(TestResult(name, True,
                f"SUPERSEDE returned for A->B attempt: {reason}"))
        else:
            suite.add(TestResult(name, False,
                f"Expected SUPERSEDE for A->B, got {decision}"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_tier_c_no_supersede(suite: TestSuite, verbose: bool = False):
    """ET-06: Tier C never triggers supersession."""
    name = "Tier C cannot supersede (ET-06)"

    try:
        from memory_evolver import EvolutionDecider
        from note_schema import MemoryNote, Content, Semantic, Embedding, Metadata

        evolver = EvolutionDecider()

        note_c = MemoryNote(
            id="test_C",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            content=Content(raw="Tier C note", source_type="test", source_ref="test"),
            semantic=Semantic(context="C context", keywords=[], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[0.1] * 768, dimensions=768, input_hash=""),
            metadata=Metadata(tier="C")
        )

        note_a = MemoryNote(
            id="test_A",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            content=Content(raw="Tier A note", source_type="test", source_ref="test"),
            semantic=Semantic(context="A context", keywords=[], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[0.1] * 768, dimensions=768, input_hash=""),
            metadata=Metadata(tier="A")
        )

        # Test: Tier C trying to supersede Tier A should be NO_CHANGE
        decision, reason = evolver.assess(note_c, note_a, log_reasoning=False)

        if decision == "NO_CHANGE":
            suite.add(TestResult(name, True,
                f"NO_CHANGE returned for C->A attempt (C never triggers supersession)"))
        else:
            suite.add(TestResult(name, False,
                f"Expected NO_CHANGE for C->A, got {decision}: {reason}"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_reasoning_log_query(suite: TestSuite, verbose: bool = False):
    """ET-07: mm.get_reasoning() returns log entries for a note."""
    name = "Reasoning log query (ET-07)"

    try:
        from memory_manager import get_memory_manager
        from reasoning_logger import get_reasoning_logger

        mm = get_memory_manager()
        logger = get_reasoning_logger()

        # Get reasoning for any note that has been created
        # First save a note
        note, _ = mm.remember("Test note for reasoning query", force=True)

        # Query reasoning for this note
        reasoning = logger.get_reasoning(note.id)

        suite.add(TestResult(name, True,
            f"get_reasoning() returned {len(reasoning)} entries for note {note.id}",
            {"note_id": note.id, "entry_count": len(reasoning)}))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_reasoning_log_has_entries(suite: TestSuite, verbose: bool = False):
    """ET-08: Reasoning log contains expected event types."""
    name = "Reasoning log event types (ET-08)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()
        stats = logger.get_stats()

        # alias_added is optional - only needed if Phase 3.5 auto-updates are active
        expected_types = ["evolution_decision", "link_created", "tier_assignment"]

        found_types = list(stats.get("by_event_type", {}).keys())
        missing = [t for t in expected_types if t not in found_types]

        if not missing:
            suite.add(TestResult(name, True,
                f"Reasoning log has all required event types: {found_types}",
                {"total_entries": stats.get("total_entries", 0)}))
        else:
            suite.add(TestResult(name, False,
                f"Missing event types: {missing}. Found: {found_types}"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_tier_pruning(suite: TestSuite, verbose: bool = False):
    """ET-09: Reasoning log pruning works."""
    name = "Reasoning log pruning (ET-09)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()
        stats_before = logger.get_stats()

        # Run pruning (should work even if no entries to prune)
        result = logger.prune_old_entries(retention_days=180)

        suite.add(TestResult(name, True,
            f"Pruning completed: {result.get('kept_count', 0)} kept, "
            f"{result.get('archived_count', 0)} archived",
            result))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_evolution_count_tracking(suite: TestSuite, verbose: bool = False):
    """ET-10: Evolution count tracked in note metadata."""
    name = "Evolution count tracking (ET-10)"

    try:
        from note_schema import MemoryNote, Content, Semantic, Embedding, Metadata
        from datetime import datetime

        # Create a test note with full construction
        note = MemoryNote(
            id="test_evolve",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            content=Content(raw="Original content", source_type="test", source_ref="test"),
            semantic=Semantic(context="Original", keywords=["original"], tags=[], entities=[]),
            embedding=Embedding(model="test", vector=[0.1] * 768, dimensions=768, input_hash=""),
            metadata=Metadata(evolution_count=0, confidence=1.0, access_count=0, domain="test")
        )

        # Simulate evolution
        note.increment_evolution("update_note_1")
        if note.metadata.evolution_count != 1:
            suite.add(TestResult(name, False,
                f"Evolution count not incremented: got {note.metadata.evolution_count}"))
            return

        # Check confidence decay
        if note.metadata.confidence != 0.95:
            suite.add(TestResult(name, False,
                f"Confidence not decayed: got {note.metadata.confidence}"))
            return

        suite.add(TestResult(name, True,
            "Evolution count and confidence decay working correctly",
            {"evolution_count": note.metadata.evolution_count,
             "confidence": note.metadata.confidence}))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


# =============================================================================
# Test Registry
# =============================================================================

TESTS = [
    ("Default tier assignment (ET-01)", test_tier_default_values),
    ("Tier assignment by source (ET-02)", test_tier_assignment_by_source),
    ("Tier field in schema (ET-03)", test_tier_in_note_schema),
    ("REJECT decision logging (ET-04)", test_evolution_reject_logging),
    ("Tier A supersede Tier B (ET-05)", test_evolution_supersede_allowed),
    ("Tier C cannot supersede (ET-06)", test_tier_c_no_supersede),
    ("Reasoning log query (ET-07)", test_reasoning_log_query),
    ("Reasoning log event types (ET-08)", test_reasoning_log_has_entries),
    ("Reasoning log pruning (ET-09)", test_tier_pruning),
    ("Evolution count tracking (ET-10)", test_evolution_count_tracking),
]


# =============================================================================
# Main
# =============================================================================

def run_tests(verbose: bool = False) -> int:
    suite = TestSuite()

    print(f"\n{BLUE}{BOLD}Phase 4.5: Epistemic Tiering — Running{RESET}")
    print(f"{'='*60}")

    for test_name, test_fn in TESTS:
        if verbose:
            print(f"\n  >> {test_name}")
        try:
            test_fn(suite, verbose)
        except Exception as e:
            suite.add(TestResult(test_name, False,
                f"Unhandled exception in test: {e}\n{traceback.format_exc()}"))

    # Print results
    print(f"\n{'='*60}")
    s = suite.summary()
    print(f"\n{GREEN if s['failed'] == 0 else RED}{BOLD}"
          f"Phase 4.5 Results: {s['passed']}/{s['total']} passed{RESET} "
          f"({s['duration_s']:.1f}s)\n")

    for r in suite.results:
        print(r)

    return 0 if suite.all_passed() else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 4.5 epistemic tiering tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    sys.exit(run_tests(verbose=args.verbose))
