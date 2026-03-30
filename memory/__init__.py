"""
Roland Fleet Agentic Memory System
Roland Fleet Agentic Memory Architecture V1.0

A-MEM inspired Zettelkasten memory system with:
- Structured memory notes with LLM-generated semantic enrichment
- Concept linking (SUPPORTS, CONTRADICTS, EXTENDS, CAUSES, RELATED)
- Memory evolution with versioning and cold-tier archival
- Vector retrieval with domain filtering

Usage:
    from memory import get_memory_manager
    mm = get_memory_manager()
    
    # Create memory
    note = mm.remember("Content to remember", domain="security_ops")
    
    # Retrieve memories
    results = mm.recall("query", domain="security_ops")
    
    # Get formatted context for agent
    context = mm.get_context("query")
    
    # Ingest subagent output
    mm.ingest_subagent_output(task_id, output, observations)
"""
from memory_manager import MemoryManager, get_memory_manager

__all__ = ['MemoryManager', 'get_memory_manager']
