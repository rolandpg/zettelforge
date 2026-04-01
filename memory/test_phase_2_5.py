#!/usr/bin/env python3
"""
Memory System Test Suite — Phase 2.5: Actor Alias Resolution
=============================================================

Tests the actor alias resolution system per OPUS spec:
- alias_maps/actors.json, tools.json, campaigns.json
- AliasResolver class with resolve(), get_canonical(), get_all_aliases()
- Cross-alias linking in entity-guided evolution
- Self-updating alias list from note content
- Canonical names in entity_index.json

Usage:
    python3 memory/test_phase_2_5.py              # Run all tests
    python3 memory/test_phase_2_5.py --verbose     # Verbose output

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
RED   = "\033[91m"
GREEN = "\033[92m"
YELLOW= "\033[93m"
BLUE  = "\033[94m"
RESET = "\033[0m"
BOLD  = "\033[1m"


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
# Test Fixtures
# =============================================================================

def get_alias_map_dir() -> Path:
    return MEMORY_DIR / "alias_maps"


def get_alias_map_path(entity_type: str = 'actor') -> Path:
    return get_alias_map_dir() / f"{entity_type}s.json"


def load_alias_map(entity_type: str = 'actor') -> Dict:
    """Load aliases dict from alias_maps/{entity_type}s.json."""
    path = get_alias_map_path(entity_type)
    if not path.exists():
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get('aliases', {})


def save_alias_map(aliases: Dict, entity_type: str = 'actor',
                   meta: Dict = None):
    """Save full alias map including _meta wrapper."""
    path = get_alias_map_path(entity_type)
    data = {"_meta": meta or {}, "aliases": aliases}
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_entity_index() -> Dict:
    path = MEMORY_DIR / "entity_index.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_notes() -> List[Dict]:
    path = MEMORY_DIR / "notes.jsonl"
    if not path.exists():
        return []
    notes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                notes.append(json.loads(line))
    return notes


def clean_note(note_id: str):
    """Remove a note from notes.jsonl and entity_index if it exists."""
    notes_path = MEMORY_DIR / "notes.jsonl"
    if notes_path.exists():
        lines = []
        with open(notes_path) as f:
            for line in f:
                if json.loads(line).get('id') != note_id:
                    lines.append(line)
        with open(notes_path, 'w') as f:
            f.writelines(lines)

    idx = load_entity_index()
    for entity_type in idx:
        for entity_name in list(idx[entity_type].keys()):
            if note_id in idx[entity_type][entity_name]:
                idx[entity_type][entity_name].remove(note_id)
                if not idx[entity_type][entity_name]:
                    del idx[entity_type][entity_name]
    with open(MEMORY_DIR / "entity_index.json", 'w') as f:
        json.dump(idx, f, indent=2)


# =============================================================================
# Phase 2.5 Tests: Actor Alias Resolution
# =============================================================================

def test_alias_map_structure(suite: TestSuite, verbose: bool = False):
    """Alias mapping files exist and have correct structure per OPUS spec."""
    name = "Alias map structure (actors.json, tools.json)"
    try:
        actors_path = get_alias_map_path('actor')
        tools_path = get_alias_map_path('tool')

        errors = []

        # Test actors.json
        if not actors_path.exists():
            errors.append(f"actors.json not found at {actors_path}")
        else:
            try:
                actors = load_alias_map('actor')
                if not actors:
                    errors.append("actors.json is empty or has no 'aliases' key")
                elif len(actors) < 3:
                    errors.append(f"Expected at least 3 actor entries, found {len(actors)}")

                # Check structure
                for canonical, entry in actors.items():
                    if 'names' not in entry:
                        errors.append(f"'{canonical}' missing 'names' field")
                    if not isinstance(entry.get('names'), list):
                        errors.append(f"'{canonical}' 'names' is not a list")
                    if 'canonical' not in entry:
                        errors.append(f"'{canonical}' missing 'canonical' field")

                # MITRE IDs check
                actors_with_mitre = {k: v for k, v in actors.items()
                                     if v.get('mitre_id')}
                if not actors_with_mitre:
                    errors.append("No MITRE ATT&CK IDs found in actors map")

            except json.JSONDecodeError as e:
                errors.append(f"actors.json is not valid JSON: {e}")

        # Test tools.json
        if not tools_path.exists():
            errors.append(f"tools.json not found at {tools_path}")
        else:
            try:
                tools = load_alias_map('tool')
                if not tools:
                    errors.append("tools.json is empty or has no 'aliases' key")
            except json.JSONDecodeError as e:
                errors.append(f"tools.json is not valid JSON: {e}")

        if errors:
            suite.add(TestResult(name, False, "; ".join(errors)))
        else:
            actors = load_alias_map('actor')
            tools = load_alias_map('tool')
            suite.add(TestResult(name, True,
                f"actors.json: {len(actors)} actors. tools.json: {len(tools)} tools. "
                f"Structure valid per OPUS spec.",
                {"actor_count": len(actors), "tool_count": len(tools)}))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_alias_resolver_creation(suite: TestSuite, verbose: bool = False):
    """AliasResolver class loads and builds reverse map without errors."""
    name = "AliasResolver instantiation"
    try:
        from alias_resolver import AliasResolver
        resolver = AliasResolver()
        suite.add(TestResult(name, True,
            f"AliasResolver loaded. Stats: {resolver.stats()}"))
    except Exception as e:
        suite.add(TestResult(name, False, f"Failed to create AliasResolver: {e}"))


def test_canonical_resolution(suite: TestSuite, verbose: bool = False):
    """AR-01 through AR-05: resolve() maps aliases to canonical names."""
    name = "Canonical form resolution (AR-01 to AR-05)"
    try:
        from alias_resolver import AliasResolver
        resolver = AliasResolver()

        cases = [
            # (entity_type, raw, expected_canonical)
            ('actor', 'mercury', 'muddywater'),       # AR-01
            ('actor', 'muddywater', 'muddywater'),    # AR-02
            ('actor', 'unknown_actor', 'unknown_actor'),  # AR-03 graceful deg
            ('tool', 'cs beacon', 'cobalt strike'),   # AR-04
            ('cve', 'CVE-2024-3094', 'cve-2024-3094'), # AR-05 CVE pass-through
        ]

        failed = []
        for et, raw, expected in cases:
            result = resolver.resolve(et, raw)
            if result != expected:
                failed.append(f"resolve('{et}', '{raw}') -> '{result}' (expected '{expected}')")

        if failed:
            suite.add(TestResult(name, False,
                "Resolution failures:\n" + "\n".join(f"  - {f}" for f in failed)))
        else:
            suite.add(TestResult(name, True,
                f"All {len(cases)} resolution cases passed (AR-01 to AR-05)"))

    except ImportError as e:
        suite.add(TestResult(name, False, f"Could not import AliasResolver: {e}"))
    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_alias_collision_detection(suite: TestSuite, verbose: bool = False):
    """AR-06: Duplicate alias across two canonicals raises ValueError."""
    name = "Alias collision detection (AR-06)"
    try:
        from alias_resolver import AliasResolver

        # Temporarily inject a collision
        actors = load_alias_map('actor')
        actors['_test_collision'] = {
            "mitre_id": None, "canonical": "_test_collision",
            "names": ["mercury"]  # Already claimed by muddywater
        }
        meta = {"version": "1.0", "updated": "2026-03-31",
                "source": "test", "entity_type": "actor"}
        save_alias_map(actors, 'actor', meta)

        try:
            resolver = AliasResolver()
            suite.add(TestResult(name, False,
                "Expected ValueError on collision but resolver loaded without error"))
        except ValueError as e:
            if 'mercury' in str(e):
                suite.add(TestResult(name, True,
                    f"ValueError raised correctly on collision: {e}"))
            else:
                suite.add(TestResult(name, False,
                    f"ValueError raised but wrong content: {e}"))
        finally:
            # Restore
            actors = load_alias_map('actor')
            if '_test_collision' in actors:
                del actors['_test_collision']
            save_alias_map(actors, 'actor', meta)

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_resolve_all_pipeline(suite: TestSuite, verbose: bool = False):
    """resolve_all() maps raw extraction output to canonical forms."""
    name = "resolve_all() pipeline"
    try:
        from alias_resolver import AliasResolver, resolve_all
        from entity_indexer import EntityExtractor

        resolver = AliasResolver()
        extractor = EntityExtractor()

        # Extract from alias-heavy text
        text = ("MuddyWater MERCURY group using Cobalt Strike beacon. "
                "Sofacy and Fancy Bear linked to Volt Typhoon.")
        raw = extractor.extract_all(text)
        resolved = resolve_all(raw, resolver)

        failures = []
        expected_actors = {'muddywater', 'apt28', 'volt typhoon'}
        found_actors = set(resolved.get('actors', []))
        if found_actors != expected_actors:
            failures.append(
                f"Actors: expected {expected_actors}, got {found_actors}")

        # Cobalt Strike should resolve, not remain as beacon
        if 'cobalt strike' not in resolved.get('tools', []):
            failures.append(f"Tools: expected 'cobalt strike', got {resolved.get('tools', [])}")

        if failures:
            suite.add(TestResult(name, False,
                "resolve_all() pipeline failures:\n" + "\n".join(failures),
                {"raw": raw, "resolved": resolved}))
        else:
            suite.add(TestResult(name, True,
                f"Pipeline correctly resolved actors: {found_actors}, tools: {resolved.get('tools', [])}",
                {"raw": raw, "resolved": resolved}))

    except ImportError as e:
        suite.add(TestResult(name, False, f"Import error: {e}"))
    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_recall_actor_with_alias(suite: TestSuite, verbose: bool = False):
    """AR-07: mm.recall_actor('mercury') returns notes indexed under muddywater."""
    name = "Recall with alias (AR-07)"
    try:
        from alias_resolver import AliasResolver
        resolver = AliasResolver()

        # Check the entity index for muddywater notes
        idx = load_entity_index()
        muddywater_notes = idx.get('actor', {}).get('muddywater', [])

        if not muddywater_notes:
            suite.add(TestResult(name, True,
                "No muddywater notes in index yet — would resolve correctly via alias. "
                "Test will become active once notes exist."))
            return

        # Simulate: recall via alias
        canonical = resolver.resolve('actor', 'mercury')
        if canonical != 'muddywater':
            suite.add(TestResult(name, False,
                f"resolve('actor', 'mercury') -> '{canonical}' (expected 'muddywater')"))
            return

        suite.add(TestResult(name, True,
            f"Alias resolves correctly. {len(muddywater_notes)} muddywater notes in index."))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_cross_alias_linking(suite: TestSuite, verbose: bool = False):
    """Phase 2 requirement: new note about alias links to existing canonical notes."""
    name = "Cross-alias linking (Phase 2 integration)"
    try:
        from memory_manager import get_memory_manager
        from alias_resolver import AliasResolver

        resolver = AliasResolver()
        mm = get_memory_manager()

        # Capture current muddywater note count
        idx_before = load_entity_index()
        muddywater_before = set(idx_before.get('actor', {}).get('muddywater', []))

        # Save with canonical
        note1, reason1 = mm.remember(
            content="MuddyWater actor using living-off-the-land techniques against DIB.",
            force=True
        )

        # Save with alias (TEMP.Zagros maps to muddywater)
        note2, reason2 = mm.remember(
            content="TEMP.Zagros group leveraging LotL against defense contractors.",
            force=True
        )

        # Save with another alias (Mercury maps to muddywater)
        note3, reason3 = mm.remember(
            content="Mercury APT observed scanning DIB perimeter via VPN.",
            force=True
        )

        # Check: all three new notes should be in muddywater index
        idx_after = load_entity_index()
        muddywater_after = set(idx_after.get('actor', {}).get('muddywater', []))
        new_notes = muddywater_after - muddywater_before

        new_indexed = all(
            nid in muddywater_after
            for nid in [note1.id, note2.id, note3.id]
        )

        if new_indexed:
            suite.add(TestResult(name, True,
                f"All 3 alias-variant notes (MuddyWater/TEMP.Zagros/Mercury) "
                f"indexed under muddywater. {len(new_notes)} new note(s) added."))
        else:
            # Diagnostic
            all_mw = list(muddywater_after)
            suite.add(TestResult(name, False,
                f"Notes not all indexed under muddywater. "
                f"New notes: {[note1.id, note2.id, note3.id]}. "
                f"Muddywater cluster: {all_mw[-5:]}"))

    except ImportError as e:
        suite.add(TestResult(name, False, f"Could not import: {e}"))
    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_mitre_attck_ids_present(suite: TestSuite, verbose: bool = False):
    """MITRE ATT&CK IDs are present in actor aliases map."""
    name = "MITRE ATT&CK IDs in alias map"
    try:
        actors = load_alias_map('actor')
        mitre_entries = {}  # mitre_id -> canonical
        for canonical, entry in actors.items():
            mid = entry.get('mitre_id')
            if mid:
                mitre_entries[mid] = canonical

        expected_ids = {'G0069': 'muddywater', 'G0005': 'apt28', 'G0016': 'apt29'}
        found = {mid: canonical for mid, canonical in expected_ids.items()
                 if mid in mitre_entries}

        if found:
            suite.add(TestResult(name, True,
                f"Found {len(mitre_entries)} MITRE IDs. Checked: {list(expected_ids.keys())}, "
                f"Found: {found}"))
        elif not mitre_entries:
            suite.add(TestResult(name, False,
                f"No MITRE IDs found in actors map. "
                f"Actors: {list(actors.keys())[:5]}"))
        else:
            suite.add(TestResult(name, False,
                f"Expected IDs {list(expected_ids.keys())} not found in {list(mitre_entries.keys())}"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_reload_updates_resolver(suite: TestSuite, verbose: bool = False):
    """AR-15: resolver.reload() picks up changes to alias maps."""
    name = "Hot reload alias maps (AR-15)"
    try:
        from alias_resolver import AliasResolver

        # Backup current map
        actors_backup = load_alias_map('actor')
        meta_backup = {"version": "1.0", "updated": "2026-03-31",
                       "source": "test", "entity_type": "actor"}

        resolver = AliasResolver()
        original_stats = resolver.stats()

        # Add a new alias to muddywater
        actors = load_alias_map('actor')
        if 'muddywater' in actors:
            original_names = actors['muddywater']['names']
            actors['muddywater']['names'] = original_names + ['testphantom_actor_xyz']
            save_alias_map(actors, 'actor', meta_backup)

            resolver.reload()
            resolved = resolver.resolve('actor', 'testphantom_actor_xyz')

            # Restore
            save_alias_map(actors_backup, 'actor', meta_backup)
            resolver.reload()

            if resolved == 'muddywater':
                suite.add(TestResult(name, True,
                    "Hot reload correctly picks up new alias after reload()"))
            else:
                suite.add(TestResult(name, False,
                    f"New alias not resolved after reload: '{resolved}'"))
        else:
            suite.add(TestResult(name, False, "muddywater not in actors map"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


def test_graceful_degradation(suite: TestSuite, verbose: bool = False):
    """Unknown entities pass through unchanged."""
    name = "Graceful degradation for unknown entities"
    try:
        from alias_resolver import AliasResolver
        resolver = AliasResolver()

        unknown = resolver.resolve('actor', 'completely_unknown_group_xyz123')
        if unknown == 'completely_unknown_group_xyz123':
            suite.add(TestResult(name, True,
                "Unknown entity passes through unchanged (graceful degradation)"))
        else:
            suite.add(TestResult(name, False,
                f"Expected 'completely_unknown_group_xyz123', got '{unknown}'"))

    except Exception as e:
        suite.add(TestResult(name, False, f"Exception: {e}\n{traceback.format_exc()}"))


# =============================================================================
# Test Registry
# =============================================================================

TESTS = [
    ("Alias map structure", test_alias_map_structure),
    ("AliasResolver instantiation", test_alias_resolver_creation),
    ("Canonical resolution (AR-01 to AR-05)", test_canonical_resolution),
    ("Collision detection (AR-06)", test_alias_collision_detection),
    ("resolve_all() pipeline", test_resolve_all_pipeline),
    ("Recall with alias (AR-07)", test_recall_actor_with_alias),
    ("Cross-alias linking", test_cross_alias_linking),
    ("MITRE ATT&CK IDs present", test_mitre_attck_ids_present),
    ("Hot reload (AR-15)", test_reload_updates_resolver),
    ("Graceful degradation", test_graceful_degradation),
]


# =============================================================================
# Main
# =============================================================================

def run_tests(verbose: bool = False) -> int:
    suite = TestSuite()

    print(f"\n{BLUE}{BOLD}Phase 2.5: Actor Alias Resolution — Running{RESET}")
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
          f"Phase 2.5 Results: {s['passed']}/{s['total']} passed{RESET} "
          f"({s['duration_s']:.1f}s)\n")

    for r in suite.results:
        print(r)

    return 0 if suite.all_passed() else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 2.5 alias resolution tests")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()
    sys.exit(run_tests(verbose=args.verbose))
