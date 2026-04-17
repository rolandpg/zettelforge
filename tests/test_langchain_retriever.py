"""
Tests for ZettelForge × LangChain retriever integration.

These tests require real embeddings for semantic recall to return results.
Skipped when ZETTELFORGE_EMBEDDING_PROVIDER=mock (CI default).
"""

import os

import pytest

from zettelforge import MemoryManager
from zettelforge.integrations.langchain_retriever import ZettelForgeRetriever

pytestmark = pytest.mark.skipif(
    os.environ.get("ZETTELFORGE_EMBEDDING_PROVIDER") == "mock",
    reason="LangChain retriever tests require real embeddings (not mock)",
)


@pytest.fixture
def memory_manager(tmp_path):
    """Create a MemoryManager with a temp directory for testing."""
    mm = MemoryManager(jsonl_path=str(tmp_path / "zf_test_db" / "notes.jsonl"))
    # Seed with CTI-relevant memories
    mm.remember(
        "APT28 (Fancy Bear) uses spear-phishing emails with credential-harvesting links. "
        "They have been observed using domains mimicking NATO and defense contractors.",
        domain="security_ops",
    )
    mm.remember(
        "CVE-2024-3094: XZ Utils backdoor in versions 5.6.0 and 5.6.1. "
        "CVSS score 10.0. Supply chain attack affecting SSH authentication.",
        domain="security_ops",
    )
    mm.remember(
        "Project Alpha migration to Kubernetes completed on 2024-03-15. "
        "All services running on EKS cluster us-east-1.",
        domain="project",
    )
    return mm


class TestZettelForgeRetriever:
    """Test suite for ZettelForgeRetriever."""

    def test_invoke_returns_documents(self, memory_manager):
        """retriever.invoke() returns LangChain Documents."""
        retriever = ZettelForgeRetriever(memory_manager=memory_manager, k=3)
        docs = retriever.invoke("APT28 spear-phishing techniques")

        assert isinstance(docs, list)
        assert len(docs) > 0
        # Each result should be a LangChain Document
        doc = docs[0]
        assert hasattr(doc, "page_content")
        assert hasattr(doc, "metadata")
        assert isinstance(doc.page_content, str)
        assert len(doc.page_content) > 0

    def test_metadata_fields(self, memory_manager):
        """Documents carry ZettelForge metadata fields."""
        retriever = ZettelForgeRetriever(memory_manager=memory_manager, k=5)
        # Use the exact CVE ID so fastembed + the CVE-ID regex recall path
        # reliably returns the seeded security_ops note; fuzzy queries like
        # "XZ Utils CVE" don't score highly enough on fastembed with a
        # 3-note corpus.
        docs = retriever.invoke("CVE-2024-3094")

        assert len(docs) > 0
        doc = docs[0]
        meta = doc.metadata
        # Core metadata fields from MemoryNote
        assert "note_id" in meta
        assert "source_type" in meta
        assert "domain" in meta
        assert "tier" in meta
        assert "confidence" in meta
        assert "keywords" in meta
        assert "tags" in meta
        # At least one result should be from security_ops (the CVE note)
        domains = [d.metadata["domain"] for d in docs]
        assert "security_ops" in domains

    def test_k_limits_results(self, memory_manager):
        """k parameter limits the number of results."""
        retriever_k1 = ZettelForgeRetriever(memory_manager=memory_manager, k=1)
        retriever_k5 = ZettelForgeRetriever(memory_manager=memory_manager, k=5)

        docs_k1 = retriever_k1.invoke("APT28")
        docs_k5 = retriever_k5.invoke("APT28")

        assert len(docs_k1) <= 1
        assert len(docs_k5) <= 5

    def test_domain_filter(self, memory_manager):
        """domain parameter filters results by domain."""
        retriever = ZettelForgeRetriever(memory_manager=memory_manager, k=10, domain="project")
        docs = retriever.invoke("migration Kubernetes")

        # All results should be from the "project" domain
        for doc in docs:
            if doc.metadata.get("domain"):
                assert doc.metadata["domain"] == "project"

    def test_empty_query(self, memory_manager):
        """Empty query returns results without crashing."""
        retriever = ZettelForgeRetriever(memory_manager=memory_manager, k=3)
        docs = retriever.invoke("")
        assert isinstance(docs, list)

    def test_serializable_config(self, memory_manager):
        """Retriever can be instantiated with config fields."""
        retriever = ZettelForgeRetriever(
            memory_manager=memory_manager,
            k=7,
            domain="security_ops",
            include_links=False,
            exclude_superseded=True,
        )
        assert retriever.k == 7
        assert retriever.domain == "security_ops"
        assert retriever.include_links is False
        assert retriever.exclude_superseded is True
