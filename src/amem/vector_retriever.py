"""
Vector Retrieval - Memory Note Search
A-MEM Agentic Memory Architecture V1.0

Retrieves relevant notes based on embedding similarity with domain filtering.
"""
from typing import List, Optional, Tuple
import numpy as np

from amem.note_schema import MemoryNote
from amem.memory_store import MemoryStore
from amem.vector_memory import get_embedding


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


class VectorRetriever:
    """Retrieve notes by embedding similarity with domain filtering"""

    def __init__(
        self,
        similarity_threshold: float = 0.30,
        memory_store: Optional[MemoryStore] = None
    ):
        self.similarity_threshold = similarity_threshold
        self.store = memory_store or MemoryStore()

    def _get_candidates(self, domain: Optional[str] = None) -> List[MemoryNote]:
        """Get candidate notes, optionally filtered by domain."""
        all_notes = list(self.store.iterate_notes())
        if domain:
            return [n for n in all_notes if n.metadata.domain == domain]
        return all_notes

    def retrieve(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 10,
        include_links: bool = True
    ) -> List[MemoryNote]:
        """
        Retrieve notes relevant to query.
        """
        query_vector = get_embedding(query)
        candidates = self._get_candidates(domain)

        if not candidates:
            return []

        scored = []
        for note in candidates:
            if note.embedding.vector:
                sim = cosine_similarity(query_vector, note.embedding.vector)
                if sim >= self.similarity_threshold:
                    scored.append((note, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = [note for note, sim in scored[:k]]

        if include_links and results:
            results = self._expand_via_links(results, k * 2)

        for note in results:
            note.increment_access()

        return results

    def _expand_via_links(
        self,
        initial_results: List[MemoryNote],
        max_results: int
    ) -> List[MemoryNote]:
        """Expand results by including directly linked notes"""
        all_ids = set(n.id for n in initial_results)
        expanded = list(initial_results)

        for note in initial_results:
            for linked_id in note.links.related:
                if len(expanded) >= max_results:
                    break
                linked_note = self.store.get_note_by_id(linked_id)
                if linked_note and linked_note.id not in all_ids:
                    expanded.append(linked_note)
                    all_ids.add(linked_note.id)

        return expanded[:max_results]

    def get_memory_context(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 10,
        token_budget: int = 4000
    ) -> str:
        """
        Format retrieved notes for injection into agent prompt.
        """
        notes = self.retrieve(query=query, domain=domain, k=k)

        if not notes:
            return "No relevant memories found."

        context_parts = [f"## Relevant Memories ({len(notes)} notes)\n"]

        for i, note in enumerate(notes, 1):
            confidence = note.metadata.confidence
            recency = note.created_at[:10]

            context_parts.append(
                f"\n### [{i}] {note.id} (confidence: {confidence:.2f}, {recency})"
            )
            context_parts.append(f"Context: {note.semantic.context}")
            context_parts.append(f"Content: {note.content.raw[:300]}...")

            if note.links.related:
                context_parts.append(f"Related: {', '.join(note.links.related)}")

        context = "\n".join(context_parts)
        if len(context) > token_budget * 4:
            context = context[:token_budget * 4] + "\n\n[truncated...]"

        return context
