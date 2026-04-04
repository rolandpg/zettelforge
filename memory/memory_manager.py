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
from alias_resolver import AliasResolver, resolve_all
from alias_manager import AliasManager, get_alias_manager
from reasoning_logger import ReasoningLogger, get_reasoning_logger

# Try to import synthesis modules from memory/ subdirectory
try:
    from memory.synthesis_generator import get_synthesis_generator, SynthesisGenerator
    from memory.synthesis_retriever import get_synthesis_retriever, SynthesisRetriever
    from memory.synthesis_validator import get_synthesis_validator, SynthesisValidator
except ImportError:
    # Fallback to root directory if memory/ not available
    try:
        from synthesis_generator import get_synthesis_generator, SynthesisGenerator
        from synthesis_retriever import get_synthesis_retriever, SynthesisRetriever
        from synthesis_validator import get_synthesis_validator, SynthesisValidator
    except ImportError:
        # Synthesis modules not available
        SynthesisGenerator = None
        SynthesisRetriever = None
        SynthesisValidator = None
        get_synthesis_generator = lambda: None
        get_synthesis_retriever = lambda: None
        get_synthesis_validator = lambda: None


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

        # Alias resolution for actors/tools/campaigns
        self.resolver = AliasResolver()
        self.alias_manager: AliasManager = get_alias_manager()
        self.reasoning_logger: ReasoningLogger = get_reasoning_logger()

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

        # Entity index the new note (alias-resolved)
        raw_entities = self.indexer.extractor.extract_all(note.content.raw)
        resolved_entities = resolve_all(raw_entities, self.resolver)
        self.indexer.add_note_resolved(note.id, resolved_entities)

        # Track alias observations for Phase 3.5 auto-update
        self._track_alias_observations(note, resolved_entities)

        # Check for supersession: same alias match means new note supersedes old (Phase 3)
        superseded_note = self._check_supersession(note, resolved_entities)

        # Generate links
        candidates = [n for n in self.store.iterate_notes() if n.id != note.id]
        links = self.linker.generate_links(note, candidates)

        if links:
            note = self.linker.update_note_links(note, links, candidates)
            self.store._rewrite_note(note)
            self.stats['links_generated'] += len(links)
            self._log_link_reasoning(note, links)

        # Run evolution cycle
        if auto_evolve:
            self.memory_evolver.run_evolution_cycle(note)
            self.stats['evolutions_run'] += 1

        # Refresh in-memory snapshot for mid-session visibility (Phase 4)
        self.get_snapshot()

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
        Results sorted by created_at DESC (newest first) to prefer recent information.
        """
        self.stats['entity_index_hits'] += 1
        note_ids = self.indexer.get_note_ids(entity_type, entity_value.lower())
        notes = []
        for nid in note_ids:
            note = self.store.get_note_by_id(nid)
            if note:
                # Filter out superseded notes
                if exclude_superseded and note.links.superseded_by:
                    continue
                notes.append(note)
        # Sort by created_at DESC — newest first
        notes.sort(key=lambda n: n.created_at, reverse=True)
        return notes[:k]

    def recall_cve(self, cve_id: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by CVE-ID (case-insensitive)"""
        return self.recall_entity('cve', cve_id.upper(), k, exclude_superseded)

    def recall_actor(self, actor_name: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by threat actor name (alias-resolved)"""
        canonical = self.resolver.resolve('actor', actor_name)
        return self.recall_entity('actor', canonical.lower(), k, exclude_superseded)

    def recall_tool(self, tool_name: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by tool/campaign name (alias-resolved)"""
        canonical = self.resolver.resolve('tool', tool_name)
        return self.recall_entity('tool', canonical.lower(), k, exclude_superseded)

    def recall_campaign(self, campaign_name: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by campaign name (alias-resolved)"""
        canonical = self.resolver.resolve('campaign', campaign_name)
        return self.recall_entity('campaign', canonical.lower(), k, exclude_superseded)

    def recall_sector(self, sector: str, k: int = 5, exclude_superseded: bool = True) -> List[MemoryNote]:
        """Fast lookup by sector tag"""
        return self.recall_entity('sector', sector.lower(), k, exclude_superseded)

    def mark_note_superseded(self, note_id: str, superseded_by_id: str) -> bool:
        """
        Mark a note as superseded by a newer note.
        Updates BOTH notes:
          - The old note gets superseded_by set
          - The new note gets supersedes appended
        Returns True if successful, False if either note not found.
        """
        old_note = self.store.get_note_by_id(note_id)
        new_note = self.store.get_note_by_id(superseded_by_id)
        if not old_note:
            return False
        if not new_note:
            return False

        # Update the old note
        old_note.links.superseded_by = superseded_by_id

        # Update the new note: add old note to its supersedes list
        if note_id not in old_note.links.supersedes:
            # Prevent circular refs
            if note_id != superseded_by_id:
                old_note.links.supersedes.append(superseded_by_id)

        if note_id not in new_note.links.supersedes:
            new_note.links.supersedes.append(note_id)

        self.store._rewrite_note(old_note)
        self.store._rewrite_note(new_note)
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

    # === Synthesis Layer (Phase 7) ===

    def synthesize(
        self,
        query: str,
        format: str = "direct_answer",
        k: int = 15,
        include_graph: bool = True,
        tier_filter: List[str] = None
    ) -> Dict:
        """
        Synthesize an answer using RAG-as-answer approach.
        Combines vector search, knowledge graph traversal, and LLM generation.

        Args:
            query: User query to answer
            format: Response format (direct_answer, synthesized_brief, timeline_analysis, relationship_map)
            k: Number of notes to retrieve
            include_graph: Whether to include knowledge graph context
            tier_filter: Tier filter for notes (A, B, C) - defaults to ["A", "B"]

        Returns:
            Synthesis result dictionary with answer, sources, metadata
        """
        gen = get_synthesis_generator()
        return gen.synthesize(
            query=query,
            memory_manager=self,
            format=format,
            k=k,
            include_graph=include_graph,
            tier_filter=tier_filter or ["A", "B"]
        )

    def retrieve_synthesis_context(
        self,
        query: str,
        k: int = 15,
        tier_filter: List[str] = None,
        expand_graph: bool = True
    ) -> Dict:
        """
        Retrieve comprehensive context for synthesis (without LLM generation).
        Useful for debugging or manual synthesis.

        Args:
            query: Query for context retrieval
            k: Number of notes to retrieve
            tier_filter: Tier filter (A, B, C)
            expand_graph: Whether to expand via knowledge graph

        Returns:
            Context dictionary with notes, entities, relationships
        """
        retriever = get_synthesis_retriever()
        return retriever.retrieve_context(
            query=query,
            memory_manager=self,
            k=k,
            tier_filter=tier_filter or ["A", "B"],
            expand_graph=expand_graph
        )

    def validate_synthesis(self, response: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a synthesis response.

        Args:
            response: Synthesis response dictionary

        Returns:
            (is_valid: bool, errors: List[str])
        """
        validator = get_synthesis_validator()
        return validator.validate_response(response)

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

    # -----------------------------------------------------------------------
    # Phase 3.5: Alias observation tracking for auto-update
    # -----------------------------------------------------------------------

    def _track_alias_observations(
        self,
        note: MemoryNote,
        resolved_entities: Dict[str, List[str]]
    ) -> None:
        """
        Track alias observations for Phase 3.5 auto-linking.
        For each (canonical, alias) pair found in the note, record an observation.
        When a pair reaches 3 observations, the alias is auto-added to the alias map.
        """
        note_id = note.id
        for entity_type in ['actors', 'tools', 'campaigns']:
            entities = resolved_entities.get(entity_type, [])
            et_key = entity_type.rstrip('s')
            for entity in entities:
                try:
                    canonical = self.resolver.resolve(et_key, entity)
                    if canonical != entity.lower():
                        self.alias_manager.observe(et_key, canonical, entity, note_id)
                except Exception:
                    pass

    # -----------------------------------------------------------------------
    # Phase 3: Supersession detection and marking
    # -----------------------------------------------------------------------

    def _check_supersession(
        self,
        new_note: MemoryNote,
        resolved_entities: Dict[str, List[str]]
    ) -> Optional[MemoryNote]:
        """
        Detect if new_note supersedes an existing note.
        Phase 3 rule: same canonical entity + newer timestamp = supersession.
        Does NOT delete the old note — marks it superseded.
        """
        from datetime import datetime
        candidates = [n for n in self.store.iterate_notes() if n.id != new_note.id]
        if not candidates:
            return None
        new_entities: Dict[str, List[str]] = {
            k: resolved_entities.get(k, []) for k in ['cves', 'actors', 'tools', 'campaigns']
        }
        best_match: Optional[MemoryNote] = None
        best_score = 0.0
        for candidate in candidates:
            if candidate.links.superseded_by:
                continue
            cand_entities = self.indexer.extractor.extract_all(candidate.content.raw)
            cand_resolved = resolve_all(cand_entities, self.resolver)
            overlap = 0
            for key in ['cves', 'actors', 'tools', 'campaigns']:
                new_set = set(e.lower() for e in new_entities.get(key, []))
                cand_set = set(e.lower() for e in cand_resolved.get(key, []))
                overlap += len(new_set & cand_set)
            if overlap == 0:
                continue
            score = float(overlap)
            try:
                new_ts = datetime.fromisoformat(new_note.created_at)
                cand_ts = datetime.fromisoformat(candidate.created_at)
                age_diff_hours = (new_ts - cand_ts).total_seconds() / 3600
                if age_diff_hours > 0:
                    score += min(age_diff_hours / 24, 1.0)
            except Exception:
                pass
            if score > best_score:
                best_score = score
                best_match = candidate
        if best_match and best_score >= 2.0:
            self.mark_note_superseded(best_match.id, new_note.id)
            try:
                self.reasoning_logger.log_evolution(
                    note_id=new_note.id, decision="SUPERSEDE",
                    reason=f"Supersedes {best_match.id} ({best_score:.1f} shared entities)",
                    tier=new_note.metadata.tier, superseded_note_id=best_match.id,
                    extra={'supersedes_note_id': best_match.id, 'overlap_score': best_score}
                )
                self.reasoning_logger.log_link(
                    from_note=new_note.id, to_note=best_match.id,
                    relationship="SUPERSEDES",
                    reason="Newer note on same entity supersedes older",
                    tier=new_note.metadata.tier
                )
            except Exception:
                pass
            return best_match
        return None

    # -----------------------------------------------------------------------
    # Phase 5.5: Link reasoning — log why links are created
    # -----------------------------------------------------------------------

    def _log_link_reasoning(
        self,
        new_note: MemoryNote,
        links: List[Dict]
    ) -> None:
        """Log reasoning behind each link created (Phase 5.5)."""
        try:
            for link in links:
                self.reasoning_logger.log_link(
                    from_note=new_note.id,
                    to_note=link['target_id'],
                    relationship=link.get('relationship', 'RELATED'),
                    reason=link.get('reason', 'Entity overlap + vector similarity'),
                    tier=new_note.metadata.tier
                )
        except Exception:
            pass

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
