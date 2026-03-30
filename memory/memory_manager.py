"""
Memory Manager - Primary Agent Interface
Roland Fleet Agentic Memory Architecture V1.0

Provides the main interface for the primary agent to interact with the memory system.
Implements retrieval, note construction, link generation, and evolution cycles.
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from note_schema import MemoryNote
from memory_store import MemoryStore
from note_constructor import NoteConstructor
from link_generator import LinkGenerator
from memory_evolver import MemoryEvolver, EvolutionDecider
from vector_retriever import VectorRetriever


class MemoryManager:
    """
    Main interface for primary agent memory operations.
    Handles: retrieval, construction, linking, evolution, and context assembly.
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
        
        self.cold_path = cold_path
        
        # Stats
        self.stats = {
            'notes_created': 0,
            'links_generated': 0,
            'evolutions_run': 0,
            'retrievals': 0
        }
    
    def remember(
        self,
        content: str,
        source_type: str = "conversation",
        source_ref: str = "",
        domain: str = "general",
        auto_evolve: bool = True
    ) -> MemoryNote:
        """
        Create a new memory note from content.
        Runs construction → linking → evolution cycle.
        """
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
        
        return note
    
    def recall(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 10,
        include_links: bool = True
    ) -> List[MemoryNote]:
        """
        Retrieve memories relevant to query.
        """
        self.stats['retrievals'] += 1
        return self.retriever.retrieve(
            query=query,
            domain=domain,
            k=k,
            include_links=include_links
        )
    
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
    ) -> MemoryNote:
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
        return {
            **self.stats,
            'total_notes': self.store.count_notes(),
            'store_path': str(self.store.jsonl_path)
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
            'low_confidence_notes': []
        }
        
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
        from pathlib import Path
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
    import sys
    
    mm = get_memory_manager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "stats":
            print(json.dumps(mm.get_stats(), indent=2))
        
        elif command == "remember" and len(sys.argv) > 2:
            content = sys.argv[2]
            note = mm.remember(content)
            print(f"Created: {note.id}")
        
        elif command == "recall" and len(sys.argv) > 2:
            query = sys.argv[2]
            results = mm.recall(query)
            print(f"Found {len(results)} notes:")
            for r in results:
                print(f"  - {r.id}: {r.semantic.context[:60]}")
        
        elif command == "context" and len(sys.argv) > 2:
            query = sys.argv[2]
            print(mm.get_context(query))
        
        elif command == "maintenance":
            print("Daily:", json.dumps(mm.daily_maintenance(), indent=2))
            print("Weekly:", json.dumps(mm.weekly_maintenance(), indent=2))
        
        elif command == "snapshot":
            print(f"Snapshot: {mm.snapshot()}")
        
        else:
            print("Commands: stats, remember <content>, recall <query>, context <query>, maintenance, snapshot")
    else:
        print(json.dumps(mm.get_stats(), indent=2))
