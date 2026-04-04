"""
Reasoning Logger — A-MEM Audit Trail for Evolution and Link Decisions
=====================================================================

Logs every evolution decision and link creation to reasoning_log.jsonl.
Designed for debugging, explaining decisions, and learning from errors.

Phase 5.5 requirements:
  - Log every evolution decision: note_id, decision, reason, tier, timestamp
  - Log every link creation: from_note, to_note, relationship, reason, timestamp
  - mm.get_reasoning(note_id) returns reasoning entries for that note
  - Pruning: keep 180 days, archive older to cold storage
  - Reasoning entries are queryable by the agent during recall

PRD Section 9 Q6: Default 180 days, cold storage, admin-only update
PRD Section 9 Q7: Reasoning queryable by agent during recall to explain why a link exists
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any


class ReasoningLogger:
    """
    Append-only log of reasoning behind memory system decisions.
    File: memory/reasoning_log.jsonl
    """

    REASONING_LOG = Path("/home/rolandpg/.openclaw/workspace/memory/reasoning_log.jsonl")
    COLD_ARCHIVE = Path("/media/rolandpg/USB-HDD/archive")
    RETENTION_DAYS = 180

    # Valid decision types
    EVOLUTION_DECISIONS = {
        "NO_CHANGE", "UPDATE_CONTEXT", "UPDATE_TAGS",
        "UPDATE_BOTH", "SUPERSEDE", "REJECT"
    }
    LINK_RELATIONSHIPS = {
        "SUPPORTS", "CONTRADICTS", "EXTENDS", "CAUSES", "RELATED", "SUPERSEDES"
    }
    EVENT_TYPES = {
        "evolution_decision", "link_created", "tier_assignment", "alias_added"
    }

    # Valid tier values
    TIERS = {"A", "B", "C"}

    def __init__(self, log_path: str = None, cold_path: str = None):
        self.log_path = Path(log_path) if log_path else self.REASONING_LOG
        self.cold_path = Path(cold_path) if cold_path else self.COLD_ARCHIVE
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Logging methods
    # -------------------------------------------------------------------------

    def log_evolution(
        self,
        note_id: str,
        decision: str,
        reason: str,
        tier: str = "B",
        superseded_note_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an evolution decision.
        Called by MemoryEvolver when assessing whether to update/supersede a note.
        """
        if decision not in self.EVOLUTION_DECISIONS:
            raise ValueError(f"Invalid evolution decision: {decision}")
        if tier not in self.TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "evolution_decision",
            "note_id": note_id,
            "superseded_note_id": superseded_note_id,
            "decision": decision,
            "reason": str(reason)[:500],
            "tier": tier,
        }
        if extra:
            entry["extra"] = extra

        self._append(entry)

    def log_link(
        self,
        from_note: str,
        to_note: str,
        relationship: str,
        reason: str = "",
        tier: str = "B"
    ) -> None:
        """
        Log a link creation.
        Called by LinkGenerator when a new link is established.
        """
        if relationship not in self.LINK_RELATIONSHIPS:
            raise ValueError(f"Invalid link relationship: {relationship}")

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "link_created",
            "from_note": from_note,
            "to_note": to_note,
            "relationship": relationship,
            "reason": str(reason)[:500],
            "tier": tier,
        }
        self._append(entry)

    def log_tier_assignment(
        self,
        note_id: str,
        tier: str,
        source_type: str,
        auto: bool = True,
        override: bool = False
    ) -> None:
        """
        Log tier assignment when a note is saved.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "tier_assignment",
            "note_id": note_id,
            "tier": tier,
            "source_type": source_type,
            "auto": auto,
            "override": override,
        }
        self._append(entry)

    def log_alias_added(
        self,
        entity_type: str,
        canonical: str,
        alias: str,
        trigger_note_ids: List[str]
    ) -> None:
        """
        Log when a new alias is auto-added to the alias map.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "alias_added",
            "entity_type": entity_type,
            "canonical": canonical,
            "alias": alias,
            "trigger_note_ids": trigger_note_ids,
        }
        self._append(entry)

    def _append(self, entry: Dict) -> None:
        """Append a JSON line to the log file."""
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # -------------------------------------------------------------------------
    # Query methods
    # -------------------------------------------------------------------------

    def get_reasoning(self, note_id: str) -> List[Dict]:
        """
        Get all reasoning entries for a given note_id.
        Searches all event types where note_id appears.
        """
        entries = []
        if not self.log_path.exists():
            return entries

        with open(self.log_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    # Match any field containing this note_id
                    if (
                        entry.get("note_id") == note_id
                        or entry.get("superseded_note_id") == note_id
                        or entry.get("from_note") == note_id
                        or entry.get("to_note") == note_id
                    ):
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue

        return entries

    def get_recent(self, limit: int = 50) -> List[Dict]:
        """Get the N most recent reasoning entries."""
        entries = []
        if not self.log_path.exists():
            return entries

        with open(self.log_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return entries[:limit]

    def get_stats(self) -> Dict:
        """Return reasoning log statistics."""
        if not self.log_path.exists():
            return {
                "total_entries": 0,
                "by_event_type": {},
                "by_decision": {},
                "oldest_entry": None,
                "newest_entry": None,
                "log_path": str(self.log_path),
            }

        event_types: Dict[str, int] = {}
        decisions: Dict[str, int] = {}
        oldest = None
        newest = None

        with open(self.log_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    et = entry.get("event_type", "unknown")
                    event_types[et] = event_types.get(et, 0) + 1

                    if et == "evolution_decision":
                        d = entry.get("decision", "unknown")
                        decisions[d] = decisions.get(d, 0) + 1

                    ts = entry.get("timestamp", "")
                    if ts:
                        if oldest is None or ts < oldest:
                            oldest = ts
                        if newest is None or ts > newest:
                            newest = ts
                except json.JSONDecodeError:
                    continue

        return {
            "total_entries": sum(event_types.values()),
            "by_event_type": event_types,
            "by_decision": decisions,
            "oldest_entry": oldest,
            "newest_entry": newest,
            "log_path": str(self.log_path),
        }

    # -------------------------------------------------------------------------
    # Pruning (Phase 5.5)
    # -------------------------------------------------------------------------

    def prune_old_entries(self, retention_days: int = None) -> Dict:
        """
        Archive entries older than retention_days to cold storage.
        Returns dict with prune results.
        """
        if retention_days is None:
            retention_days = self.RETENTION_DAYS

        if not self.log_path.exists():
            return {"archived_count": 0, "deleted_count": 0, "errors": []}

        cutoff = datetime.now() - timedelta(days=retention_days)
        kept: List[Dict] = []
        archived_count = 0
        errors = []

        # Ensure cold archive dir exists
        self.cold_path.mkdir(parents=True, exist_ok=True)

        # Read all entries
        all_entries: List[Dict] = []
        with open(self.log_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        all_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # Split into kept vs archived
        for entry in all_entries:
            ts_str = entry.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts < cutoff:
                    # Archive it
                    archive_file = self.cold_path / f"reasoning_log_{ts_str[:10]}.jsonl"
                    with open(archive_file, "a") as f:
                        f.write(json.dumps(entry) + "\n")
                    archived_count += 1
                else:
                    kept.append(entry)
            except Exception as e:
                errors.append(f"Parse error on {ts_str}: {e}")
                kept.append(entry)  # Keep entries we can't parse

        # Rewrite kept entries
        with open(self.log_path, "w") as f:
            for entry in kept:
                f.write(json.dumps(entry) + "\n")

        return {
            "archived_count": archived_count,
            "deleted_count": len(all_entries) - len(kept),
            "kept_count": len(kept),
            "retention_days": retention_days,
            "cutoff": cutoff.isoformat(),
            "errors": errors,
        }


# Global instance
_reasoning_logger: Optional[ReasoningLogger] = None


def get_reasoning_logger() -> ReasoningLogger:
    global _reasoning_logger
    if _reasoning_logger is None:
        _reasoning_logger = ReasoningLogger()
    return _reasoning_logger
