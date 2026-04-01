#!/usr/bin/env python3
"""
Memory Plan Reviewer — iterates on the memory system improvement plan.

Runs the full test suite, reports phase-by-phase status, logs iterations,
recommends next action, and maintains PRD context. Designed to run every
30 minutes until the PRD is fully commissioned.

Run via cron: */30 * * * *  (every 30 minutes)
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
WORKSPACE = Path("/home/rolandpg/.openclaw/workspace")
PRD_PATH = MEMORY_DIR / "MEMORY_PRD.md"
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
                            failed = int(parts[i-1].split('/')[0])
                elif '✓ Phase' in line_clean or '✗ Phase' in line_clean:
                    # "  ✓ Phase 1: 14/14 requirements"
                    parts = line_clean.replace('✓', '').replace('✗', '').split(':')
                    if len(parts) >= 2:
                        phase_part = parts[0].strip().replace('Phase', '').strip()
                        phase_num = phase_part
                        ratio = parts[1].split('/')
                        total_r = int(ratio[0].strip())
                        req_r = int(ratio[1].replace('requirements', '').strip())
                        phase_results[phase_num] = {
                            'passed': total_r,
                            'failed': req_r - total_r,
                            'total': req_r
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
        sys.path.insert(0, str(WORKSPACE))
        sys.path.insert(0, str(MEMORY_DIR))
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
        for phase in sorted(phase_results.keys(), key=lambda x: int(x)):
            pr = phase_results[phase]
            if pr.get('failed', 0) > 0:
                failures = pr.get('failed', 0)
                return (f"Phase {phase}: {failures} requirement(s) failing — "
                        f"run 'python3 memory/test_memory_system.py --phase {phase} --verbose'")
        return "Tests failed — run test suite manually"

    # All tests passing — advance to next incomplete phase
    completed = [p for p, r in phase_results.items() if r.get('failed', 0) == 0]
    if '3' not in completed:
        return "Phase 3 (Date-Aware Retrieval) — implement supersedes tracking"
    if '4' not in completed:
        return "Phase 4 (Mid-Session Snapshot Refresh) — implement write-through snapshot"
    if '5' not in completed:
        return "Phase 5 (Cold Archive) — implement auto-archival of low-confidence notes"
    return "ALL PHASES COMPLETE — PRD fully commissioned"


def load_prd() -> dict:
    """Load and parse the PRD for phase context."""
    if not PRD_PATH.exists():
        return {'error': 'PRD not found'}

    text = PRD_PATH.read_text()
    phases = {}

    # Extract phase definitions from PRD
    phase_pattern = re.compile(
        r'(?:Phase (\d+):\s*(.+?)(?:\n---|##|$))',
        re.DOTALL | re.IGNORECASE
    )
    for m in phase_pattern.finditer(text):
        phase_num = m.group(1)
        content = m.group(2).strip()[:200]
        phases[phase_num] = content

    # Extract success metrics
    metrics = []
    metric_pattern = re.compile(r'[-*]\s+(.+?)(?:\n|$)', re.IGNORECASE)
    for m in metric_pattern.finditer(text):
        if 'metric' in m.group(1).lower() or 'criterion' in m.group(1).lower():
            metrics.append(m.group(1).strip())

    return {
        'path': str(PRD_PATH),
        'phases': phases,
        'size_bytes': len(text),
        'success_criteria': metrics[:5]
    }


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

    # Get memory + PRD stats
    mem_stats = get_memory_stats()
    prd_info = load_prd()

    # Determine next action
    phase_results = test_results.get('phase_results', {})
    next_action = get_next_action(phase_results, test_passed)

    # Build log entry
    entry = {
        'timestamp': timestamp,
        'tests_passed': test_passed,
        'tests_total': test_results.get('total', 0),
        'tests_failed': test_results.get('failed', 0),
        'phase_results': phase_results,
        'memory_stats': mem_stats,
        'prd_info': prd_info,
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

    print(f"\nPRD: {prd_info.get('phases', {})}")

    print(f"\nNext action: {next_action}")

    # Log
    log_iteration(entry)

    return 0 if test_passed else 1


if __name__ == "__main__":
    sys.exit(main())
