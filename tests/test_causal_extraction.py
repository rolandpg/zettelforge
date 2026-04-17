#!/usr/bin/env python3
"""
Test causal triple extraction in ZettelForge.
Validates Task 1: LLM-based causal edge extraction from consolidation pass.
"""

import sys
import os
import tempfile
from unittest.mock import patch
# Package installed via pip - no sys.path manipulation needed

from zettelforge import MemoryManager
import zettelforge.knowledge_graph as knowledge_graph_module


def test_causal_extraction():
    print("=== Causal Triple Extraction Test ===\n")

    # Isolate the JSONL KnowledgeGraph singleton + AMEM_DATA_DIR so this
    # test can't leak state into or inherit state from neighbors.
    old_data_dir = os.environ.get("AMEM_DATA_DIR")
    old_kg_instance = knowledge_graph_module._kg_instance
    tmpdir = tempfile.mkdtemp()
    os.environ["AMEM_DATA_DIR"] = tmpdir
    knowledge_graph_module._kg_instance = None
    mm = MemoryManager(jsonl_path=f"{tmpdir}/notes.jsonl", lance_path=f"{tmpdir}/vectordb")

    try:
        # Test CTI content with causal relationships
        cti_content = """
        APT28 (Fancy Bear) continues to target critical infrastructure in the energy sector.
        The group uses DROPBEAR malware for initial access and Cobalt Strike for lateral movement.
        CVE-2024-1111 enables remote code execution on unpatched Microsoft Exchange servers.
        APT48 used this vulnerability to compromise Server ALPHA on May 15, 2024.
        The incident was contained after patching on May 20, 2024.
        """

        print("Input CTI content:")
        print(cti_content[:300])
        print()

        # Prompt-routed mock: returns parseable causal triples for the causal
        # extraction prompt and a benign empty object for the NER prompt.
        # Routes by prompt content rather than call order so it's robust to
        # enrichment-worker ordering. Mirrors the AI-3/AI-4 pattern from
        # tests/test_two_phase_e2e.py.
        def _route(prompt, *args, **kwargs):
            if "Extract causal relationships" in prompt:
                return (
                    '[{"subject":"APT28","relation":"uses","object":"DROPBEAR"},'
                    ' {"subject":"APT28","relation":"targets","object":"critical infrastructure"},'
                    ' {"subject":"CVE-2024-1111","relation":"enables","object":"remote code execution"}]'
                )
            if "Extract named entities" in prompt:
                return "{}"
            return ""

        # sync=True runs causal extraction inline, so the backend write
        # completes before we query it (no enrichment-queue race).
        with patch("zettelforge.llm_client.generate", side_effect=_route):
            note, status = mm.remember(cti_content, domain="cti", sync=True)

        print(f"Note created: {note.id}")
        print(f"Status: {status}")
        print()

        # Read causal edges straight out of the storage backend, which is
        # where store_causal_edges actually writes them (backend=self.store
        # path in NoteConstructor.store_causal_edges). The prior version
        # read the JSONL KnowledgeGraph singleton, which the SQLite backend
        # never populates — so the assertion couldn't catch pipeline
        # regressions.
        causal_edges = mm.store.get_causal_edges("intrusion_set", "apt28", max_depth=3)
        print("=== Causal Edges from APT28 (backend query) ===")
        print(f"Count: {len(causal_edges)}")
        for edge in causal_edges:
            print(
                f"  ✓ apt28 --[{edge.get('relationship')}]-->"
                f" (edge_type={edge.get('edge_type')}, note_id={edge.get('note_id')})"
            )

        print("\n=== Test Complete ===")
        # Guards the full causal extraction + storage pipeline: LLM call,
        # JSON parse, relation-allowlist filter, alias resolve, backend
        # persist. Regressions in any of these will drop edge count to 0.
        assert len(causal_edges) > 0, (
            "Expected >=1 causal edge from APT28 after sync=True remember. "
            "Pipeline broken somewhere: LLM generate, extract_json, "
            "CAUSAL_RELATIONS allowlist, AliasResolver, or add_kg_edge."
        )
    finally:
        knowledge_graph_module._kg_instance = old_kg_instance
        if old_data_dir is None:
            os.environ.pop("AMEM_DATA_DIR", None)
        else:
            os.environ["AMEM_DATA_DIR"] = old_data_dir


if __name__ == "__main__":
    test_causal_extraction()
    sys.exit(0)
