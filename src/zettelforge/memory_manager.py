"""
Memory Manager - Primary Agent Interface
A-MEM Agentic Memory Architecture V1.0

Main interface for agent memory operations.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from zettelforge.note_schema import MemoryNote
from zettelforge.memory_store import MemoryStore, get_default_data_dir
from zettelforge.note_constructor import NoteConstructor
from zettelforge.entity_indexer import EntityIndexer
from zettelforge.vector_retriever import VectorRetriever
from zettelforge.alias_resolver import AliasResolver
from zettelforge.synthesis_generator import SynthesisGenerator, get_synthesis_generator
from zettelforge.synthesis_validator import SynthesisValidator, get_synthesis_validator
from zettelforge.prospective_indexer import generate_prospective_index, ProspectiveRetriever
from zettelforge.governance_validator import GovernanceValidator
from zettelforge.knowledge_graph import get_knowledge_graph


class MemoryManager:
    """
    Main interface for agent memory operations.
    """

    def __init__(
        self,
        jsonl_path: Optional[str] = None,
        lance_path: Optional[str] = None
    ):
        self.store = MemoryStore(jsonl_path=jsonl_path, lance_path=lance_path)
        self.constructor = NoteConstructor()
        self.indexer = EntityIndexer()
        self.retriever = VectorRetriever(memory_store=self.store)
        self.governance = GovernanceValidator()

        self.stats = {
            'notes_created': 0,
            'retrievals': 0,
            'entity_index_hits': 0
        }

    def remember(
        self,
        content: str,
        source_type: str = "conversation",
        source_ref: str = "",
        domain: str = "general"
    ) -> Tuple[MemoryNote, str]:
        """
        Create a new memory note from content.
        
        Returns: (note, status)
        """
        # Governance validation
        self.governance.enforce("remember", content)

        # Construct note
        note = self.constructor.construct(
            raw_content=content,
            source_type=source_type,
            source_ref=source_ref,
            domain=domain
        )

        # Write to store
        self.store.write_note(note)
        self.stats['notes_created'] += 1

        # Alias resolution and indexing
        self.resolver = getattr(self, "resolver", AliasResolver())
        raw_entities = self.indexer.extractor.extract_all(note.content.raw)
        
        resolved_entities = {}
        for etype, elist in raw_entities.items():
            resolved_entities[etype] = [self.resolver.resolve(etype, e) for e in elist]
            
        self.indexer.add_note(note.id, resolved_entities)
        
        # Phase 3: Check supersession
        self._check_supersession(note, resolved_entities)
        
        # Phase 6: Knowledge Graph Update
        self._update_knowledge_graph(note, resolved_entities)

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
        Uses intent classifier for adaptive retrieval strategy (Task 3).
        """
        self.stats['retrievals'] += 1

        # Classify query intent
        from zettelforge.intent_classifier import get_intent_classifier
        classifier = get_intent_classifier()
        intent, intent_meta = classifier.classify(query)
        policy = classifier.get_traversal_policy(intent)

        # Log for observability
        print(f"[Intent] {intent.value} (conf={intent_meta.get('confidence', 0):.2f}) for: {query[:50]}...")
        print(f"[Policy] vector={policy['vector']}, graph={policy['graph']}, temporal={policy['temporal']}")

        # Adjust k based on policy
        k = max(k, policy['top_k'])

        # Route based on intent
        if intent.value in ['factual', 'entity_lookup']:
            # Use entity index
            entities = self.indexer.extractor.extract_all(query)
            results = []
            for etype, elist in entities.items():
                for evalue in elist:
                    notes = self.recall_entity(etype, evalue, k=3)
                    results.extend(notes)
            # Fall back to vector retrieval if entity index returns nothing
            if not results:
                return self.retriever.retrieve(
                    query=query,
                    domain=domain,
                    k=k,
                    include_links=include_links
                )
            results = results[:k]
        elif intent.value == 'temporal':
            # Use temporal graph
            from zettelforge.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            changes = kg.get_changes_since('2020-01-01')  # TODO: parse from query
            note_ids = [c['to'].split(':')[-1] for c in changes if c['to'].startswith('note:')]
            results = [self.store.get_note_by_id(nid) for nid in note_ids if self.store.get_note_by_id(nid)]
            results = results[:k]
        elif intent.value in ['relational', 'causal']:
            # Use graph traversal
            from zettelforge.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            entities = self.indexer.extractor.extract_all(query)
            results = []
            for etype, elist in entities.items():
                for evalue in elist:
                    paths = kg.traverse(etype, evalue, max_depth=2)
                    for path in paths:
                        for step in path:
                            if step['to_type'] == 'note':
                                note = self.store.get_note_by_id(step['to_value'])
                                if note:
                                    results.append(note)
            results = results[:k]
        else:
            # Default: vector retrieval
            results = self.retriever.retrieve(
                query=query,
                domain=domain,
                k=k,
                include_links=include_links
            )

        # Prospective matching (Kumiho-style) for all query types
        if not hasattr(self, '_prospective_retriever'):
            self._prospective_retriever = ProspectiveRetriever(self.store)
        existing_ids = {n.id for n in results}
        prospective_hits = self._prospective_retriever.retrieve(
            query=query,
            note_lookup=lambda nid: self.store.get_note_by_id(nid),
            top_k=k,
        )
        for note, _ in prospective_hits:
            if note.id not in existing_ids:
                results.append(note)
                existing_ids.add(note.id)

        return results


    def recall_entity(
        self,
        entity_type: str,
        entity_value: str,
        k: int = 5
    ) -> List[MemoryNote]:
        """
        Fast lookup by entity type and value.
        entity_type: 'cve', 'actor', 'tool', 'campaign', 'sector'
        """
        self.stats['entity_index_hits'] += 1
        note_ids = self.indexer.get_note_ids(entity_type, entity_value.lower())
        notes = []
        for nid in note_ids[:k]:
            note = self.store.get_note_by_id(nid)
            if note:
                notes.append(note)
        return notes

    def recall_cve(self, cve_id: str, k: int = 5) -> List[MemoryNote]:
        """Fast lookup by CVE-ID (case-insensitive)"""
        return self.recall_entity('cve', cve_id.upper(), k)

    def recall_actor(self, actor_name: str, k: int = 5) -> List[MemoryNote]:
        """Fast lookup by threat actor name"""
        return self.recall_entity('actor', actor_name.lower(), k)

    def recall_tool(self, tool_name: str, k: int = 5) -> List[MemoryNote]:
        """Fast lookup by tool name"""
        return self.recall_entity('tool', tool_name.lower(), k)

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

    def get_stats(self) -> Dict:
        """Get memory system statistics"""
        return {
            **self.stats,
            'total_notes': self.store.count_notes(),
            'entity_index': self.indexer.stats()
        }




    def _update_knowledge_graph(self, note: MemoryNote, resolved_entities: Dict[str, List[str]]):
        kg = get_knowledge_graph()
        
        # 1. Add Note node
        note_id = kg.add_node("note", note.id, {"content": note.content.raw[:200], "domain": note.metadata.domain})
        
        # 2. Add Entity Nodes and MENTIONED_IN edges
        all_entities = []
        for etype, elist in resolved_entities.items():
            for evalue in elist:
                all_entities.append((etype, evalue))
                kg.add_edge(etype, evalue, "note", note.id, "MENTIONED_IN")

        # 3. Inferred Entity-to-Entity Relationships (Heuristic)
        # e.g., Actor uses Tool, Actor exploits CVE, Tool targets Asset
        actors = resolved_entities.get("actor", [])
        tools = resolved_entities.get("tool", [])
        cves = resolved_entities.get("cve", [])
        assets = resolved_entities.get("asset", [])
        campaigns = resolved_entities.get("campaign", [])

        # Actor -> Tool
        for a in actors:
            for t in tools:
                kg.add_edge("actor", a, "tool", t, "USES_TOOL")
            for c in cves:
                kg.add_edge("actor", a, "cve", c, "EXPLOITS_CVE")
            for asset in assets:
                kg.add_edge("actor", a, "asset", asset, "TARGETS_ASSET")
            for camp in campaigns:
                kg.add_edge("actor", a, "campaign", camp, "CONDUCTS_CAMPAIGN")

        # Tool -> Asset
        for t in tools:
            for asset in assets:
                kg.add_edge("tool", t, "asset", asset, "TARGETS_ASSET")
            for c in cves:
                kg.add_edge("tool", t, "cve", c, "EXPLOITS_CVE")

        # 4. LLM-based Causal Triple Extraction (MAGMA-style)
        # This is the slow path - only run for important CTI notes
        if note.metadata.domain in ["cti", "incident", "threat_intel"] or len(note.content.raw) > 200:
            try:
                triples = self.constructor.extract_causal_triples(note.content.raw, note.id)
                if triples:
                    edges = self.constructor.store_causal_edges(triples, note.id)
                    print(f"[Causal] Extracted {len(triples)} triples, stored {edges} edges for note {note.id}")
            except Exception as e:
                print(f"[Causal] Extraction failed: {e}")

    def mark_note_superseded(self, note_id: str, superseded_by_id: str) -> bool:
        old_note = self.store.get_note_by_id(note_id)
        new_note = self.store.get_note_by_id(superseded_by_id)
        if not old_note or not new_note:
            return False

        old_note.links.superseded_by = superseded_by_id
        if note_id not in new_note.links.supersedes:
            new_note.links.supersedes.append(note_id)

        self.store._rewrite_note(old_note)
        self.store._rewrite_note(new_note)
        
        # Add temporal edge to knowledge graph (Task 2)
        kg = get_knowledge_graph()
        kg.add_temporal_edge(
            from_type="note", from_value=superseded_by_id,
            to_type="note", to_value=note_id,
            relationship="SUPERSEDES",
            timestamp=datetime.now().isoformat(),
            properties={"supersedes": note_id}
        )
        
        return True

    def _check_supersession(self, new_note: MemoryNote, resolved_entities: Dict[str, List[str]]) -> Optional[MemoryNote]:
        from datetime import datetime
        candidates = [n for n in self.store.iterate_notes() if n.id != new_note.id]
        if not candidates:
            return None
            
        new_entities = {k: resolved_entities.get(k, []) for k in ["cve", "actor", "tool", "campaign", "asset"]}
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            if candidate.links.superseded_by:
                continue
                
            cand_entities = self.indexer.extractor.extract_all(candidate.content.raw)
            cand_resolved = {}
            for k, v in cand_entities.items():
                cand_resolved[k] = [self.resolver.resolve(k, e) for e in v]
                
            overlap = 0
            for key in ["cve", "actor", "tool", "campaign", "asset"]:
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
                
        # Lowered threshold slightly for benchmark tracking context
        if best_match and best_score >= 1.0:
            self.mark_note_superseded(best_match.id, new_note.id)
            return best_match
            
        return None

    def snapshot(self) -> str:
        """Export memory snapshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = get_default_data_dir()
        snapshot_dir = data_dir / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Export JSONL
        self.store.export_snapshot(str(snapshot_dir))

        return str(snapshot_dir / f"notes_{timestamp}.jsonl")


    # === Phase 6: Knowledge Graph Retrieval ===

    def get_entity_relationships(self, entity_type: str, entity_value: str) -> List[Dict]:
        """Get direct relationships for an entity from the knowledge graph."""
        kg = get_knowledge_graph()
        
        # Resolve alias if necessary
        self.resolver = getattr(self, "resolver", AliasResolver())
        canonical = self.resolver.resolve(entity_type, entity_value)
        
        return kg.get_neighbors(entity_type, canonical)

    def traverse_graph(self, start_type: str, start_value: str, max_depth: int = 2) -> List[Dict]:
        """Traverse relationships from a starting entity."""
        kg = get_knowledge_graph()
        self.resolver = getattr(self, "resolver", AliasResolver())
        canonical = self.resolver.resolve(start_type, start_value)
        
        return kg.traverse(start_type, canonical, max_depth)

    # === Phase 7: Synthesis Layer ===

    def synthesize(
        self,
        query: str,
        format: str = "direct_answer",
        k: int = 10,
        tier_filter: List[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize an answer from retrieved memories (Phase 7 RAG-as-Answer).

        Args:
            query: The question to answer
            format: Output format - "direct_answer", "synthesized_brief",
                    "timeline_analysis", or "relationship_map"
            k: Number of notes to retrieve for context
            tier_filter: Filter by tier ["A", "B"] or ["A", "B", "C"]

        Returns:
            Dictionary with synthesis result, metadata, and sources

        Example:
            result = mm.synthesize("What do we know about APT28?", format="synthesized_brief")
            print(result["synthesis"]["summary"])
        """
        gen = get_synthesis_generator()
        return gen.synthesize(
            query=query,
            memory_manager=self,
            format=format,
            k=k,
            tier_filter=tier_filter
        )

    def validate_synthesis(self, response: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a synthesis response for quality.

        Returns:
            (is_valid, list_of_errors)
        """
        validator = get_synthesis_validator()
        return validator.validate_response(response)

    def check_synthesis_quality(self, response: Dict) -> Dict:
        """
        Compute quality score for a synthesis response.

        Returns quality metrics including score (0-1) and grade.
        """
        validator = get_synthesis_validator()
        return validator.check_quality_score(response)


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
