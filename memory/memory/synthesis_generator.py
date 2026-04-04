"""
Synthesis Generator — Phase 7 RAG-as-Answer Synthesis Layer
============================================================

Implements LLM-based answer synthesis using retrieved notes and knowledge graph context.
Supports multiple response formats: direct_answer, synthesized_brief, timeline_analysis, relationship_map.

Usage:
    from synthesis_generator import SynthesisGenerator
    from memory_manager import get_memory_manager

    gen = SynthesisGenerator()
    result = gen.synthesize(
        query="What do we know about UNC2452's supply chain activity?",
        memory_manager=mm,
        format="synthesized_brief"
    )
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

from vector_retriever import VectorRetriever
from knowledge_graph import get_knowledge_graph


MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
SCHEMA_FILE = MEMORY_DIR / "memory/synthesis_schema.json"


class SynthesisGenerator:
    """
    LLM-based answer synthesis with multiple output formats.
    Uses vector retrieval + knowledge graph traversal for comprehensive context.
    """

    def __init__(
        self,
        llm_model: str = "nemotron-3-nano",
        schema_file: str = None,
        max_context_tokens: int = 3000,
        confidence_threshold: float = 0.4
    ):
        self.llm_model = llm_model
        self.schema_file = Path(schema_file) if schema_file else SCHEMA_FILE
        self.max_context_tokens = max_context_tokens
        self.confidence_threshold = confidence_threshold

        self._schema = None
        self._llm_client = None
        self._lock = threading.RLock()
        self._load_schema()

    def _load_schema(self) -> None:
        """Load synthesis schema."""
        try:
            with open(self.schema_file) as f:
                self._schema = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._schema = self._default_schema()

    def _default_schema(self) -> Dict:
        """Default schema if file not found."""
        return {
            "response_formats": {
                "direct_answer": {
                    "schema": {
                        "properties": {
                            "answer": {"type": "string"},
                            "confidence": {"type": "number"},
                            "sources": {"type": "array"}
                        }
                    }
                },
                "synthesized_brief": {"schema": {"properties": {}}},
                "timeline_analysis": {"schema": {"properties": {}}},
                "relationship_map": {"schema": {"properties": {}}}
            },
            "validation_rules": {
                "min_sources": 1,
                "max_sources": 20,
                "min_confidence": 0.3,
                "max_summary_length": 500,
                "max_answer_length": 200
            }
        }

    def _get_llm_client(self):
        """Get or create LLM client."""
        if self._llm_client is None:
            # Use Ollama for synthesis
            try:
                import ollama
                self._llm_client = ollama
            except ImportError:
                self._llm_client = None
        return self._llm_client

    # -------------------------------------------------------------------------
    # Synthesis Entry Points
    # -------------------------------------------------------------------------

    def synthesize(
        self,
        query: str,
        memory_manager: 'MemoryManager' = None,
        memory_store: 'MemoryStore' = None,
        format: str = "direct_answer",
        k: int = 10,
        include_graph: bool = True,
        tier_filter: List[str] = None
    ) -> Dict:
        """
        Synthesize an answer from retrieved notes.

        Args:
            query: User query to answer
            memory_manager: MemoryManager instance (optional)
            memory_store: MemoryStore instance (optional)
            format: Response format (direct_answer, synthesized_brief, timeline_analysis, relationship_map)
            k: Number of notes to retrieve
            include_graph: Whether to include knowledge graph context
            tier_filter: Tier filter (A, B, C) - defaults to ["A", "B"]

        Returns:
            Synthesis result dictionary with answer, sources, metadata
        """
        start_time = time.time()

        # Get memory manager if not provided - lazy import to avoid circular
        mm = memory_manager
        if mm is None:
            from memory.memory_manager import get_memory_manager
            mm = get_memory_manager()

        # Get tier filter
        tier_filter = tier_filter or ["A", "B"]

        # Retrieve notes
        notes = self._retrieve_notes(query, mm, k, tier_filter)
        graph_context = None
        if include_graph:
            graph_context = self._get_graph_context(query, mm)

        # Build context
        context = self._build_context(notes, graph_context)

        # Generate synthesis
        synthesis = self._generate_synthesis(query, context, format)

        # Calculate metrics
        latency_ms = int((time.time() - start_time) * 1000)
        tokens_used = self._estimate_tokens(context)

        # Build result
        result = {
            "query": query,
            "format": format,
            "synthesis": synthesis,
            "metadata": {
                "query_id": hashlib.md5(query.encode()).hexdigest()[:12],
                "model_used": self.llm_model,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "confidence_threshold": self.confidence_threshold,
                "sources_count": len(notes),
                "tier_filter": tier_filter
            },
            "sources": [self._note_to_source(n) for n in notes[:10]]
        }

        return result

    def _retrieve_notes(
        self,
        query: str,
        mm: 'MemoryManager',
        k: int,
        tier_filter: List[str]
    ) -> List:
        """Retrieve notes via vector search."""
        if mm is None:
            from memory.memory_manager import get_memory_manager
            mm = get_memory_manager()
        results = mm.recall(query, k=k * 2)  # Get extra for filtering
        filtered = [n for n in results if n.metadata.tier in tier_filter]
        return filtered[:k]

    def _get_graph_context(self, query: str, mm: 'MemoryManager') -> Dict:
        """Get knowledge graph context for query entities."""
        kg = get_knowledge_graph()
        if mm is None:
            from memory.memory_manager import get_memory_manager
            mm = get_memory_manager()

        # Extract entities from query (simplified)
        entities = self._extract_entities(query)

        context = {
            "entities": entities,
            "relationships": [],
            "related_notes": []
        }

        # For each entity, get related notes from graph
        for entity in entities:
            for entity_type in ['actor', 'tool', 'cve', 'campaign']:
                node = kg.get_node_by_entity(entity_type, entity)
                if node:
                    # Get neighbors
                    neighbors = kg.get_neighbors(node['node_id'])
                    context["relationships"].extend([
                        {
                            "from": entity,
                            "to": n.get('entity_id', 'unknown'),
                            "relationship": "RELATED"
                        }
                        for n in neighbors
                    ])

        return context

    def _extract_entities(self, text: str) -> List[str]:
        """Extract potential entities from text."""
        import re
        entities = []

        # CVE patterns
        cve_pattern = r'(CVE-\d{4}-\d{4,})'
        for match in re.finditer(cve_pattern, text, re.IGNORECASE):
            entities.append(match.group(1).lower())

        # Actor-like patterns (simplified)
        actor_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        for match in re.finditer(actor_pattern, text):
            entities.append(match.group(1).lower())

        return entities[:10]

    def _build_context(self, notes: List, graph_context: Dict = None) -> str:
        """Build context string for LLM."""
        context_parts = []

        # Notes context
        for note in notes[:10]:
            context_parts.append(f"\n--- NOTE: {note.id} (Tier {note.metadata.tier}) ---")
            context_parts.append(f"Content: {note.content.raw[:500]}...")
            if note.semantic.context:
                context_parts.append(f"Summary: {note.semantic.context}")

        # Graph context
        if graph_context and graph_context.get("relationships"):
            context_parts.append("\n--- KNOWLEDGE GRAPH CONTEXT ---")
            for rel in graph_context["relationships"][:5]:
                context_parts.append(
                    f"{rel.get('from', 'unknown')} -> {rel.get('relationship', 'UNKNOWN')} -> {rel.get('to', 'unknown')}"
                )

        return "\n".join(context_parts)

    def _generate_synthesis(self, query: str, context: str, format: str) -> Dict:
        """Generate synthesis using LLM."""
        prompt = self._build_prompt(query, context, format)

        client = self._get_llm_client()
        if client:
            try:
                response = client.chat(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(format)},
                        {"role": "user", "content": prompt}
                    ],
                    format=self._get_json_format(format)
                )
                return json.loads(response.message.content)
            except Exception as e:
                # Fallback if LLM fails
                return self._fallback_synthesis(query, format)

        return self._fallback_synthesis(query, format)

    def _get_system_prompt(self, format: str) -> str:
        """Get system prompt for synthesis format."""
        prompts = {
            "direct_answer": "You are a cybersecurity intelligence assistant. Provide a concise, factual answer to the query based on the provided context. Include confidence level and cite sources.",
            "synthesized_brief": "You are a cybersecurity intelligence analyst. Create a comprehensive brief summarizing the key themes and evidence from the provided context.",
            "timeline_analysis": "You are a cybersecurity timeline analyst. Build a chronological timeline of events from the provided context, identifying key milestones.",
            "relationship_map": "You are a cybersecurity threat analyst. Map relationships between entities (actors, tools, CVEs, campaigns) from the provided context."
        }
        return prompts.get(format, prompts["direct_answer"])

    def _get_json_format(self, format: str) -> Dict:
        """Get JSON schema for LLM output."""
        formats = {
            "direct_answer": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "confidence": {"type": "number"},
                    "sources": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["answer", "confidence", "sources"]
            },
            "synthesized_brief": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "themes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "evidence": {"type": "string"}
                            }
                        }
                    },
                    "confidence": {"type": "number"}
                },
                "required": ["summary", "themes", "confidence"]
            },
            "timeline_analysis": {
                "type": "object",
                "properties": {
                    "timeline": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string"},
                                "event": {"type": "string"}
                            }
                        }
                    },
                    "confidence": {"type": "number"}
                },
                "required": ["timeline", "confidence"]
            },
            "relationship_map": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"}
                            }
                        }
                    },
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "type": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["entities", "relationships"]
            }
        }
        return formats.get(format, formats["direct_answer"])

    def _build_prompt(self, query: str, context: str, format: str) -> str:
        """Build LLM prompt."""
        return f"""Analyze the following cybersecurity intelligence context and provide a {format.replace('_', ' ')}.

