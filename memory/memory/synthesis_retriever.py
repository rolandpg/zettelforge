"""
Synthesis Retriever — Phase 7 Hybrid Search for Synthesis
==========================================================

Implements hybrid retrieval combining vector search with knowledge graph traversal
to provide comprehensive context for answer synthesis.

Usage:
    from synthesis_retriever import SynthesisRetriever
    from memory_manager import get_memory_manager

    retriever = SynthesisRetriever()
    context = retriever.retrieve_context(
        query="UNC2452 supply chain activity",
        memory_manager=mm,
        k=15
    )
"""

import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json

from vector_retriever import VectorRetriever
from knowledge_graph import get_knowledge_graph


class SynthesisRetriever:
    """
    Hybrid search retriever combining vector and graph-based retrieval.
    Prioritizes authoritative sources (Tier A/B) and ensures graph coverage.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.30,
        max_results: int = 20,
        include_graph: bool = True
    ):
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results
        self.include_graph = include_graph
        self._vector_retriever = None
        self._lock = threading.RLock()

    def _get_vector_retriever(self) -> VectorRetriever:
        """Get or create vector retriever."""
        if self._vector_retriever is None:
            self._vector_retriever = VectorRetriever(
                similarity_threshold=self.similarity_threshold
            )
        return self._vector_retriever

    def retrieve_context(
        self,
        query: str,
        memory_manager: 'MemoryManager' = None,
        memory_store: 'MemoryStore' = None,
        k: int = 15,
        tier_filter: List[str] = None,
        expand_graph: bool = True
    ) -> Dict:
        """
        Retrieve comprehensive context for synthesis.

        Args:
            query: User query
            memory_manager: MemoryManager instance
            memory_store: MemoryStore instance
            k: Number of notes to retrieve
            tier_filter: Tier filter for notes
            expand_graph: Whether to expand graph context

        Returns:
            Context dictionary with notes, entities, relationships
        """
        mm = memory_manager
        if mm is None:
            from memory_manager import get_memory_manager
            mm = get_memory_manager()

        # Get tier filter
        tier_filter = tier_filter or ["A", "B"]

        with self._lock:
            context = {
                "query": query,
                "retrieved_at": datetime.utcnow().isoformat() + "Z",
                "notes": [],
                "entities": {},
                "relationships": [],
                "source_counts": {
                    "vector": 0,
                    "graph": 0,
                    "deduplicated": 0
                }
            }

            # 1. Vector search for semantic context
            vector_results = self._retrieve_by_vector(query, mm, k, tier_filter)
            context["notes"].extend(vector_results["notes"])
            # Build entities from note content and query
            all_text = query
            for note in vector_results["notes"]:
                all_text += " " + note.content.raw
            context["entities"] = self._extract_entities(all_text)
            context["source_counts"]["vector"] = len(vector_results["notes"])

            # 2. Graph traversal for entity expansion
            if self.include_graph and expand_graph:
                graph_context = self._expand_graph_context(
                    query, mm, max_depth=2, tier_filter=tier_filter
                )
                context["relationships"].extend(graph_context["relationships"])
                context["source_counts"]["graph"] = len(graph_context["notes"])

                # Deduplicate notes
                note_ids = {n.id for n in context["notes"]}
                new_notes = [n for n in graph_context["notes"] if n.id not in note_ids]
                context["notes"].extend(new_notes)
                context["source_counts"]["deduplicated"] = len(new_notes)

            # 3. Sort by relevance and limit
            context["notes"] = self._sort_notes(context["notes"], query)[:self.max_results]

            # 4. Build entity index for quick lookup
            context["entities_by_type"] = self._index_entities_by_type(context["entities"])

            return context

    def _retrieve_by_vector(
        self,
        query: str,
        mm: 'MemoryManager',
        k: int,
        tier_filter: List[str]
    ) -> Dict:
        """Retrieve notes via vector search."""
        results = mm.recall(query, k=k * 2, domain="security_ops")
        filtered = [n for n in results if n.metadata.tier in tier_filter]
        return {"notes": filtered[:k]}

    def _expand_graph_context(
        self,
        query: str,
        mm: 'MemoryManager',
        max_depth: int = 2,
        tier_filter: List[str] = None
    ) -> Dict:
        """Expand context via knowledge graph traversal."""
        kg = get_knowledge_graph()
        kg_results = {"notes": [], "relationships": []}

        # Extract entities from query
        entities = self._extract_entities(query)
        if not entities:
            return kg_results

        tier_filter = tier_filter or ["A", "B"]

        # Get note IDs for entities
        entity_notes = {}
        for entity in entities:
            for entity_type in ['actor', 'tool', 'cve', 'campaign']:
                node = kg.get_node_by_entity(entity_type, entity)
                if node:
                    note_ids = mm.entity_indexer.get_note_ids(entity_type, entity)
                    entity_notes[entity] = note_ids
                    break

        # If we found entities, expand graph
        if entity_notes:
            for entity, note_ids in entity_notes.items():
                for note_id in note_ids:
                    note = mm.memory_store.get_note_by_id(note_id)
                    if note and note.metadata.tier in tier_filter:
                        kg_results["notes"].append(note)

                        # Get relationships from graph
                        node = kg.get_node_by_entity('note', note_id)
                        if node:
                            edges = kg.get_edges_from(node['node_id'])
                            for edge in edges:
                                kg_results["relationships"].append({
                                    "from": entity,
                                    "to": edge.get('to_node_id', 'unknown'),
                                    "relationship": edge.get('relationship_type', 'UNKNOWN'),
                                    "confidence": 0.8
                                })

        return kg_results

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entities from text."""
        import re
        entities = []

        # CVE patterns
        for match in re.finditer(r'(CVE-\d{4}-\d{4,})', text, re.IGNORECASE):
            entities.append(match.group(1).lower())

        # Actor patterns (simplified)
        actor_patterns = [
            r'\b(volt\s+typhoon|apt28|lazarus|lazarus\s+group)\b',
            r'\b(muddy\s*water|mercury|temp\.zagros)\b',
            r'\b(unc\d+|nocturnal\s+kitten)\b',
        ]

        for pattern in actor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities.append(match.group(0).lower().replace(' ', '-'))

        return entities[:10]

    def _index_entities_by_type(self, entities: List[str]) -> Dict[str, List[str]]:
        """Index entities by type (for quick lookup)."""
        index = {
            "cve": [],
            "actor": [],
            "tool": [],
            "campaign": [],
            "other": []
        }

        for entity in entities:
            if entity.startswith('cve-'):
                index["cve"].append(entity)
            elif any(x in entity for x in ['apt', 'lazarus', 'volty', 'muddy']):
                index["actor"].append(entity)
            else:
                index["other"].append(entity)

        return index

    def _sort_notes(self, notes: List, query: str) -> List:
        """Sort notes by relevance to query."""
        # Simple scoring: confidence + tier bonus
        def score(note):
            base = note.metadata.confidence
            tier_bonus = {"A": 0.2, "B": 0.1, "C": 0.0}.get(note.metadata.tier, 0)
            return base + tier_bonus

        return sorted(notes, key=score, reverse=True)

    def get_context_summary(self, context: Dict, max_length: int = 500) -> str:
        """Generate a summary of the retrieved context."""
        notes = context.get("notes", [])
        if not notes:
            return "No relevant notes found."

        summaries = []
        for note in notes[:5]:
            if note.semantic.context:
                summaries.append(f"[{note.id}] {note.semantic.context}")
            else:
                summaries.append(f"[{note.id}] {note.content.raw[:100]}...")

        summary = " | ".join(summaries)
        return summary[:max_length] + ("..." if len(summary) > max_length else "")


# =============================================================================
# Global Access
# =============================================================================

_retriever: Optional[SynthesisRetriever] = None
_retriever_lock = threading.Lock()


def get_synthesis_retriever() -> SynthesisRetriever:
    """Get or create the global synthesis retriever instance."""
    global _retriever
    if _retriever is None:
        with _retriever_lock:
            if _retriever is None:
                _retriever = SynthesisRetriever()
    return _retriever


# =============================================================================
# CLI / Quick Test
# =============================================================================

if __name__ == "__main__":
    print("Synthesis Retriever CLI")
    print("=" * 50)

    retriever = SynthesisRetriever()

    # Test with no data
    print("\n1. Test retrieval with empty data:")
    context = retriever.retrieve_context(
        query="threat actors targeting government",
        k=5
    )
    print(f"   Notes retrieved: {len(context.get('notes', []))}")
    print(f"   Entities found: {context.get('entities_by_type')}")

    print("\n2. Context summary:")
    summary = retriever.get_context_summary(context)
    print(f"   {summary}")

    print("\n3. Synthesis Retriever initialized successfully.")
