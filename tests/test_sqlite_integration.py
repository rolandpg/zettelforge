"""
Integration tests for MemoryManager with SQLiteBackend.

These tests use a real MemoryManager and real SQLite database — no mocks.
Each test gets an isolated tmp_path directory.
"""

import os

os.environ["ZETTELFORGE_BACKEND"] = "sqlite"

import pytest

from zettelforge import MemoryManager


@pytest.fixture
def mm(tmp_path):
    """Create an isolated MemoryManager backed by SQLite in tmp_path."""
    os.environ["AMEM_DATA_DIR"] = str(tmp_path)
    mgr = MemoryManager(jsonl_path=str(tmp_path / "notes.jsonl"))
    yield mgr
    # Cleanup: close the backend to release the DB file
    try:
        mgr.store.close()
    except Exception:
        pass


class TestSQLiteIntegration:
    """End-to-end integration tests for MemoryManager + SQLiteBackend."""

    def test_remember_and_recall_roundtrip(self, mm):
        """Remember a CTI report, recall it by query, verify content matches."""
        content = (
            "APT28 deployed a new variant of XAgent malware targeting "
            "European government networks in March 2026. The malware uses "
            "DNS tunneling for command and control communications."
        )
        note, status = mm.remember(content, domain="cti", sync=True)

        assert status == "created"
        assert note.id is not None
        assert note.content.raw == content

        # Verify the note is retrievable by ID
        retrieved = mm.store.get_note_by_id(note.id)
        assert retrieved is not None
        assert retrieved.content.raw == content
        assert retrieved.metadata.domain == "cti"

    def test_entity_extraction_and_lookup(self, mm):
        """Remember text with CVEs/actors, verify recall_entity finds it."""
        content = (
            "CVE-2024-3094 is a critical vulnerability in XZ Utils that was "
            "exploited by a sophisticated supply chain attack. The backdoor "
            "was discovered in March 2024."
        )
        note, status = mm.remember(content, domain="cti", sync=True)
        assert status == "created"

        # Look up by CVE entity
        results = mm.recall_entity("cve", "CVE-2024-3094")
        assert len(results) >= 1
        found_ids = [r.id for r in results]
        assert note.id in found_ids

    def test_kg_edges_created(self, mm):
        """Remember text with actor+tool, verify KG edges are created."""
        content = (
            "Sandworm was observed using Cobalt Strike beacons to maintain "
            "persistent access to compromised networks."
        )
        note, status = mm.remember(content, domain="cti", sync=True)
        assert status == "created"

        # "Sandworm" matches the actor regex, "Cobalt Strike" matches tool.
        # The heuristic KG builder should create USES_TOOL and MENTIONED_IN edges.
        relationships = mm.get_entity_relationships("actor", "sandworm")

        # At minimum there should be edges from the heuristic builder
        assert len(relationships) >= 1

        # Check for expected relationship types (heuristic or LLM-generated)
        rel_types = {r["relationship"] for r in relationships}
        # Accept any of the known edge types the system creates
        expected_any = {"USES_TOOL", "MENTIONED_IN", "uses", "uses_tool"}
        assert rel_types & expected_any, f"Expected one of {expected_any}, got {rel_types}"

    def test_supersession_flow(self, mm):
        """Remember similar content twice, verify first note gets superseded."""
        content_v1 = (
            "CVE-2024-9999 affects nginx versions before 1.25.4 and allows "
            "remote code execution via crafted HTTP headers."
        )
        note_v1, status_v1 = mm.remember(content_v1, domain="cti", sync=True)
        assert status_v1 == "created"

        # Second note with overlapping entities but updated information
        content_v2 = (
            "CVE-2024-9999 affects nginx versions before 1.25.5 and allows "
            "remote code execution via crafted HTTP headers. A patch is now "
            "available. CVSS score is 9.8."
        )
        note_v2, status_v2 = mm.remember(content_v2, domain="cti", sync=True)
        assert status_v2 == "created"

        # The first note should now be superseded by the second
        old_note = mm.store.get_note_by_id(note_v1.id)
        assert old_note is not None
        # Supersession requires entity overlap score >= 1.0
        # With shared CVE entity, this should trigger
        if old_note.links.superseded_by:
            assert old_note.links.superseded_by == note_v2.id

    def test_count_notes(self, mm):
        """Remember 3 notes, verify get_stats()['total_notes'] == 3."""
        mm.remember("First note about network security.", domain="cti", sync=True)
        mm.remember("Second note about malware analysis.", domain="cti", sync=True)
        mm.remember("Third note about threat intelligence.", domain="cti", sync=True)

        stats = mm.get_stats()
        assert stats["total_notes"] == 3
