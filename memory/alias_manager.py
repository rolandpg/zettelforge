"""
Alias Manager — Phase 3.5: Auto-Update Alias Map from Observations
====================================================================

Tracks observation counts for (canonical_name, alias) pairs.
When count >= 3 for the same pair, auto-adds the alias to the canonical's alias list.
Persists observation counts to memory/alias_observations.json.

Usage:
    am = AliasManager()
    am.observe('actor', 'muddywater', 'mercury', note_id='note_xxx')
    # After 3+ observations of 'mercury' linked to 'muddywater', auto-adds alias
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
OBSERVATIONS_FILE = MEMORY_DIR / "alias_observations.json"
AUTO_THRESHOLD = 3  # Observations before auto-adding alias


class AliasManager:
    """
    Tracks alias observations and auto-updates alias maps.
    """

    def __init__(
        self,
        observations_file: str = None,
        alias_resolver=None,
        auto_threshold: int = None
    ):
        self.observations_file = Path(observations_file) if observations_file else OBSERVATIONS_FILE
        self.auto_threshold = auto_threshold if auto_threshold is not None else AUTO_THRESHOLD
        self.resolver = alias_resolver

        # observations[entity_type][canonical][alias] = [note_ids...]
        self.observations: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
        self._load()

    def _load(self) -> None:
        """Load observations from disk."""
        if not self.observations_file.exists():
            self.observations = {}
            return
        try:
            with open(self.observations_file) as f:
                self.observations = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.observations = {}

    def _save(self) -> None:
        """Persist observations to disk."""
        self.observations_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.observations_file, 'w') as f:
            json.dump(self.observations, f, indent=2)

    def observe(
        self,
        entity_type: str,
        canonical: str,
        alias: str,
        note_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Record an observation linking alias to canonical.

        If count reaches auto_threshold, auto-adds the alias to alias map.

        Returns: (was_auto_added, canonical_or_none)
            - (True, canonical) if alias was auto-added this call
            - (False, None) if not yet at threshold
            - (False, "already_known") if alias already in map
        """
        canonical_lower = canonical.lower().strip()
        alias_lower = alias.lower().strip()

        # Validate inputs
        if not canonical_lower or not alias_lower:
            return False, None
        if not note_id or len(str(note_id)) > 512:
            return False, None

        # Skip if alias is already a known alias for this canonical
        if self.resolver:
            all_aliases = self.resolver.get_all_aliases(entity_type, canonical_lower)
            if alias_lower in [a.lower() for a in all_aliases]:
                return False, "already_known"

        # Initialize nested dicts
        self.observations.setdefault(entity_type, {})
        self.observations[entity_type].setdefault(canonical_lower, {})
        self.observations[entity_type][canonical_lower].setdefault(alias_lower, [])

        # Add note_id if not already recorded
        if note_id not in self.observations[entity_type][canonical_lower][alias_lower]:
            self.observations[entity_type][canonical_lower][alias_lower].append(note_id)

        count = len(self.observations[entity_type][canonical_lower][alias_lower])

        # Auto-add if threshold reached
        if count >= self.auto_threshold:
            added = self._auto_add_alias(entity_type, canonical_lower, alias_lower)
            if added:
                # Clear observations for this pair after successful auto-add
                del self.observations[entity_type][canonical_lower][alias_lower]
                self._save()
                return True, canonical_lower
            # add_alias returned False — alias already exists or collision.
            # Do NOT save here; observations persist at count=N so caller can retry
            # or investigate. Prevents infinite retry loops when add_alias permanently fails.
            return False, None

        # Not yet at threshold — save observations normally
        self._save()
        return False, None

    def _auto_add_alias(
        self,
        entity_type: str,
        canonical: str,
        alias: str
    ) -> bool:
        """Add alias to the alias map via resolver. Creates canonical if needed."""
        if self.resolver is None:
            return False

        try:
            # Canonical might not exist yet — use add_canonical_with_alias to create it
            success = self.resolver.add_canonical_with_alias(entity_type, canonical, alias)
            # If canonical already existed, add_alias would have worked; fall back
            if not success:
                success = self.resolver.add_alias(entity_type, canonical, alias)
            return success
        except ValueError as e:
            # Alias collision — alias already maps to a different canonical
            # Log and continue; do not crash the observation pipeline
            import structlog
            logger = structlog.get_logger()
            logger.warning("alias_collision_detected", entity_type=entity_type,
                           canonical=canonical, alias=alias, error=str(e))
            return False

    def get_observation_count(
        self,
        entity_type: str,
        canonical: str,
        alias: str
    ) -> int:
        """Get current observation count for a (canonical, alias) pair."""
        try:
            return len(
                self.observations[entity_type][canonical.lower()][alias.lower()]
            )
        except KeyError:
            return 0

    def get_pending_aliases(self, entity_type: str = None) -> Dict:
        """
        Get all alias pairs that are pending (not yet auto-added).
        Optionally filter by entity_type.
        """
        result = {}
        types_to_check = [entity_type] if entity_type else self.observations.keys()

        for et in types_to_check:
            if et not in self.observations:
                continue
            result[et] = {}
            for canonical, aliases in self.observations[et].items():
                for alias, note_ids in aliases.items():
                    count = len(note_ids)
                    if count < self.auto_threshold:
                        result[et].setdefault(canonical, {})[alias] = {
                            'count': count,
                            'threshold': self.auto_threshold,
                            'remaining': self.auto_threshold - count,
                            'note_ids': note_ids
                        }
        return result

    def stats(self) -> Dict:
        """Return alias manager statistics."""
        total_observations = sum(
            len(notes)
            for canonicals in self.observations.values()
            for notes in canonicals.values()
        )
        return {
            'total_observations': total_observations,
            'auto_threshold': self.auto_threshold,
            'by_entity_type': {
                et: {
                    canonical: {
                        alias: len(note_ids)
                        for alias, note_ids in aliases.items()
                    }
                    for canonical, aliases in canonicals.items()
                }
                for et, canonicals in self.observations.items()
            },
            'pending_aliases': self.get_pending_aliases(),
            'observations_file': str(self.observations_file)
        }


# Thread-safe lazy initialization
_alias_manager: Optional['AliasManager'] = None
_alias_lock = threading.Lock()


def get_alias_manager() -> 'AliasManager':
    global _alias_manager
    if _alias_manager is None:
        with _alias_lock:
            # Double-check after acquiring lock
            if _alias_manager is None:
                from alias_resolver import AliasResolver
                resolver = AliasResolver()
                _alias_manager = AliasManager(alias_resolver=resolver)
    return _alias_manager