QUERY:
{query}

CONTEXT:
{context}

INSTRUCTIONS:
- Extract only relevant information from the context
- Cite specific notes where applicable
- Be concise and factual
- Report confidence level based on evidence quality

Format your response as valid JSON matching the specified schema."""

    def _fallback_synthesis(self, query: str, format: str) -> Dict:
        """Fallback synthesis when LLM unavailable."""
        if format == "direct_answer":
            return {
                "answer": f"No specific answer found for: {query[:50]}...",
                "confidence": 0.0,
                "sources": []
            }
        elif format == "synthesized_brief":
            return {
                "summary": f"No synthesized brief available for: {query[:50]}...",
                "themes": [],
                "confidence": 0.0
            }
        else:
            return {"error": "No data available for synthesis"}

    def _note_to_source(self, note) -> Dict:
        """Convert note to source dictionary."""
        return {
            "note_id": note.id,
            "relevance_score": min(1.0, note.metadata.confidence),
            "quote": note.content.raw[:200] if note.content.raw else "",
            "tier": note.metadata.tier
        }

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 4 chars = 1 token)."""
        return len(text) // 4


# =============================================================================
# Global Access
# =============================================================================

_synthesis_gen: Optional[SynthesisGenerator] = None
_synthesis_lock = threading.Lock()


def get_synthesis_generator() -> SynthesisGenerator:
    """Get or create the global synthesis generator instance."""
    global _synthesis_gen
    if _synthesis_gen is None:
        with _synthesis_lock:
            if _synthesis_gen is None:
                _synthesis_gen = SynthesisGenerator()
    return _synthesis_gen


# =============================================================================
# CLI / Quick Test
# =============================================================================

if __name__ == "__main__":
    print("Synthesis Generator CLI")
    print("=" * 50)

    # Test with no data
    gen = SynthesisGenerator()
    print("\n1. Basic synthesis test:")
    result = gen.synthesize(
        query="What threat actors are active?",
        format="synthesized_brief",
        k=3
    )
    print(f"   Format: {result.get('format')}")
    print(f"   Sources: {result.get('metadata', {}).get('sources_count', 0)}")
    print(f"   Latency: {result.get('metadata', {}).get('latency_ms', 0)}ms")

    # Test direct answer
    print("\n2. Direct answer test:")
    result = gen.synthesize(
        query="Tell me about CVE-2024-3094",
        format="direct_answer",
        k=3
    )
    print(f"   Answer: {result.get('synthesis', {}).get('answer', 'N/A')[:100]}...")

    print("\n3. Synthesis Generator initialized successfully.")
