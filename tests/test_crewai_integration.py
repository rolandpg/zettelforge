"""Tests for ZettelForge × CrewAI tool integration.

The CrewAI dependency is optional. These tests are skipped when crewai is
not installed so they don't break CI runs that don't pin the optional extra.
The recall/synthesize round-trip tests further skip on the mock embedding
provider since they need real semantic similarity to surface results.
"""

from __future__ import annotations

import os

import pytest

from zettelforge import MemoryManager

crewai = pytest.importorskip("crewai")  # noqa: F841 — gate the whole module

# Importing the integration module also gates on crewai, so do it after the gate.
from zettelforge.integrations.crewai import (  # noqa: E402
    ZettelForgeRecallTool,
    ZettelForgeRememberTool,
    ZettelForgeSynthesizeTool,
    _format_recall_result,
    _format_synthesis_result,
)


# ── Pure-formatter tests (no MemoryManager needed) ──────────────────────────


class TestRecallFormatter:
    """The recall formatter is the contract between ZettelForge data and the
    string the agent reasons over. Lock its shape so we don't silently change
    what agents see."""

    def test_empty_returns_no_match_message(self):
        out = _format_recall_result([], "APT28")
        assert "No matching notes" in out
        assert "APT28" in out

    def test_renders_note_header_fields(self):
        from zettelforge.note_schema import (
            Content,
            Embedding,
            MemoryNote,
            Metadata,
            Semantic,
        )

        note = MemoryNote(
            id="note-abc",
            created_at="2026-04-27T00:00:00Z",
            updated_at="2026-04-27T00:00:00Z",
            content=Content(
                raw="APT28 used spear-phishing.",
                source_type="report",
                source_ref="cti/incident-42",
            ),
            semantic=Semantic(context="APT28 spear-phishing observation",
                              entities=["APT28", "spear-phishing"]),
            embedding=Embedding(),
            metadata=Metadata(domain="cti", tier="A", confidence=0.9, importance=3),
        )
        out = _format_recall_result([note], "spear-phishing")
        assert "id=note-abc" in out
        assert "tier=A" in out
        assert "domain=cti" in out
        assert "cti/incident-42" in out
        assert "APT28" in out
        assert "spear-phishing" in out

    def test_truncates_long_content(self):
        from zettelforge.note_schema import (
            Content,
            Embedding,
            MemoryNote,
            Metadata,
            Semantic,
        )

        long = "A" * 1200
        note = MemoryNote(
            id="note-long",
            created_at="2026-04-27T00:00:00Z",
            updated_at="2026-04-27T00:00:00Z",
            content=Content(raw=long, source_type="report", source_ref=""),
            semantic=Semantic(context="long-content-fixture"),
            embedding=Embedding(),
            metadata=Metadata(domain="cti", tier="B"),
        )
        out = _format_recall_result([note], "any")
        # Content body is truncated at 500 chars + ellipsis marker
        assert "..." in out
        assert long not in out


class TestSynthesisFormatter:
    """The synthesis result shape varies by format (direct_answer vs.
    synthesized_brief vs. timeline_analysis vs. relationship_map). The
    formatter must surface the answer field for each shape and append
    sources without losing structure."""

    def test_direct_answer_with_sources(self):
        result = {
            "answer": "APT28 used Cobalt Strike for lateral movement.",
            "confidence": 0.85,
            "sources": [
                {"id": "note-1", "tier": "A"},
                {"id": "note-2", "tier": "B"},
            ],
        }
        out = _format_synthesis_result(result)
        assert "Cobalt Strike" in out
        assert "confidence: 0.85" in out
        assert "note-1" in out
        assert "tier=A" in out

    def test_summary_field_used_when_answer_absent(self):
        result = {"summary": "APT28 active throughout 2025.", "sources": []}
        out = _format_synthesis_result(result)
        assert "APT28 active throughout 2025." in out

    def test_structured_format_serialized_as_json(self):
        result = {
            "timeline": [{"date": "2025-01", "event": "initial access"}],
            "sources": ["note-x"],
        }
        out = _format_synthesis_result(result)
        # Structured payloads are coerced to JSON so the agent doesn't lose them
        assert "initial access" in out
        assert "note-x" in out

    def test_empty_synthesis_returns_explanatory_string(self):
        out = _format_synthesis_result({})
        assert "no answer" in out


