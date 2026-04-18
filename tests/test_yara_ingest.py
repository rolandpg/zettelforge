"""End-to-end ingest tests for zettelforge.yara.ingest."""

from pathlib import Path

import pytest

from zettelforge.memory_manager import MemoryManager
from zettelforge.yara.ingest import ingest_rule, ingest_rules_dir

FIXTURES = Path(__file__).parent / "fixtures" / "yara"


@pytest.fixture
def mm(tmp_path: Path) -> MemoryManager:
    """Fresh MemoryManager backed by a scratch SQLite/JSONL pair."""
    return MemoryManager(
        jsonl_path=str(tmp_path / "notes.jsonl"),
        lance_path=str(tmp_path / "vec"),
    )


def test_ingest_rule_creates_note_and_relations(mm: MemoryManager) -> None:
    note, relations = ingest_rule(FIXTURES / "technique_loader.yar", mm, tier="warn")
    assert note is not None
    assert note.content.source_type == "yara"
    # Every CCCS technique rule in the fixtures maps to at least one
    # AttackPattern + technique YaraTag relation.
    rel_kinds = {r["rel"] for r in relations}
    assert "detects" in rel_kinds
    assert any(r["to_type"] == "YaraTag" for r in relations)


def test_ingest_rule_accepts_raw_text(mm: MemoryManager) -> None:
    src = (FIXTURES / "malware_hash.yar").read_text()
    note, _ = ingest_rule(src, mm, tier="non_cccs")
    assert note is not None


def test_ingest_rule_is_idempotent_on_content_sha256(mm: MemoryManager) -> None:
    """Second call for an unchanged rule returns the original note."""
    first, _ = ingest_rule(FIXTURES / "technique_loader.yar", mm, tier="warn")
    second, _ = ingest_rule(FIXTURES / "technique_loader.yar", mm, tier="warn")
    assert first is not None and second is not None
    assert first.id == second.id


def test_ingest_rules_dir_walks_tree(mm: MemoryManager) -> None:
    result = ingest_rules_dir(FIXTURES, mm, tier="warn")
    assert result["ingested"] >= 3
    assert result["errors"] == []


def test_ingest_rules_dir_second_run_skips_existing(mm: MemoryManager) -> None:
    """Re-ingesting the same tree bumps ``skipped`` via the idempotent path."""
    first = ingest_rules_dir(FIXTURES, mm, tier="warn")
    second = ingest_rules_dir(FIXTURES, mm, tier="warn")
    assert first["ingested"] >= 3
    assert second["ingested"] == 0
    assert second["skipped"] >= first["ingested"]


def test_ingest_rule_strict_rejects_plain_yara(mm: MemoryManager) -> None:
    """Plain YARA (no CCCS meta) is rejected under strict tier."""
    note, _ = ingest_rule(FIXTURES / "malware_hash.yar", mm, tier="strict")
    assert note is None


def test_ingest_rule_writes_note_findable_by_source_ref(mm: MemoryManager) -> None:
    note, _ = ingest_rule(FIXTURES / "technique_loader.yar", mm, tier="warn")
    assert note is not None
    assert note.content.source_ref.startswith("yara:MemoryModule:")
    refetched = mm.store.get_note_by_source_ref(note.content.source_ref)
    assert refetched is not None
    assert refetched.id == note.id
