"""
Memory Manager - Primary Agent Interface
Roland Fleet Agentic Memory Architecture V1.0

Provides the main interface for the primary agent to interact with the memory system.
Implements retrieval, note construction, linking, evolution, entity indexing, and deduplication.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

# Add memory/ to path for local imports
_memory_dir = Path('/home/rolandpg/.openclaw/workspace/memory')
if str(_memory_dir) not in sys.path:
    sys.path.insert(0, str(_memory_dir))

from note_schema import MemoryNote
from memory_store import MemoryStore
from note_constructor import NoteConstructor
from link_generator import LinkGenerator
from memory_evolver import MemoryEvolver, EvolutionDecider
from vector_retriever import VectorRetriever
from entity_indexer import EntityIndexer, Deduplicator


class MemoryManager:
    """
    Main interface for primary agent memory operations.
    Handles: retrieval, construction, linking, evolution, entity indexing, deduplication.
    """

    def __init__(
        self,
        jsonl_path: str = "/home/rolandpg/.openclaw/workspace/memory/notes.jsonl",
        lance_path: str = "/home/rolandpg/.openclaw/workspace/vectordb/",
        cold_path: str = "/media/rolandpg/USB-HDD"
    ):
        # Initialize components
        self.store = MemoryStore(jsonl_path=jsonl_path, lance_path=lance_path)
        self.constructor = NoteConstructor()
        self.linker = LinkGenerator()
        self.evolver = EvolutionDecider()
        self.memory_evolver = MemoryEvolver(self.store, self.evolver)
        self.retriever = VectorRetriever()

        # Entity indexing + deduplication
        self.indexer = EntityIndexer()
        self.indexer.load()
        self.dedup = Deduplicator(self.indexer)

        self.cold_path = cold_path

        # Stats
        self.stats = {
            'notes_created': 0,
            'duplicates_skipped': 0,
            'links_generated': 0,
            'evolutions_run': 0,
            'retrievals': 0,
            'entity_index_hits': 0
        }

    def remember(
        self,
        content: str,
        source_type: str = "conversation",
        source_ref: str = "",
        domain: str = "general",
        auto_evolve: bool = True,
        force: bool = False
    ) -> Tuple[Optional[MemoryNote], str]:
        """
        Create a new memory note from content.
        Runs deduplication check → construction → entity index → linking → evolution.

        Returns: (note or None, reason)
            - (note, "created") if new note saved
            - (existing_note, "duplicate_skipped") if duplicate found
            - (note, "similar_skipped") if similar note found above threshold
        """
        # Deduplication check
        if not force:
            is_dup, dup_reason, existing_id = self.dedup.check_duplicate(content, domain)
            if is_dup:
                self.stats['duplicates_skipped'] += 1
                self._log_dedup(content, dup_reason, existing_id, "skipped")
                # Return the existing note
                existing = self.store.get_note_by_id(existing_id)
                return existing, f"duplicate_skipped:{dup_reason}"

            # Similarity check
            similar = self.dedup.find_similar(content)
            if similar:
                sim_id, sim_score, sim_ctx = similar[0]
                self._log_dedup(content, f"similar:{sim_score:.2f}", sim_id, "similar")
                # For now, still save but log it
                # TODO: decide: skip or warn

        # Construct note
        note = self.constructor.enrich(
            raw_content=content,
            source_type=source_type,
            source_ref=source_ref,
            domain=domain
        )

        # Write to store
        self.store.write_note(note)
        self.stats['notes_created'] += 1

        # Entity index the new note
        self.indexer.add_note(note.id, note.content.raw)

        # Generate links
        candidates = [n for n in self.store.iterate_notes() if n.id != note.id]
        links = self.linker.generate_links(note, candidates)

        if links:
            note = self.linker.update_note_links(note, links, candidates)
            self.store._rewrite_note(note)
            self.stats['links_generated'] += len(links)

        # Run evolution cycle
        if auto_evolve:
            self.memory_evolver.run_evolution_cycle(note)
            self.stats['evolutions_run'] += 1

        return note, "created"

    def recall(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 10,
        include_links: bool = True,
        exclude_superseded: bool = True
    ) -> List[MemoryNote]:
        """
        Retrieve memories relevant to query.
        exclude_superseded: Filter out notes that have been superseded by newer notes
        """
        self.stats['retrievals'] += 1
        results = self.retriever.retrieve(
            query=query,
            domain=domain,
            k=k,
            include_links=include_links
        )

        # Filter out superseded notes
        if exclude_superseded:
            results = [note for note in results if not note.links.superseded_by]

        return results

    # === Entity Index Accessors ===

    def recall_entity(
        self,
        entity_type: str,
        entity_value: str,
        k: int = 5,
        exclude_superseded: bool = True
    ) -> List[MemoryNote]:
        """
        Fast lookup by entity type and value.
        entity_type: 'cve', 'actor', 'tool', 'campaign', 'sector'
        exclude_superseded: Filter out notes that have been superseded by newer notes
        """
        self.stats['entity_index_hits'] += 1
        note_ids = self.indexer.get_note_ids(entity_type, entity_value.lower())
        notes = []
        for nid in note_ids[:k]:
            note = self.store.get_note_by_id(nid)
            if note:
                # Filter out superseded notes
                if exclude_superseded and note.links.superseded_by:
                    continue
                notes.append(note)
        return notes

    def recall_cve(self, cve_id: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by CVE-ID (case-insensitive)"""
        return self.recall_entity('cve', cve_id.upper(), k, exclude_superseded)

    def recall_actor(self, actor_name: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by threat actor name"""
        return self.recall_entity('actor', actor_name.lower(), k, exclude_superseded)

    def recall_tool(self, tool_name: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by tool/campaign name"""
        return self.recall_entity('tool', tool_name.lower(), k, exclude_superseded)

    def recall_campaign(self, campaign_name: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by campaign name"""
        return self.recall_entity('campaign', campaign_name.lower(), k, exclude_superseded)

    def recall_sector(self, sector: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by sector tag"""
        return self.recall_entity('sector', sector.lower(), k, exclude_superseded)

    def mark_note_superseded(self, note_id: str, superseded_by_id: str) -> bool:
        """
        Mark a note as superseded by a newer note.
        Returns True if successful, False if note not found.
        """
        note = self.store.get_note_by_id(note_id)
        if not note:
            return False

        note.links.superseded_by = superseded_by_id
        self.store.update_note(note)
        return True

    def get_superseded_notes(self) -> List[MemoryNote]:
        """Get all notes that have been superseded"""
        superseded = []
        for note in self.store.iterate_notes():
            if note.links.superseded_by:
                superseded.append(note)
        return superseded

    def get_snapshot(self) -> List[MemoryNote]:
        """
        Get current memory snapshot reflecting all notes including recent changes.
        This provides a mid-session refresh capability.
        """
        return list(self.store.iterate_notes())

    def archive_low_confidence_notes(self, confidence_threshold: float = 0.3, dry_run: bool = False) -> Dict:
        """
        Archive notes with confidence < threshold and access_count == 0.
        Returns dict with archive results.
        """
        from pathlib import Path
        import json

        archive_dir = Path(f"{self.cold_path}/archive")
        archive_dir.mkdir(parents=True, exist_ok=True)

        results = {
            'archived_count': 0,
            'skipped_count': 0,
            'archived_ids': [],
            'errors': []
        }

        for note in self.store.iterate_notes():
            # Check archival criteria
            if (note.metadata.confidence >= confidence_threshold or
                note.metadata.access_count > 0):
                results['skipped_count'] += 1
                continue

            if dry_run:
                results['archived_ids'].append(note.id)
                results['archived_count'] += 1
                continue

            try:
                # Archive the note
                archive_file = archive_dir / f"{note.id}_v{note.version}.jsonl"
                with open(archive_file, 'w') as f:
                    f.write(note.model_dump_json() + '\n')

                # Remove from active store
                self.store.delete_note(note.id)

                results['archived_count'] += 1
                results['archived_ids'].append(note.id)

            except Exception as e:
                results['errors'].append({
                    'note_id': note.id,
                    'error': str(e)
                })

        return results

    def get_archived_notes(self) -> List[str]:
        """Get list of archived note IDs"""
        from pathlib import Path
        archive_dir = Path(f"{self.cold_path}/archive")
        if not archive_dir.exists():
            return []

        return [f.stem for f in archive_dir.glob("*.jsonl")]

    def get_entity_stats(self) -> Dict:
        """Entity index statistics"""
        self.indexer.load()
        return self.indexer.stats()

    def rebuild_entity_index(self) -> Dict:
        """Force rebuild of entity index from all notes"""
        return self.indexer.build()

    # === Context and Stats ===

    def get_context(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 10,
        token_budget: int = 4000
    ) -> str:
        """
        Get formatted memory context for agent prompt injection.
        """
        return self.retriever.get_memory_context(
            query=query,
            domain=domain,
            k=k,
            token_budget=token_budget
        )

    def get_subagent_context(
        self,
        task: str,
        domain: str,
        k: int = 5,
        token_budget: int = 2000
    ) -> str:
        """
        Get scoped memory context for subagent spawn.
        Limited to 5 notes and 2000 tokens for subagent context window.
        """
        return self.get_context(
            query=task,
            domain=domain,
            k=k,
            token_budget=token_budget
        )

    def ingest_subagent_output(
        self,
        task_id: str,
        output: str,
        observations: str = "",
        domain: str = "general"
    ) -> Tuple[Optional[MemoryNote], str]:
        """
        Ingest subagent output into memory system.
        Creates note from subagent results, triggers evolution.
        """
        # Combine output and observations
        content = f"""Subagent Task: {task_id}
Output: {output}
Observations: {observations}"""

        return self.remember(
            content=content,
            source_type="subagent_output",
            source_ref=f"subagent:{task_id}",
            domain=domain,
            auto_evolve=True
        )

    def get_stats(self) -> Dict:
        """Get memory system statistics"""
        entity_stats = self.indexer.stats() if self.indexer.load() else {}
        return {
            **self.stats,
            'total_notes': self.store.count_notes(),
            'store_path': str(self.store.jsonl_path),
            'entity_index': entity_stats
        }

    def snapshot(self) -> str:
        """Export memory snapshot to cold storage"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_dir = f"{self.cold_path}/snapshots"

        # Export JSONL
        self.store.export_snapshot(snapshot_dir)

        # Return snapshot info
        snapshot_file = f"{snapshot_dir}/notes_{timestamp}.jsonl"
        return snapshot_file

    def daily_maintenance(self) -> Dict:
        """Run daily maintenance tasks"""
        results = {
            'snapshot_created': False,
            'notes_count': 0,
            'low_confidence_notes': [],
            'entity_index_rebuilt': False
        }

        # Rebuild entity index daily
        idx_results = self.rebuild_entity_index()
        results['entity_index_rebuilt'] = True
        results['entity_index'] = idx_results

        # Snapshot
        snapshot_file = self.snapshot()
        results['snapshot_created'] = True
        results['notes_count'] = self.store.count_notes()

        # Find low confidence notes
        for note in self.store.iterate_notes():
            if note.metadata.confidence < 0.5:
                results['low_confidence_notes'].append({
                    'id': note.id,
                    'confidence': note.metadata.confidence,
                    'evolution_count': note.metadata.evolution_count
                })

        return results

    def weekly_maintenance(self) -> Dict:
        """Run weekly maintenance tasks"""
        results = {
            'reindex_needed': True,
            'archive_count': 0,
            'orphaned_links': []
        }

        # Count archives
        archive_dir = Path(f"{self.cold_path}/archive")
        if archive_dir.exists():
            results['archive_count'] = len(list(archive_dir.glob("*.jsonl")))

        # Check for orphaned links
        all_notes = list(self.store.iterate_notes())
        all_ids = {n.id for n in all_notes}

        for note in all_notes:
            for link_id in note.links.related:
                if link_id not in all_ids:
                    results['orphaned_links'].append({
                        'from': note.id,
                        'to': link_id
                    })

        return results

    def _log_dedup(
        self,
        content: str,
        reason: str,
        note_id: Optional[str],
        action: str
    ) -> None:
        """Log deduplication events"""
        log_path = Path("/home/rolandpg/.openclaw/workspace/memory/dedup_log.jsonl")
        entry = {
            'timestamp': datetime.now().isoformat(),
            'content_preview': content[:100],
            'reason': reason,
            'existing_note': note_id,
            'action': action
        }
        with open(log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


# CLI for testing
if __name__ == "__main__":
    import sys as _sys

    mm = get_memory_manager()

    if len(_sys.argv) > 1:
        command = _sys.argv[1]

        if command == "stats":
            print(json.dumps(mm.get_stats(), indent=2))

        elif command == "remember" and len(_sys.argv) > 2:
            content = ' '.join(_sys.argv[2:])
            note, reason = mm.remember(content)
            print(f"{reason}: {note.id if note else 'None'}")

        elif command == "recall" and len(_sys.argv) > 2:
            query = ' '.join(_sys.argv[2:])
            results = mm.recall(query)
            print(f"Found {len(results)} notes:")
            for r in results:
                print(f"  - {r.id}: {r.semantic.context[:60]}")

        elif command == "entity" and len(_sys.argv) > 3:
            etype = _sys.argv[2]
            evalue = ' '.join(_sys.argv[3:])
            notes = mm.recall_entity(etype, evalue)
            print(f"Entity {etype} '{evalue}': {len(notes)} notes")
            for n in notes:
                print(f"  - {n.id}: {n.semantic.context[:80]}")

        elif command == "cve" and len(_sys.argv) > 2:
            cve = _sys.argv[2]
            notes = mm.recall_cve(cve)
            print(f"CVE {cve}: {len(notes)} notes")
            for n in notes:
                print(f"  - {n.id}: {n.semantic.context[:80]}")

        elif command == "actor" and len(_sys.argv) > 2:
            actor = ' '.join(_sys.argv[2:])
            notes = mm.recall_actor(actor)
            print(f"Actor '{actor}': {len(notes)} notes")
            for n in notes:
                print(f"  - {n.id}: {n.semantic.context[:80]}")

        elif command == "context" and len(_sys.argv) > 2:
            query = ' '.join(_sys.argv[2:])
            print(mm.get_context(query))

        elif command == "maintenance":
            print("Daily:", json.dumps(mm.daily_maintenance(), indent=2))
            print("Weekly:", json.dumps(mm.weekly_maintenance(), indent=2))

        elif command == "snapshot":
            print(f"Snapshot: {mm.snapshot()}")

        elif command == "rebuild-index":
            print(json.dumps(mm.rebuild_entity_index(), indent=2))

        else:
            print("Commands: stats, remember <content>, recall <query>, "
                  "entity <type> <value>, cve <id>, actor <name>, "
                  "context <query>, maintenance, snapshot, rebuild-index")
    else:
        print(json.dumps(mm.get_stats(), indent=2))
