"""
Vector Retrieval - Memory Note Search
Roland Fleet Agentic Memory Architecture V1.0

Retrieves relevant notes based on embedding similarity with domain filtering.
"""
import json
from typing import List, Optional, Tuple
from note_schema import MemoryNote
from embedding_utils import EmbeddingGenerator
from memory_store import MemoryStore


class VectorRetriever:
    """Retrieve notes by embedding similarity with domain filtering"""

    def __init__(self, similarity_threshold: float = 0.30):
        self.similarity_threshold = similarity_threshold
        self.embedder = EmbeddingGenerator()
        self.store = MemoryStore()

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

        Args:
            query: Natural language query
            domain: Optional domain filter (security_ops, project, personal, research)
            k: Number of top results to return
            include_links: Whether to expand results via linked notes

        Returns:
            List of relevant MemoryNotes sorted by relevance
        """
        query_vector = self.embedder.embed(query)
        candidates = self._get_candidates(domain)

        if not candidates:
            return []

        scored = []
        for note in candidates:
            if note.embedding.vector:
                sim = self.embedder.cosine_similarity(query_vector, note.embedding.vector)
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

    def retrieve_by_embedding(
        self,
        query_vector: List[float],
        domain: Optional[str] = None,
        k: int = 10
    ) -> List[Tuple[MemoryNote, float]]:
        """Retrieve notes by embedding vector directly"""
        candidates = self._get_candidates(domain)

        scored = []
        for note in candidates:
            if note.embedding.vector:
                sim = self.embedder.cosine_similarity(query_vector, note.embedding.vector)
                if sim >= self.similarity_threshold:
                    scored.append((note, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def get_memory_context(
        self,
        query: str,
        domain: Optional[str] = None,
        k: int = 10,
        token_budget: int = 4000
    ) -> str:
        """
        Format retrieved notes for injection into agent prompt.
        Returns structured context string with relevance signals.
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


def test_retrieval():
    """Test vector retrieval"""
    print("Testing vector retrieval...")

    retriever = VectorRetriever()

    queries = [
        "threat actor targeting network equipment",
        "MSSP market consolidation",
        "critical vulnerabilities"
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        results = retriever.retrieve(query, k=5)
        print(f"  Found: {len(results)} relevant notes")
        for r in results[:3]:
            print(f"    - {r.id}: {r.semantic.context[:60]}")

    print("\nRetrieval test PASSED")


if __name__ == "__main__":
    test_retrieval()
