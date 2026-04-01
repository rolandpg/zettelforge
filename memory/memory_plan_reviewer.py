#!/usr/bin/env python3
"""
Memory Plan Reviewer — iterates on the memory system improvement plan.

Runs the full test suite, reports phase-by-phase status, logs iterations,
and recommends next action. Designed to run every 30 minutes until the
PRD is fully commissioned.

Run via cron: */30 * * * *  (every 30 minutes)
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
WORKSPACE = Path("/home/rolandpg/.openclaw/workspace")
PLAN_PATH = MEMORY_DIR / "MEMORY_PRD.md"
STATS_LOG = MEMORY_DIR / "plan_iterations.jsonl"


def run_tests() -> dict:
    """Run the test suite and parse results."""
    test_script = MEMORY_DIR / "test_memory_system.py"
    if not test_script.exists():
        return {"error": "test_memory_system.py not found"}

    try:
        result = subprocess.run(
            [sys.executable, str(test_script)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(WORKSPACE)
        )
        output = result.stdout + result.stderr

        # Parse test summary
        total = passed = failed = 0
        phase_results = {}
        in_summary = False

        for line in output.split('\n'):
            # Strip ANSI codes
            import re
            line_clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()

            if 'Memory System Test Suite — Summary' in line_clean:
                in_summary = True
                continue

            if in_summary:
                if line_clean.startswith('Tests:'):
                    # "Tests: 28 passed / 0 failed (22.0s)"
                    parts = line_clean.split()
                    for i, p in enumerate(parts):
                        if p == 'Tests:':
                            total = int(parts[i+1])
                        elif p == 'passed':
                            passed = int(parts[i-1])
                        elif p == 'failed':
                            failed_val = parts[i-1].split('/')[0]
                            failed = int(failed_val)
                elif '✓ Phase' in line_clean or '✗ Phase' in line_clean:
                    # "  [✓ Phase 0[0m: 6/6 requirements" or "✓ Phase 1: 14/14 requirements"
                    # Extract phase number and ratio
                    parts = line_clean.replace('✓', '').replace('✗', '').split(':')
                    if len(parts) >= 2:
                        phase_part = parts[0].strip().replace('Phase', '').strip()
                        phase_num = phase_part
                        ratio_part = parts[1].split('/')[0].strip()
                        total_r = parts[1].split('/')[0].strip()
                        req_r = parts[1].split('/')[1].replace('requirements', '').strip()
                        phase_results[phase_num] = {
                            'passed': int(total_r),
                            'failed': int(req_r) - int(total_r),
                            'total': int(req_r)
                        }
                elif 'FAILED' in line_clean or 'PASSED' in line_clean or 'ALL TESTS' in line_clean:
                    in_summary = False

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'phase_results': phase_results,
            'output_preview': output[-500:] if len(output) > 500 else output
        }

    except subprocess.TimeoutExpired:
        return {"error": "Test suite timed out (>120s)"}
    except Exception as e:
        return {"error": str(e)}


def get_memory_stats() -> dict:
    """Get current memory system stats."""
    try:
        sys.path.insert(0, str(MEMORY_DIR))
        sys.path.insert(0, str(WORKSPACE))
        from memory.memory_manager import get_memory_manager
        mm = get_memory_manager()
        stats = mm.get_stats()
        entity_stats = mm.get_entity_stats() if hasattr(mm, 'get_entity_stats') else {}
        return {
            'total_notes': stats.get('total_notes', 0),
            'notes_created': stats.get('notes_created', 0),
            'duplicates_skipped': stats.get('duplicates_skipped', 0),
            'entity_index': entity_stats.get('total_entities', 0),
            'entity_breakdown': entity_stats.get('by_type', {})
        }
    except Exception as e:
        return {'error': str(e)}


def get_next_action(phase_results: dict, test_passed: bool) -> str:
    """Determine next action based on current state."""
    if not test_passed:
        # Find the first failing phase
        for phase in sorted(phase_results.keys(), key=lambda x: int(x)):
            pr = phase_results[phase]
            if pr.get('failed', 0) > 0:
                failures = pr.get('failed', 0)
                return (f"Phase {phase}: {failures} requirement(s) failing — "
                        f"run 'python3 memory/test_memory_system.py --phase {phase} --verbose' "
                        f"to identify specific failures")
        return "Tests failed but no specific phase identified — run test suite manually"

    # All tests passing — advance to next incomplete phase
    completed = [p for p, r in phase_results.items() if r.get('failed', 0) == 0]
    if '3' not in completed:
        return "Phase 3 (Date-Aware Retrieval) — implement supersedes tracking"
    if '4' not in completed:
        return "Phase 4 (Mid-Session Snapshot Refresh) — implement write-through snapshot"
    if '5' not in completed:
        return "Phase 5 (Cold Archive) — implement auto-archival of low-confidence notes"
    return "ALL PHASES COMPLETE — PRD fully commissioned"


def log_iteration(entry: dict):
    """Append to plan_iterations.jsonl"""
    with open(STATS_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def main():
    timestamp = datetime.now().isoformat()
    print(f"Memory Plan Review — {timestamp}")

    # Run tests
    test_results = run_tests()
    test_passed = test_results.get('failed', 999) == 0 and 'error' not in test_results

    # Get memory stats
    mem_stats = get_memory_stats()

    # Determine next action
    phase_results = test_results.get('phase_results', {})
    next_action = get_next_action(phase_results, test_passed)

    # Build entry
    entry = {
        'timestamp': timestamp,
        'tests_passed': test_passed,
        'tests_total': test_results.get('total', 0),
        'tests_failed': test_results.get('failed', 0),
        'phase_results': phase_results,
        'memory_stats': mem_stats,
        'next_action': next_action
    }

    # Print summary
    print(f"Tests: {test_results.get('passed', 0)}/{test_results.get('total', 0)} passed")
    if test_results.get('failed', 0) > 0:
        print(f"  FAILED: {test_results['failed']} requirement(s)")
        for phase, pr in sorted(phase_results.items(), key=lambda x: int(x[0])):
            if pr.get('failed', 0) > 0:
                print(f"  Phase {phase}: {pr['failed']} requirement(s) failing")
    else:
        print("  All tests passing")

    print(f"Memory: {mem_stats.get('total_notes', '?')} notes, "
          f"{mem_stats.get('entity_index', '?')} entities indexed")

    if 'error' in test_results:
        print(f"  Test error: {test_results['error']}")

    print(f"\nNext action: {next_action}")

    # Log
    log_iteration(entry)

    # Exit code: 0 if all passing, 1 if failures
    return 0 if test_passed else 1


if __name__ == "__main__":
    sys.exit(main())