# ── Tool wiring tests (no LLM/embedding work) ───────────────────────────────


class TestToolMetadata:
    """Tools must expose name/description/args_schema in CrewAI's expected
    BaseTool shape. This catches accidental schema regressions before they
    surface as runtime errors inside an agent crew."""

    def test_recall_tool_metadata(self):
        from zettelforge.integrations.crewai import _RecallInput

        mm = MemoryManager()
        tool = ZettelForgeRecallTool(memory_manager=mm)
        assert tool.name == "zettelforge_recall"
        assert "Search ZettelForge memory" in tool.description
        assert tool.args_schema is _RecallInput
        assert tool.k == 10
        assert tool.domain is None

    def test_remember_tool_metadata(self):
        from zettelforge.integrations.crewai import _RememberInput

        mm = MemoryManager()
        tool = ZettelForgeRememberTool(memory_manager=mm)
        assert tool.name == "zettelforge_remember"
        assert "Store a new note" in tool.description
        assert tool.args_schema is _RememberInput
        assert tool.domain == "cti"
        assert tool.source_type == "crewai_agent"
        assert tool.evolve is False

    def test_synthesize_tool_metadata(self):
        from zettelforge.integrations.crewai import _SynthesizeInput

        mm = MemoryManager()
        tool = ZettelForgeSynthesizeTool(memory_manager=mm)
        assert tool.name == "zettelforge_synthesize"
        assert "synthesized" in tool.description.lower()
        assert tool.args_schema is _SynthesizeInput
        assert tool.k == 10
        assert tool.format == "direct_answer"

    def test_tools_carry_memory_manager(self):
        """Regression: the memory_manager Field must be accepted as an
        arbitrary type rather than rejected by Pydantic strict-mode."""
        mm = MemoryManager()
        for tool_cls in (
            ZettelForgeRecallTool,
            ZettelForgeRememberTool,
            ZettelForgeSynthesizeTool,
        ):
            tool = tool_cls(memory_manager=mm)
            assert tool.memory_manager is mm


# ── Round-trip tests (need real embeddings) ─────────────────────────────────


@pytest.mark.skipif(
    os.environ.get("ZETTELFORGE_EMBEDDING_PROVIDER") == "mock",
    reason="Round-trip tests require real embeddings (not mock).",
)
class TestRoundTrip:
    @pytest.fixture
    def memory_manager(self, tmp_path):
        mm = MemoryManager(jsonl_path=str(tmp_path / "zf_crewai_test" / "notes.jsonl"))
        mm.remember(
            "APT28 (Fancy Bear) uses spear-phishing for initial access against NATO targets.",
            domain="cti",
        )
        mm.remember(
            "CVE-2024-3094: XZ Utils backdoor in 5.6.0 and 5.6.1, CVSS 10.0.",
            domain="cti",
        )
        return mm

    def test_recall_returns_formatted_text(self, memory_manager):
        tool = ZettelForgeRecallTool(memory_manager=memory_manager, k=2)
        out = tool._run(query="APT28 spear-phishing")
        assert isinstance(out, str)
        assert "APT28" in out
        assert "id=" in out

    def test_remember_persists_and_returns_id(self, memory_manager):
        tool = ZettelForgeRememberTool(memory_manager=memory_manager)
        out = tool._run(
            content="Lazarus Group observed using novel macOS payload in 2025-Q1.",
            source_ref="incident/2025-q1-lazarus",
        )
        assert "Stored note id=" in out
        # Recall should now surface it
        recall = ZettelForgeRecallTool(memory_manager=memory_manager, k=5)
        recall_out = recall._run(query="Lazarus macOS payload")
        assert "Lazarus" in recall_out
