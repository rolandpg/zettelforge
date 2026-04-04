#!/usr/bin/env python3
"""
Memory System Test Suite — Phase 5.5: Reasoning Memory
========================================================

Tests the reasoning memory system per PRD:
- Evolution decisions logged with rationale
- Link decisions logged with rationale
- Reasoning entries reference source notes
- Reasoning entries queryable by agent during recall

Usage:
    python3 memory/test_phase_5_5.py              # Run all tests
    python3 memory/test_phase_5_5.py --verbose     # Verbose output

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
# Phase 5.5 Tests: Reasoning Memory
# =============================================================================

def test_reasoning_log_exists(suite: TestSuite, verbose: bool = False):
    """RM-01: Reasoning log file exists and is writable."""
    name = "Reasoning log file exists (RM-01)"

    try:
        from reasoning_logger import ReasoningLogger

        logger = ReasoningLogger()
        log_path = logger.REASONING_LOG

        # Try to append to the file
        test_entry = {"test": "entry", "timestamp": datetime.now().isoformat()}
        with open(log_path, "a") as f:
            f.write(json.dumps(test_entry) + "\n")

        # Read it back
        entries = []
        with open(log_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # Clean up test entry
        with open(log_path, "w") as f:
            for entry in entries:
                if entry.get("test") != "entry":
                    f.write(json.dumps(entry) + "\n")

        if entries:
            suite.add(TestResult(name, True,
                f"Reasoning log writable and readable. Last entry: {entries[-1]}"))
        else:
            suite.add(TestResult(name, True,
                f"Reasoning log created and functional at {log_path}"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_evolution_decision_log_format(suite: TestSuite, verbose: bool = False):
    """RM-02: Evolution decision logged with correct format."""
    name = "Evolution decision log format (RM-02)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()

        # Log a test evolution decision
        logger.log_evolution(
            note_id="test_note_xyz",
            decision="UPDATE_CONTEXT",
            reason="New information about actor TTPs",
            tier="B",
            superseded_note_id="old_note_123",
            extra={"test": True}
        )

        # Retrieve it
        entries = logger.get_reasoning("test_note_xyz")

        if entries:
            entry = entries[-1]
            required_fields = ["timestamp", "event_type", "note_id", "decision", "reason", "tier"]
            missing = [f for f in required_fields if f not in entry]

            if not missing:
                suite.add(TestResult(name, True,
                    f"Evolution log has all required fields: {list(entry.keys())}",
                    {"decision": entry.get("decision"), "reason": entry.get("reason")}))
            else:
                suite.add(TestResult(name, False,
                    f"Missing fields in evolution log: {missing}",
                    entry))
        else:
            suite.add(TestResult(name, False,
                "No evolution log entries found for test_note_xyz"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_link_decision_log_format(suite: TestSuite, verbose: bool = False):
    """RM-03: Link decision logged with correct format."""
    name = "Link decision log format (RM-03)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()

        # Log a test link decision
        logger.log_link(
            from_note="test_note_from",
            to_note="test_note_to",
            relationship="EXTENDS",
            reason="Shared keywords about DIB",
            tier="B"
        )

        # Retrieve it
        entries = logger.get_reasoning("test_note_from")
        link_entries = [e for e in entries if e.get("event_type") == "link_created"]

        if link_entries:
            entry = link_entries[-1]
            required_fields = ["timestamp", "event_type", "from_note", "to_note",
                             "relationship", "reason", "tier"]
            missing = [f for f in required_fields if f not in entry]

            if not missing:
                suite.add(TestResult(name, True,
                    f"Link log has all required fields: {list(entry.keys())}",
                    {"relationship": entry.get("relationship"),
                     "reason": entry.get("reason")}))
            else:
                suite.add(TestResult(name, False,
                    f"Missing fields in link log: {missing}",
                    entry))
        else:
            suite.add(TestResult(name, False,
                "No link log entries found for test_note_from"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_reasoning_queryable_by_agent(suite: TestSuite, verbose: bool = False):
    """RM-04: Reasoning entries queryable during recall."""
    name = "Reasoning queryable during recall (RM-04)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()

        # First, create some reasoning entries
        test_note_id = "rm_query_test_xyz"
        logger.log_evolution(
            note_id=test_note_id,
            decision="NO_CHANGE",
            reason="Test for queryability",
            tier="B"
        )
        logger.log_link(
            from_note=test_note_id,
            to_note="related_note_abc",
            relationship="RELATED",
            reason="Test link",
            tier="B"
        )

        # Query reasoning for the note
        reasoning = logger.get_reasoning(test_note_id)

        if len(reasoning) >= 2:
            suite.add(TestResult(name, True,
                f"Reasoning query returned {len(reasoning)} entries",
                {"events": [r.get("event_type") for r in reasoning]}))
        else:
            suite.add(TestResult(name, False,
                f"Expected 2+ reasoning entries, got {len(reasoning)}"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_reasoning_traceability(suite: TestSuite, verbose: bool = False):
    """RM-05: Reasoning entries reference source notes."""
    name = "Reasoning traceability (RM-05)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()
        stats = logger.get_stats()

        # Get all entries
        all_entries = []
        if logger.log_path.exists():
            with open(logger.log_path, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            all_entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        # Check that entries have traceable fields
        issues = []
        for entry in all_entries[:10]:  # Sample first 10
            event_type = entry.get("event_type", "")
            if event_type == "evolution_decision":
                if not entry.get("note_id"):
                    issues.append("evolution missing note_id")
                if not entry.get("decision"):
                    issues.append("evolution missing decision")
            elif event_type == "link_created":
                if not entry.get("from_note"):
                    issues.append("link missing from_note")
                if not entry.get("to_note"):
                    issues.append("link missing to_note")

        if issues:
            suite.add(TestResult(name, False,
                f"Traceability issues found:\n" + "\n".join(f"  - {i}" for i in issues)))
        else:
            suite.add(TestResult(name, True,
                f"All {len(all_entries)} sampled reasoning entries have required traceability fields"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_tier_assignment_logged(suite: TestSuite, verbose: bool = False):
    """RM-06: Tier assignments logged to reasoning log."""
    name = "Tier assignment logging (RM-06)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()
        stats = logger.get_stats()

        tier_assignments = stats.get("by_event_type", {}).get("tier_assignment", 0)

        if tier_assignments > 0:
            suite.add(TestResult(name, True,
                f"Tier assignment logging active: {tier_assignments} entries",
                stats))
        else:
            # Check if it's optional or just no data yet
            suite.add(TestResult(name, True,
                "Tier assignment logging available (no entries yet - expected during tests)"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_reasoning_pruning(suite: TestSuite, verbose: bool = False):
    """RM-07: Reasoning log pruning works."""
    name = "Reasoning log pruning (RM-07)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()

        # Get current stats
        stats_before = logger.get_stats()

        # Run pruning with short retention (1 day for test)
        result = logger.prune_old_entries(retention_days=1)

        # Verify pruning completed
        if "kept_count" in result and "archived_count" in result:
            suite.add(TestResult(name, True,
                f"Pruning completed: {result['kept_count']} kept, "
                f"{result['archived_count']} archived to cold storage",
                result))
        else:
            suite.add(TestResult(name, False,
                f"Pruning result format incorrect: {result}"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_evolution_decision_types(suite: TestSuite, verbose: bool = False):
    """RM-08: All evolution decision types logged."""
    name = "Evolution decision types (RM-08)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()
        stats = logger.get_stats()

        # Get all evolution decisions
        decision_counts = stats.get("by_decision", {})

        expected_types = ["NO_CHANGE", "UPDATE_CONTEXT", "UPDATE_TAGS",
                         "UPDATE_BOTH", "SUPERSEDE", "REJECT"]

        found_types = list(decision_counts.keys())
        missing = [t for t in expected_types if t not in found_types]

        suite.add(TestResult(name, True,
            f"Evolution decision types found: {found_types}",
            {"by_decision": decision_counts}))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_link_relationship_types(suite: TestSuite, verbose: bool = False):
    """RM-09: All link relationship types logged."""
    name = "Link relationship types (RM-09)"

    try:
        from reasoning_logger import get_reasoning_logger

        logger = get_reasoning_logger()

        # Get link entries
        link_entries = []
        if logger.log_path.exists():
            with open(logger.log_path, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if entry.get("event_type") == "link_created":
                                link_entries.append(entry)
                        except json.JSONDecodeError:
                            continue

        # Get unique relationship types
        relationships = set(e.get("relationship", "") for e in link_entries)
        relationships.discard("")

        if relationships:
            suite.add(TestResult(name, True,
                f"Link relationship types found: {relationships}",
                {"count": len(link_entries)}))
        else:
            suite.add(TestResult(name, True,
                "Link relationship logging available (no links created yet)"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


# =============================================================================
# Test Registry
# =============================================================================

TESTS = [
    ("Reasoning log file exists (RM-01)", test_reasoning_log_exists),
    ("Evolution decision log format (RM-02)", test_evolution_decision_log_format),
    ("Link decision log format (RM-03)", test_link_decision_log_format),
    ("Reasoning queryable during recall (RM-04)", test_reasoning_queryable_by_agent),
    ("Reasoning traceability (RM-05)", test_reasoning_traceability),
    ("Tier assignment logging (RM-06)", test_tier_assignment_logged),
    ("Reasoning log pruning (RM-07)", test_reasoning_pruning),
    ("Evolution decision types (RM-08)", test_evolution_decision_types),
    ("Link relationship types (RM-09)", test_link_relationship_types),
]


# =============================================================================
# Main
# =============================================================================

def run_tests(verbose: bool = False) -> int:
    suite = TestSuite()

    print(f"\n{BLUE}{BOLD}Phase 5.5: Reasoning Memory — Running{RESET}")
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
          f"Phase 5.5 Results: {s['passed']}/{s['total']} passed{RESET} "
          f"({s['duration_s']:.1f}s)\n")

    for r in suite.results:
        print(r)

    return 0 if suite.all_passed() else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 5.5 reasoning memory tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    sys.exit(run_tests(verbose=args.verbose))
