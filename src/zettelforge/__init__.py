"""
ZettelForge: Agentic Memory System

A production-grade memory system for AI agents with:
- Vector semantic search
- Knowledge graph relationships
- Entity extraction and indexing
- RAG-as-answer synthesis
- Intent-based query routing

Community edition (MIT):
    >>> from zettelforge import MemoryManager
    >>> mm = MemoryManager()
    >>> mm.remember("Important information")
    >>> results = mm.recall("query")
    >>> synthesis = mm.synthesize("What do we know?")

Enterprise edition (ThreatRecall by Threatengram) adds:
    - STIX 2.1 TypeDB ontology
    - Blended retrieval (vector + graph)
    - OpenCTI integration
    - Sigma rule generation
    - Advanced synthesis formats
    - Multi-tenant auth
    See https://threatengram.com/enterprise
"""

from zettelforge.edition import (
    Edition,
    get_edition,
    is_enterprise,
    is_community,
    edition_name,
    EditionError,
)
from zettelforge.memory_manager import MemoryManager, get_memory_manager
from zettelforge.note_schema import MemoryNote
from zettelforge.vector_retriever import VectorRetriever
from zettelforge.synthesis_generator import SynthesisGenerator, get_synthesis_generator
from zettelforge.synthesis_validator import SynthesisValidator, get_synthesis_validator

from zettelforge.knowledge_graph import KnowledgeGraph, get_knowledge_graph
from zettelforge.ontology import (
    TypedEntityStore,
    OntologyValidator,
    get_ontology_store,
    get_ontology_validator,
    ENTITY_TYPES,
    RELATION_TYPES
)
from zettelforge.intent_classifier import IntentClassifier, get_intent_classifier, QueryIntent
from zettelforge.note_constructor import NoteConstructor
from zettelforge.fact_extractor import FactExtractor, ExtractedFact
from zettelforge.memory_updater import MemoryUpdater, UpdateOperation

__version__ = "2.1.0"
__all__ = [
    # Edition
    "Edition",
    "get_edition",
    "is_enterprise",
    "is_community",
    "edition_name",
    "EditionError",
    # Core
    "MemoryManager",
    "get_memory_manager",
    "MemoryNote",
    "VectorRetriever",
    "SynthesisGenerator",
    "get_synthesis_generator",
    "SynthesisValidator",
    "get_synthesis_validator",
    # Knowledge Graph
    "KnowledgeGraph",
    "get_knowledge_graph",
    # Ontology
    "TypedEntityStore",
    "OntologyValidator",
    "get_ontology_store",
    "get_ontology_validator",
    "ENTITY_TYPES",
    "RELATION_TYPES",
    # Intent Classification
    "IntentClassifier",
    "get_intent_classifier",
    "QueryIntent",
    # Note Constructor
    "NoteConstructor",
    # Two-Phase Pipeline
    "FactExtractor",
    "ExtractedFact",
    "MemoryUpdater",
    "UpdateOperation",
]

# ── Enterprise-only imports (conditional) ───────────────────────────────────
# These are only available when running Enterprise edition.
# Importing them in Community won't fail, but using them will raise EditionError.

if is_enterprise():
    from zettelforge.graph_retriever import GraphRetriever, ScoredResult
    from zettelforge.blended_retriever import BlendedRetriever
    from zettelforge.cti_integration import (
        CTIPlatformConnector,
        get_cti_connector,
        import_cti_to_memory,
        unified_recall,
    )
    from zettelforge.context_injection import (
        ContextInjector,
        get_context_injector,
        inject_for_task,
        ProactiveAgentMixin,
    )
    from zettelforge.sigma_generator import (
        SigmaGenerator,
        get_sigma_generator,
        generate_actor_rules,
        generate_sentinel_rules,
    )

    try:
        from zettelforge.typedb_client import TypeDBKnowledgeGraph, get_typedb_knowledge_graph
    except ImportError:
        pass  # TypeDB driver not installed

    __all__ += [
        # Enterprise: TypeDB
        "TypeDBKnowledgeGraph",
        "get_typedb_knowledge_graph",
        # Enterprise: Graph Retrieval
        "GraphRetriever",
        "ScoredResult",
        "BlendedRetriever",
        # Enterprise: CTI Integration
        "CTIPlatformConnector",
        "get_cti_connector",
        "import_cti_to_memory",
        "unified_recall",
        # Enterprise: Context Injection
        "ContextInjector",
        "get_context_injector",
        "inject_for_task",
        "ProactiveAgentMixin",
        # Enterprise: Sigma Generation
        "SigmaGenerator",
        "get_sigma_generator",
        "generate_actor_rules",
        "generate_sentinel_rules",
    ]