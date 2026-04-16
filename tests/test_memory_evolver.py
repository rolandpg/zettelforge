"""Tests for memory_evolver.py — A-Mem neighbor evolution."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from zettelforge.memory_evolver import MemoryEvolver
from zettelforge.note_schema import (
    Content,
    Embedding,
    Links,
    MemoryNote,
    Metadata,
    Semantic,
)


def _make_note(note_id: str, content: str, domain: str = "cti") -> MemoryNote:
    """Build a minimal MemoryNote for testing."""
    now = datetime.now().isoformat()
    return MemoryNote(
        id=note_id,
        created_at=now,
        updated_at=now,
        content=Content(raw=content, source_type="test", source_ref="test"),
        semantic=Semantic(context="", keywords=[], tags=[], entities=[]),
        embedding=Embedding(vector=[0.1] * 768),
        metadata=Metadata(domain=domain),
        links=Links(),
    )


class TestFindEvolutionCandidates:
    def test_returns_similar_notes_excluding_self(self):
        mm = MagicMock()
        evolver = MemoryEvolver(mm, k=3)

        new_note = _make_note("new-1", "APT28 uses new malware Gamefish")
        neighbor = _make_note("old-1", "APT28 is a Russian threat actor")

        mm.recall.return_value = [new_note, neighbor]

        candidates = evolver.find_evolution_candidates(new_note)
        assert len(candidates) == 1
        assert candidates[0].id == "old-1"

    def test_caps_at_k(self):
        mm = MagicMock()
        evolver = MemoryEvolver(mm, k=2)

        new_note = _make_note("new-1", "APT28 uses Gamefish")
        neighbors = [_make_note(f"old-{i}", f"Note {i}") for i in range(5)]
        mm.recall.return_value = neighbors

        candidates = evolver.find_evolution_candidates(new_note)
        assert len(candidates) == 2

    def test_empty_recall_returns_empty(self):
        mm = MagicMock()
        mm.recall.return_value = []
        evolver = MemoryEvolver(mm, k=5)

        candidates = evolver.find_evolution_candidates(_make_note("n", "text"))
        assert candidates == []


class TestEvaluateEvolution:
    @patch("zettelforge.memory_evolver.generate")
    def test_evolve_action(self, mock_gen):
        mm = MagicMock()
        evolver = MemoryEvolver(mm)

        mock_gen.return_value = (
            '{"action": "evolve", "reason": "adds new TTP", '
            '"updated_content": "APT28 is a Russian threat actor that uses Gamefish malware"}'
        )

        new_note = _make_note("new-1", "APT28 uses Gamefish")
        neighbor = _make_note("old-1", "APT28 is a Russian threat actor")

        result = evolver.evaluate_evolution(new_note, neighbor)
        assert result is not None
        assert result["action"] == "evolve"
        assert "Gamefish" in result["updated_content"]

    @patch("zettelforge.memory_evolver.generate")
    def test_keep_action(self, mock_gen):
        mm = MagicMock()
        evolver = MemoryEvolver(mm)

        mock_gen.return_value = '{"action": "keep", "reason": "unrelated", "updated_content": ""}'

        result = evolver.evaluate_evolution(
            _make_note("new-1", "Weather is nice"),
            _make_note("old-1", "APT28 is Russian"),
        )
        assert result is not None
        assert result["action"] == "keep"

    @patch("zettelforge.memory_evolver.generate")
    def test_parse_failure_retries_once(self, mock_gen):
        mm = MagicMock()
        evolver = MemoryEvolver(mm)

        # First call returns garbage, second returns valid JSON
        mock_gen.side_effect = [
            "not json at all",
            '{"action": "keep", "reason": "retry worked", "updated_content": ""}',
        ]

        result = evolver.evaluate_evolution(
            _make_note("new-1", "text"),
            _make_note("old-1", "text"),
        )
        assert result is not None
        assert result["action"] == "keep"
        assert mock_gen.call_count == 2

    @patch("zettelforge.memory_evolver.generate")
    def test_both_attempts_fail_returns_none(self, mock_gen):
        mm = MagicMock()
        evolver = MemoryEvolver(mm)

        mock_gen.return_value = "garbage"

        result = evolver.evaluate_evolution(
            _make_note("new-1", "text"),
            _make_note("old-1", "text"),
        )
        assert result is None

    @patch("zettelforge.memory_evolver.generate")
    def test_invalid_action_returns_none(self, mock_gen):
        mm = MagicMock()
        evolver = MemoryEvolver(mm)

        mock_gen.return_value = '{"action": "delete", "reason": "bad", "updated_content": ""}'

        result = evolver.evaluate_evolution(
            _make_note("new-1", "text"),
            _make_note("old-1", "text"),
        )
        assert result is None

    @patch("zettelforge.memory_evolver.generate")
    def test_evolve_without_content_returns_none(self, mock_gen):
        mm = MagicMock()
        evolver = MemoryEvolver(mm)

        mock_gen.return_value = '{"action": "evolve", "reason": "oops", "updated_content": ""}'

        result = evolver.evaluate_evolution(
            _make_note("new-1", "text"),
            _make_note("old-1", "text"),
        )
        assert result is None


class TestApplyEvolution:
    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.2] * 768)
    def test_preserves_original_in_previous_raw(self, _mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        neighbor = _make_note("old-1", "APT28 is Russian")

        evolved = evolver.apply_evolution(neighbor, "APT28 is Russian and uses Gamefish", "new-1")

        assert evolved.content.previous_raw == "APT28 is Russian"
        assert "Gamefish" in evolved.content.raw

    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.2] * 768)
    def test_increments_evolution_count(self, _mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        neighbor = _make_note("old-1", "APT28 is Russian")
        assert neighbor.metadata.evolution_count == 0

        evolver.apply_evolution(neighbor, "Updated content", "new-1")
        assert neighbor.metadata.evolution_count == 1

    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.2] * 768)
    def test_records_evolved_by(self, _mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        neighbor = _make_note("old-1", "APT28 is Russian")
        evolver.apply_evolution(neighbor, "Updated", "new-1")

        assert "new-1" in neighbor.evolved_by

    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.2] * 768)
    def test_re_embeds_with_new_content(self, mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        neighbor = _make_note("old-1", "original")
        evolver.apply_evolution(neighbor, "evolved text", "new-1")

        mock_embed.assert_called_once_with("evolved text")
        assert neighbor.embedding.vector == [0.2] * 768

    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.2] * 768)
    def test_persists_via_rewrite(self, _mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        neighbor = _make_note("old-1", "original")
        evolver.apply_evolution(neighbor, "evolved", "new-1")

        mm.store._rewrite_note.assert_called_once_with(neighbor)


class TestRollback:
    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.1] * 768)
    def test_restores_original_content(self, _mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        note = _make_note("old-1", "Evolved content")
        note.content.previous_raw = "Original content"
        note.metadata.evolution_count = 1

        assert evolver.rollback(note) is True
        assert note.content.raw == "Original content"
        assert note.content.previous_raw is None

    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.1] * 768)
    def test_decrements_evolution_count(self, _mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        note = _make_note("old-1", "Evolved")
        note.content.previous_raw = "Original"
        note.metadata.evolution_count = 2

        evolver.rollback(note)
        assert note.metadata.evolution_count == 1

    def test_returns_false_when_no_previous(self):
        mm = MagicMock()
        evolver = MemoryEvolver(mm)

        note = _make_note("old-1", "Content")
        assert note.content.previous_raw is None
        assert evolver.rollback(note) is False

    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.1] * 768)
    def test_re_embeds_restored_content(self, mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        note = _make_note("old-1", "Evolved")
        note.content.previous_raw = "Original"

        evolver.rollback(note)
        mock_embed.assert_called_once_with("Original")

    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.1] * 768)
    def test_evolution_count_floors_at_zero(self, _mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()
        evolver = MemoryEvolver(mm)

        note = _make_note("old-1", "Evolved")
        note.content.previous_raw = "Original"
        note.metadata.evolution_count = 0

        evolver.rollback(note)
        assert note.metadata.evolution_count == 0


class TestEvolveNeighbors:
    @patch("zettelforge.memory_evolver.get_embedding", return_value=[0.2] * 768)
    @patch("zettelforge.memory_evolver.generate")
    def test_full_pipeline_evolve(self, mock_gen, _mock_embed):
        mm = MagicMock()
        mm.store._rewrite_note = MagicMock()

        neighbor = _make_note("old-1", "APT28 is Russian")
        mm.recall.return_value = [neighbor]

        mock_gen.return_value = (
            '{"action": "evolve", "reason": "adds TTP", '
            '"updated_content": "APT28 is Russian and uses Gamefish"}'
        )

        evolver = MemoryEvolver(mm, k=5)
        new_note = _make_note("new-1", "APT28 uses Gamefish")

        report = evolver.evolve_neighbors(new_note)

        assert report["candidates_found"] == 1
        assert report["evaluated"] == 1
        assert report["evolved"] == 1
        assert report["kept"] == 0
        assert report["errors"] == 0
        assert "old-1" in report["evolved_ids"]

    @patch("zettelforge.memory_evolver.generate")
    def test_full_pipeline_keep(self, mock_gen):
        mm = MagicMock()

        neighbor = _make_note("old-1", "APT28 is Russian")
        mm.recall.return_value = [neighbor]

        mock_gen.return_value = '{"action": "keep", "reason": "unrelated", "updated_content": ""}'

        evolver = MemoryEvolver(mm, k=5)
        report = evolver.evolve_neighbors(_make_note("new-1", "Weather report"))

        assert report["evolved"] == 0
        assert report["kept"] == 1

    @patch("zettelforge.memory_evolver.generate")
    def test_full_pipeline_parse_error(self, mock_gen):
        mm = MagicMock()

        neighbor = _make_note("old-1", "APT28 is Russian")
        mm.recall.return_value = [neighbor]

        mock_gen.return_value = "total garbage"

        evolver = MemoryEvolver(mm, k=5)
        report = evolver.evolve_neighbors(_make_note("new-1", "text"))

        assert report["errors"] == 1
        assert report["evolved"] == 0

    def test_no_candidates(self):
        mm = MagicMock()
        mm.recall.return_value = []

        evolver = MemoryEvolver(mm, k=5)
        report = evolver.evolve_neighbors(_make_note("new-1", "text"))

        assert report["candidates_found"] == 0
        assert report["evaluated"] == 0
