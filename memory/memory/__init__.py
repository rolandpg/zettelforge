"""
A-MEM Memory Module — Phase 6 Complete
========================================

Agentic Memory system with:
- Core memory management (Phases 1-5)
- Knowledge graph (Phase 6)
- Temporal relationships (Phase 6 Extension)
- IEP 2.0 governance

Exports:
    KnowledgeGraph — Base knowledge graph storage
    TemporalKnowledgeGraph — Temporal-aware knowledge graph
    GraphRetriever — Graph-based information retrieval
    TemporalGraphRetriever — Temporal-aware graph retrieval
    OntologyValidator — Schema validation
    IEPManager — IEP 2.0 policy management
"""

from .knowledge_graph import KnowledgeGraph, get_knowledge_graph
from .temporal_knowledge_graph import (
    TemporalKnowledgeGraph,
    get_temporal_knowledge_graph,
    TemporalRelationship,
    EventType
)
from .graph_retriever import GraphRetriever, IEPStore
from .temporal_graph_retriever import TemporalGraphRetriever, get_temporal_graph_retriever
from .ontology_validator import OntologyValidator

try:
    from .iep_policy import IEPManager, HANDLING_LEVELS, ACTION_LEVELS, SHARING_LEVELS, LICENSE_LEVELS
except ImportError:
    # IEP policy may not be available
    IEPManager = None
    HANDLING_LEVELS = []
    ACTION_LEVELS = []
    SHARING_LEVELS = []
    LICENSE_LEVELS = []

__all__ = [
    # Knowledge Graph
    'KnowledgeGraph',
    'get_knowledge_graph',
    
    # Temporal Knowledge Graph
    'TemporalKnowledgeGraph',
    'get_temporal_knowledge_graph',
    'TemporalRelationship',
    'EventType',
    
    # Retrievers
    'GraphRetriever',
    'IEPStore',
    'TemporalGraphRetriever',
    'get_temporal_graph_retriever',
    
    # Validation
    'OntologyValidator',
    
    # IEP
    'IEPManager',
    'HANDLING_LEVELS',
    'ACTION_LEVELS',
    'SHARING_LEVELS',
    'LICENSE_LEVELS',
]

__version__ = '1.6.0'
__phase__ = 'Phase 6 Complete — Temporal Knowledge Graph'
