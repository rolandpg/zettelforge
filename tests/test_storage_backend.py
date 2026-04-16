"""Tests for StorageBackend ABC compliance.

Validates that the ABC cannot be instantiated directly and that it
declares every method required by the ZettelForge storage contract.
"""

import inspect

import pytest

from zettelforge.storage_backend import StorageBackend


class TestStorageBackendABC:
    """ABC structural tests -- no concrete backend needed."""

    def test_cannot_instantiate_abc(self):
        """StorageBackend is abstract and must not be instantiated."""
        with pytest.raises(TypeError):
            StorageBackend()

    def test_abc_defines_all_note_methods(self):
        required = [
            "write_note",
            "rewrite_note",
            "get_note_by_id",
            "get_note_by_source_ref",
            "iterate_notes",
            "get_notes_by_domain",
            "get_recent_notes",
            "count_notes",
            "delete_note",
        ]
        for method in required:
            assert hasattr(StorageBackend, method), f"Missing note method: {method}"
            assert callable(getattr(StorageBackend, method))

    def test_abc_defines_vector_sync_method(self):
        assert hasattr(StorageBackend, "reindex_vector")
        sig = inspect.signature(StorageBackend.reindex_vector)
        params = list(sig.parameters.keys())
        assert "note_id" in params
        assert "vector" in params

    def test_abc_defines_kg_methods(self):
        required = [
            "add_kg_node",
            "add_kg_edge",
            "get_kg_node",
            "get_kg_neighbors",
            "traverse_kg",
            "get_entity_timeline",
            "get_changes_since",
        ]
        for method in required:
            assert hasattr(StorageBackend, method), f"Missing KG method: {method}"

    def test_add_kg_edge_accepts_note_id(self):
        """BLOCKER-3: add_kg_edge must accept note_id for provenance."""
        sig = inspect.signature(StorageBackend.add_kg_edge)
        assert "note_id" in sig.parameters, "add_kg_edge missing note_id parameter"

    def test_abc_defines_entity_index_methods(self):
        required = [
            "add_entity_mapping",
            "remove_entity_mappings_for_note",
            "get_note_ids_for_entity",
            "search_entities",
        ]
        for method in required:
            assert hasattr(StorageBackend, method), f"Missing entity method: {method}"

    def test_abc_defines_lifecycle_methods(self):
        required = ["initialize", "close", "health_check", "export_snapshot"]
        for method in required:
            assert hasattr(StorageBackend, method), f"Missing lifecycle method: {method}"

    def test_health_check_has_default_implementation(self):
        """health_check() is concrete -- subclasses inherit a default."""
        # Verify it is NOT abstract (has a default body)
        abstracts = getattr(StorageBackend, "__abstractmethods__", set())
        assert "health_check" not in abstracts

    def test_abstract_methods_count(self):
        """Guard against accidentally dropping abstract methods."""
        abstracts = StorageBackend.__abstractmethods__
        # 9 note + 1 vector + 10 KG + 4 entity + 3 lifecycle = 27
        assert len(abstracts) == 27, (
            f"Expected 27 abstract methods, got {len(abstracts)}: {sorted(abstracts)}"
        )

    def test_minimal_concrete_subclass(self):
        """A subclass implementing all abstract methods can be instantiated."""

        class _Stub(StorageBackend):
            def write_note(self, note): ...
            def rewrite_note(self, note): ...
            def get_note_by_id(self, note_id): ...
            def get_note_by_source_ref(self, source_ref): ...
            def iterate_notes(self): ...
            def get_notes_by_domain(self, domain): ...
            def get_recent_notes(self, limit=10): ...
            def count_notes(self): ...
            def delete_note(self, note_id): ...
            def reindex_vector(self, note_id, vector): ...
            def add_kg_node(self, entity_type, entity_value, properties=None): ...
            def add_kg_edge(self, from_type, from_value, to_type, to_value, relationship, note_id=None, properties=None): ...
            def get_kg_node(self, entity_type, entity_value): ...
            def get_kg_node_by_id(self, node_id): ...
            def get_kg_neighbors(self, entity_type, entity_value, relationship=None): ...
            def traverse_kg(self, start_type, start_value, max_depth=2): ...
            def get_entity_timeline(self, entity_type, entity_value): ...
            def get_changes_since(self, timestamp): ...
            def get_causal_edges(self, entity_type, entity_value, max_depth=3, max_visited=50): ...
            def get_incoming_causal(self, entity_type, entity_value, max_depth=3, max_visited=50): ...
            def add_entity_mapping(self, entity_type, entity_value, note_id): ...
            def remove_entity_mappings_for_note(self, note_id): ...
            def get_note_ids_for_entity(self, entity_type, entity_value): ...
            def search_entities(self, query, limit=10): ...
            def initialize(self): ...
            def close(self): ...
            def export_snapshot(self, output_path): ...

        stub = _Stub()
        health = stub.health_check()
        assert health["status"] == "ok"
        assert health["backend"] == "_Stub"
