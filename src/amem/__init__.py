"""
A-MEM: Agentic Memory System

A production-grade memory system for AI agents with:
- Vector semantic search
- Knowledge graph relationships
- Entity extraction and indexing
- RAG-as-answer synthesis

Example:
    >>> from amem import MemoryManager
    >>> mm = MemoryManager()
    >>> mm.remember("Important information")
    >>> results = mm.recall("query")
"""

from amem.memory_manager import MemoryManager, get_memory_manager
from amem.note_schema import MemoryNote
from amem.vector_retriever import VectorRetriever

__version__ = "1.0.0-alpha.1"
__all__ = [
    "MemoryManager",
    "get_memory_manager",
    "MemoryNote",
    "VectorRetriever",
]
