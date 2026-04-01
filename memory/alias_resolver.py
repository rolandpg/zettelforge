"""
Alias Resolver — Canonical Name Resolution for Threat Actor Alias Maps
======================================================================

Loads alias maps from memory/alias_maps/*.json.
Builds reverse lookup dictionaries at init.
Resolves raw entity strings to canonical names.

Usage:
    resolver = AliasResolver()
    canonical = resolver.resolve('actor', 'mercury')  # -> 'muddywater'
    all_aliases = resolver.get_all_aliases('actor', 'muddywater')  # full list
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
ALIAS_MAP_DIR = MEMORY_DIR / "alias_maps"


class AliasResolver:
    def __init__(self, alias_map_dir: str = None):
        self.alias_map_dir = Path(alias_map_dir) if alias_map_dir else ALIAS_MAP_DIR
        self._maps: Dict[str, dict] = {}
        self._reverse: Dict[str, Dict[str, str]] = {}  # entity_type -> alias -> canonical
        self._meta: Dict[str, dict] = {}
        self._entity_types = ['actor', 'tool', 'campaign']
        self._load_all()

    def _load_all(self):
        """Load all alias map files and build reverse lookup tables."""
        self._maps = {}
        self._reverse = {}
        self._meta = {}
        self._collisions: Dict[str, List[str]] = {}

        for entity_type in self._entity_types:
            map_file = self.alias_map_dir / f"{entity_type}s.json"
            # Pluralize: actors.json, tools.json, campaigns.json

            if not map_file.exists():
                # Try singular
                map_file = self.alias_map_dir / f"{entity_type}.json"

            if map_file.exists():
                with open(map_file) as f:
                    data = json.load(f)

                meta = data.pop('_meta', {})
                aliases = data.pop('aliases', {})  # Extract the aliases dict
                self._meta[entity_type] = meta
                self._maps[entity_type] = aliases

                # Build reverse map and check collisions
                self._reverse[entity_type] = {}
                seen_aliases: Dict[str, List[str]] = {}  # alias -> [canonical_names]

                for canonical, entry in aliases.items():
                    aliases_list = entry.get('names', [])
                    # Deduplicate aliases list
                    aliases_list = list(dict.fromkeys(a.lower().strip() for a in aliases_list))

                    for alias_key in aliases_list:
                        if alias_key in seen_aliases:
                            seen_aliases[alias_key].append(canonical)
                        else:
                            seen_aliases[alias_key] = [canonical]

                # Detect collisions (same alias claimed by multiple canonicals)
                self._collisions[entity_type] = {}
                for alias_key, canonicals in seen_aliases.items():
                    if len(canonicals) > 1:
                        self._collisions[entity_type][alias_key] = canonicals
                        self._reverse[entity_type][alias_key] = canonicals[0]

                # Build non-colliding reverse map (only unambiguous aliases)
                for alias_key, canonicals in seen_aliases.items():
                    if len(canonicals) == 1:
                        self._reverse[entity_type][alias_key] = canonicals[0]

        # Raise on any collisions
        all_collisions = {k: v for k, v in self._collisions.items() if v}
        if all_collisions:
            collision_report = []
            for et, collisions in all_collisions.items():
                for alias, canonicals in collisions.items():
                    collision_report.append(
                        f"  [{et}] '{alias}' claimed by: {canonicals}"
                    )
            raise ValueError(
                f"Alias map collision(s) detected — must be resolved before load:\n"
                + "\n".join(collision_report)
            )

    def resolve(self, entity_type: str, raw_name: str) -> str:
        """
        Resolve a raw entity name to its canonical form.

        Returns canonical name if mapping exists.
        Returns raw_name.lower().strip() if no mapping exists (graceful degradation).
        """
        if entity_type not in self._reverse:
            return raw_name.lower().strip()

        key = raw_name.lower().strip()
        if key in self._reverse[entity_type]:
            return self._reverse[entity_type][key]
        return key

    def get_canonical(self, entity_type: str, raw_name: str) -> Optional[str]:
        """
        Like resolve(), but returns None instead of raw_name when no mapping exists.
        Distinguishes 'no mapping' from 'mapped to self'.
        """
        if entity_type not in self._reverse:
            return None

        key = raw_name.lower().strip()
        if key in self._reverse[entity_type]:
            return self._reverse[entity_type][key]
        return None

    def get_all_aliases(self, entity_type: str, canonical: str) -> List[str]:
        """Return the full alias list for a canonical name."""
        if entity_type not in self._maps:
            return []

        entry = self._maps[entity_type].get(canonical, {})
        return entry.get('names', [])

    def get_mitre_id(self, entity_type: str, canonical: str) -> Optional[str]:
        """Return the MITRE ATT&CK ID for a canonical entity, if known."""
        if entity_type not in self._maps:
            return None

        entry = self._maps[entity_type].get(canonical, {})
        return entry.get('mitre_id')

    def reload(self):
        """Re-read alias map files from disk. Call after manual map updates."""
        self._load_all()

    def stats(self) -> dict:
        """Return coverage statistics for loaded alias maps."""
        stats = {}
        for entity_type in self._entity_types:
            if entity_type in self._maps:
                canonical_count = len(self._maps[entity_type])
                alias_count = sum(
                    len(entry.get('names', []))
                    for entry in self._maps[entity_type].values()
                )
                stats[entity_type] = {
                    'canonical_count': canonical_count,
                    'alias_count': alias_count,
                    'meta': self._meta.get(entity_type, {})
                }
            else:
                stats[entity_type] = {
                    'canonical_count': 0,
                    'alias_count': 0,
                    'meta': {}
                }
        return stats


# =============================================================================
# resolve_all() — Pipeline Integration Function
# =============================================================================

def resolve_all(extracted: Dict[str, List[str]], resolver: AliasResolver) -> Dict[str, List[str]]:
    """
    Resolve raw extracted entities to canonical names.

    Sits between extract_all() and index update in mm.remember().

    Args:
        extracted: Dict with keys 'cves', 'actors', 'tools', 'campaigns', 'sectors'
                   each containing a list of raw entity strings.
        resolver: AliasResolver instance.

    Returns:
        Dict with same structure but entity names resolved to canonical forms.
        Unrecognized entities pass through unchanged.
        CVEs pass through unchanged (no alias map for CVEs).

    Example:
        raw = {'cves': ['CVE-2024-3094'], 'actors': ['mercury'], 'tools': [], ...}
        resolved = resolve_all(raw, resolver)
        # -> {'cves': ['CVE-2024-3094'], 'actors': ['muddywater'], 'tools': [], ...}
    """
    resolved = {}

    # CVEs: no resolution needed (already canonical by design)
    resolved['cves'] = extracted.get('cves', [])

    # Sectors: keyword categories, no alias resolution
    resolved['sectors'] = extracted.get('sectors', [])

    # Actors: resolve through alias map
    raw_actors = extracted.get('actors', [])
    canonical_actors = []
    seen = set()
    for actor in raw_actors:
        canonical = resolver.resolve('actor', actor)
        if canonical not in seen:
            seen.add(canonical)
            canonical_actors.append(canonical)
    resolved['actors'] = canonical_actors

    # Tools: resolve through alias map
    raw_tools = extracted.get('tools', [])
    canonical_tools = []
    seen = set()
    for tool in raw_tools:
        canonical = resolver.resolve('tool', tool)
        if canonical not in seen:
            seen.add(canonical)
            canonical_tools.append(canonical)
    resolved['tools'] = canonical_tools

    # Campaigns: resolve through alias map
    raw_campaigns = extracted.get('campaigns', [])
    canonical_campaigns = []
    seen = set()
    for campaign in raw_campaigns:
        canonical = resolver.resolve('campaign', campaign)
        if canonical not in seen:
            seen.add(canonical)
            canonical_campaigns.append(canonical)
    resolved['campaigns'] = canonical_campaigns

    return resolved


# =============================================================================
# CLI / Quick Test
# =============================================================================

if __name__ == "__main__":
    resolver = AliasResolver()

    print(f"\nAliasResolver stats: {resolver.stats()}\n")

    # AR-01 through AR-05 quick checks
    cases = [
        ('actor', 'mercury', 'muddywater'),
        ('actor', 'muddywater', 'muddywater'),
        ('actor', 'Sofacy', 'apt28'),
        ('actor', 'Fancy Bear', 'apt28'),
        ('actor', 'unknown_actor', 'unknown_actor'),
        ('tool', 'cs beacon', 'cobalt strike'),
        ('tool', 'beacon', 'cobalt strike'),
        ('cve', 'CVE-2024-3094', 'CVE-2024-3094'),
    ]

    passed = failed = 0
    for et, raw, expected in cases:
        result = resolver.resolve(et, raw)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] resolve('{et}', '{raw}') -> '{result}' (expected '{expected}')")

    print(f"\n{passed}/{passed+failed} resolution checks passed")
