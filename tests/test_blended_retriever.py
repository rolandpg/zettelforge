"""Tests for BlendedRetriever - combines vector + graph results."""

import pytest
from datetime import datetime

from zettelforge.blended_retriever import BlendedRetriever
from zettelforge.graph_retriever import ScoredResult
from zettelforge.note_schema import MemoryNote, Content, Semantic, Embedding, Metadata

NOW = datetime.now().isoformat()


def _make_note(note_id: str, raw: str) -> MemoryNote:
    return MemoryNote(
        id=note_id,
        created_at=NOW,
        updated_at=NOW,
        content=Content(raw=raw, source_type="test", source_ref=""),
        semantic=Semantic(context=raw[:50], keywords=[], tags=[], entities=[]),
        embedding=Embedding(vector=[0.1] * 768),
        metadata=Metadata(),
    )


class TestBlendedRetriever:
    def test_vector_only_when_no_graph_results(self):
        vector_notes = [
            (_make_note("v1", "vector result 1"), 0.9),
            (_make_note("v2", "vector result 2"), 0.7),
        ]
        policy = {"vector": 0.5, "graph": 0.5, "entity_index": 0.0, "temporal": 0.0, "top_k": 10}
        blended = BlendedRetriever()
        results = blended.blend(
            vector_results=vector_notes,
            graph_results=[],
            policy=policy,
            note_lookup=lambda nid: None,
            k=10,
        )
        assert len(results) == 2
        assert results[0].id == "v1"

    def test_graph_only_when_no_vector_results(self):
        note_g1 = _make_note("g1", "graph result 1")
        graph_scored = [ScoredResult(note_id="g1", score=0.8, hops=1, path=[])]
        policy = {"vector": 0.5, "graph": 0.5, "entity_index": 0.0, "temporal": 0.0, "top_k": 10}
        blended = BlendedRetriever()
        results = blended.blend(
            vector_results=[],
            graph_results=graph_scored,
            policy=policy,
            note_lookup=lambda nid: note_g1 if nid == "g1" else None,
            k=10,
        )
        assert len(results) == 1
        assert results[0].id == "g1"

    def test_blending_merges_and_deduplicates(self):
        shared_note = _make_note("shared", "appears in both")
        vector_notes = [(shared_note, 0.8), (_make_note("v_only", "vector only"), 0.5)]
        graph_scored = [
            ScoredResult(note_id="shared", score=0.9, hops=1, path=[]),
            ScoredResult(note_id="g_only", score=0.5, hops=2, path=[]),
        ]
        note_g_only = _make_note("g_only", "graph only")
        policy = {"vector": 0.5, "graph": 0.5, "entity_index": 0.0, "temporal": 0.0, "top_k": 10}

        def lookup(nid):
            return {"g_only": note_g_only, "shared": shared_note}.get(nid)

        blended = BlendedRetriever()
        results = blended.blend(
            vector_results=vector_notes,
            graph_results=graph_scored,
            policy=policy,
            note_lookup=lookup,
            k=10,
        )
        ids = [r.id for r in results]
        assert ids.count("shared") == 1
        assert "v_only" in ids
        assert "g_only" in ids

    def test_shared_note_ranks_higher(self):
        shared_note = _make_note("shared", "appears in both")
        v_only = _make_note("v_only", "vector only")
        g_only_note = _make_note("g_only", "graph only")
        # Shared has high vector score, v_only has lower
        vector_notes = [(shared_note, 0.9), (v_only, 0.5)]
        graph_scored = [
            ScoredResult(note_id="shared", score=0.8, hops=1, path=[]),
            ScoredResult(note_id="g_only", score=0.3, hops=2, path=[]),
        ]
        policy = {"vector": 0.5, "graph": 0.5, "entity_index": 0.0, "temporal": 0.0, "top_k": 10}

        def lookup(nid):
            return {"g_only": g_only_note, "shared": shared_note}.get(nid)

        blended = BlendedRetriever()
        results = blended.blend(
            vector_results=vector_notes,
            graph_results=graph_scored,
            policy=policy,
            note_lookup=lookup,
            k=10,
        )
        assert results[0].id == "shared"

    def test_respects_k_limit(self):
        vector_notes = [(_make_note(f"v{i}", f"note {i}"), 0.9 - i * 0.05) for i in range(10)]
        policy = {"vector": 1.0, "graph": 0.0, "entity_index": 0.0, "temporal": 0.0, "top_k": 10}
        blended = BlendedRetriever()
        results = blended.blend(
            vector_results=vector_notes,
            graph_results=[],
            policy=policy,
            note_lookup=lambda nid: None,
            k=3,
        )
        assert len(results) == 3

    def test_policy_weights_affect_ranking(self):
        v_note = _make_note("v_only", "vector only")
        g_note = _make_note("g_only", "graph only")
        vector_notes = [(v_note, 0.8)]
        graph_scored = [ScoredResult(note_id="g_only", score=0.9, hops=1, path=[])]
        policy = {"vector": 0.1, "graph": 0.9, "entity_index": 0.0, "temporal": 0.0, "top_k": 10}
        blended = BlendedRetriever()
        results = blended.blend(
            vector_results=vector_notes,
            graph_results=graph_scored,
            policy=policy,
            note_lookup=lambda nid: g_note if nid == "g_only" else None,
            k=10,
        )
        assert results[0].id == "g_only"

    def test_actual_similarity_preserved_not_position_rank(self):
        """Verify that actual similarity scores drive ranking, not position."""
        # Two notes: low-similarity ranked first (position 1) vs high-similarity ranked second
        low_sim = _make_note("low_sim", "low similarity note")
        high_sim = _make_note("high_sim", "high similarity note")
        # Even though low_sim appears first, its score is much lower
        vector_notes = [(low_sim, 0.2), (high_sim, 0.95)]
        policy = {"vector": 1.0, "graph": 0.0, "entity_index": 0.0, "temporal": 0.0, "top_k": 10}
        blended = BlendedRetriever()
        results = blended.blend(
            vector_results=vector_notes,
            graph_results=[],
            policy=policy,
            note_lookup=lambda nid: None,
            k=10,
        )
        # high_sim should rank first because its ACTUAL score (0.95) > low_sim (0.2)
        assert results[0].id == "high_sim"

    def test_rrf_fusion(self):
        """Test RRF fusion method."""
        v_note = _make_note("v1", "vector result")
        g_note = _make_note("g1", "graph result")
        shared = _make_note("shared", "in both")
        vector_notes = [(shared, 0.9), (v_note, 0.5)]
        graph_scored = [
            ScoredResult(note_id="shared", score=0.8, hops=1, path=[]),
            ScoredResult(note_id="g1", score=0.3, hops=2, path=[]),
        ]
        blended = BlendedRetriever()
        results = blended.blend_rrf(
            vector_results=vector_notes,
            graph_results=graph_scored,
            note_lookup=lambda nid: {"g1": g_note, "shared": shared}.get(nid),
            k=10,
        )
        ids = [r.id for r in results]
        assert "shared" in ids
        # Shared appears in both signals so it should rank first
        assert ids[0] == "shared"

    def test_normalize_scores_uniform(self):
        """All equal scores should produce uniform normalized scores."""
        from zettelforge.blended_retriever import _normalize_scores
        n1 = _make_note("a", "a")
        n2 = _make_note("b", "b")
        result = _normalize_scores([(n1, 0.5), (n2, 0.5)])
        assert result[0][1] == result[1][1] == 0.5

    def test_normalize_scores_range(self):
        """Min-max normalization should map min->0, max->1."""
        from zettelforge.blended_retriever import _normalize_scores
        n1 = _make_note("a", "a")
        n2 = _make_note("b", "b")
        n3 = _make_note("c", "c")
        result = _normalize_scores([(n1, 0.1), (n2, 0.5), (n3, 1.0)])
        assert abs(result[0][1] - 0.0) < 1e-9  # min -> 0
        assert abs(result[2][1] - 1.0) < 1e-9  # max -> 1