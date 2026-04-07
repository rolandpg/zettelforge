"""
ZettelForge: Agentic Memory System

A production-grade memory system for AI agents with:
- Vector semantic search
- Knowledge graph relationships
- Entity extraction and indexing
- RAG-as-answer synthesis (Phase 7)

Example:
    >>> from zettelforge import MemoryManager
    >>> mm = MemoryManager()
    >>> mm.remember("Important information")
    >>> results = mm.recall("query")
    >>> synthesis = mm.synthesize("What do we know?")
"""

from zettelforge.memory_manager import MemoryManager, get_memory_manager
from zettelforge.note_schema import MemoryNote
from zettelforge.vector_retriever import VectorRetriever
from zettelforge.synthesis_generator import SynthesisGenerator, get_synthesis_generator
from zettelforge.synthesis_validator import SynthesisValidator, get_synthesis_validator

from zettelforge.knowledge_graph import KnowledgeGraph, get_knowledge_graph

__version__ = "1.0.0-alpha.3"
__all__ = [
    "MemoryManager",
    "get_memory_manager",
    "MemoryNote",
    "VectorRetriever",
    "SynthesisGenerator",
    "get_synthesis_generator",
    "SynthesisValidator",
    "get_synthesis_validator",
    "KnowledgeGraph",
    "get_knowledge_graph"
]
