"""
Temporal Graph Retriever — Phase 6 Temporal Query Interface
===============================================================

Implements temporal-aware retrieval for the knowledge graph:
- Query events by time ranges
- Retrieve event chains and sequences  
- Find causally related events
- Temporal pattern detection
- Timeline reconstruction

Usage:
    retriever = TemporalGraphRetriever()
    
    # Get events in time range
    events = retriever.get_events_between("2024-03-01", "2024-03-31")
    
    # Get event chain
    chain = retriever.get_event_chain("initial_access_001")
    
    # Find causal ancestors
    ancestors = retriever.get_causal_ancestors("impact_001")
    
    # Reconstruct attack timeline
    timeline = retriever.reconstruct_timeline("campaign_001")
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
import threading

from knowledge_graph import KnowledgeGraph, get_knowledge_graph
from temporal_knowledge_graph import (
    TemporalKnowledgeGraph, 
    get_temporal_knowledge_graph,
    TemporalRelationship,
    EventType
)


class TemporalGraphRetriever:
    """
    Graph-based information retriever with temporal awareness.
    
    Combines base graph retrieval with temporal querying capabilities
    to support chronological reasoning over CTI data.
    """
    
    def __init__(
        self,
        kg: KnowledgeGraph = None,
        tkg: TemporalKnowledgeGraph = None
    ):
        """
        Initialize temporal graph retriever.
        
        Args:
            kg: Base KnowledgeGraph instance
            tkg: TemporalKnowledgeGraph instance
        """
        self.kg = kg if kg else get_knowledge_graph()
        self.tkg = tkg if tkg else get_temporal_knowledge_graph()
        self._lock = threading.RLock()
    
    # -------------------------------------------------------------------------
    # Event Retrieval by Time
    # -------------------------------------------------------------------------
    
    def get_events_between(
        self,
        start_time: str,
        end_time: str,
        event_types: List[str] = None,
        actor: str = None,
        technique: str = None
    ) -> List[Dict]:
        """
        Get events within a time range with optional filters.
        
        Args:
            start_time: ISO 8601 start timestamp
            end_time: ISO 8601 end timestamp
            event_types: Optional list of event types to filter
            actor: Optional actor name filter
            technique: Optional MITRE technique ID filter
            
        Returns:
            List of matching events in chronological order
        """
        events = self.tkg.get_events_between(start_time, end_time)
        
        # Apply filters
        if event_types:
            events = [e for e in events if e['properties'].get('event_type') in event_types]
        if actor:
            events = [e for e in events if e['properties'].get('actor') == actor]
        if technique:
            events = [e for e in events if e['properties'].get('technique') == technique]
        
        return events
    
    def get_events_before_event(
        self,
        event_id: str,
        k: int = 10,
        event_types: List[str] = None
    ) -> List[Dict]:
        """
        Get events that occurred before a specific event.
        
        Args:
            event_id: Reference event ID
            k: Maximum results
            event_types: Optional filter by event types
            
        Returns:
            List of preceding events (newest first)
        """
        event = self.tkg.get_event(event_id)
        if not event:
            return []
        
        timestamp = event['properties'].get('timestamp')
        if not timestamp:
            return []
        
        events = self.tkg.get_events_before(timestamp, event_type=None, k=k * 2)
        
        if event_types:
            events = [e for e in events if e['properties'].get('event_type') in event_types]
        
        return events[:k]
    
    def get_events_after_event(
        self,
        event_id: str,
        k: int = 10,
        event_types: List[str] = None
    ) -> List[Dict]:
        """
        Get events that occurred after a specific event.
        
        Args:
            event_id: Reference event ID
            k: Maximum results
            event_types: Optional filter by event types
            
        Returns:
            List of following events (oldest first)
        """
        event = self.tkg.get_event(event_id)
        if not event:
            return []
        
        timestamp = event['properties'].get('timestamp')
        if not timestamp:
            return []
        
        events = self.tkg.get_events_after(timestamp, event_type=None, k=k * 2)
        
        if event_types:
            events = [e for e in events if e['properties'].get('event_type') in event_types]
        
        return events[:k]
    
    # -------------------------------------------------------------------------
    # Temporal Chain Retrieval
    # -------------------------------------------------------------------------
    
    def get_event_chain(
        self,
        event_id: str,
        max_length: int = 10,
        include_causal: bool = True
    ) -> Dict:
        """
        Get the complete event chain for an event.
        
        Args:
            event_id: Starting event
            max_length: Maximum chain length
            include_causal: Include CAUSES relationships
            
        Returns:
            Chain dictionary with events, edges, and metadata
        """
        chain = self.tkg.get_event_chain(event_id, max_length)
        
        # Build edge list
        edges = []
        for i in range(len(chain) - 1):
            from_id = chain[i]['properties']['event_id']
            to_id = chain[i + 1]['properties']['event_id']
            
            # Find temporal edges between them
            temporal_edges = self.tkg.get_temporal_edges_from(from_id)
            for edge in temporal_edges:
                if edge['to_event_id'] == to_id:
                    edges.append(edge)
        
        return {
            'events': chain,
            'edges': edges,
            'start_event': chain[0]['properties']['event_id'] if chain else None,
            'end_event': chain[-1]['properties']['event_id'] if chain else None,
            'length': len(chain),
            'time_span_minutes': self._calculate_time_span(chain)
        }
    
    def _calculate_time_span(self, events: List[Dict]) -> Optional[int]:
        """Calculate time span in minutes for a list of events."""
        if len(events) < 2:
            return None
        
        timestamps = []
        for event in events:
            ts = event['properties'].get('timestamp_unix')
            if ts:
                timestamps.append(ts)
        
        if len(timestamps) < 2:
            return None
        
        return int((max(timestamps) - min(timestamps)) / 60)
    
    def get_attack_chain(
        self,
        start_event_id: str,
        max_depth: int = 5
    ) -> List[Dict]:
        """
        Get the attack chain starting from an initial event.
        
        Follows PRECEDES, CAUSES, and ENABLES relationships to trace
        the progression of an attack.
        
        Args:
            start_event_id: Starting event (typically initial_access)
            max_depth: Maximum chain depth
            
        Returns:
            List of events in attack progression order
        """
        chain = self.tkg.get_following_events(start_event_id, max_depth)
        
        # Filter to attack-related events only
        attack_types = [
            'initial_access', 'execution', 'persistence',
            'privilege_escalation', 'defense_evasion', 'credential_access',
            'discovery', 'lateral_movement', 'collection',
            'command_and_control', 'exfiltration', 'impact'
        ]
        
        return [
            entry for entry in chain
            if entry['event']['properties'].get('event_type') in attack_types
        ]
    
    # -------------------------------------------------------------------------
    # Causal Retrieval
    # -------------------------------------------------------------------------
    
    def get_causal_ancestors(
        self,
        event_id: str,
        max_depth: int = 5
    ) -> List[Dict]:
        """
        Get all events that causally led to the given event.
        
        Follows CAUSES and ENABLES relationships backward in time.
        
        Args:
            event_id: Event to find causal ancestors for
            max_depth: Maximum traversal depth
            
        Returns:
            List of causal ancestor events with depth info
        """
        with self._lock:
            results = []
            visited = set()
            queue = [(event_id, 0)]
            
            while queue:
                current_id, depth = queue.pop(0)
                
                if current_id in visited or depth > max_depth:
                    continue
                visited.add(current_id)
                
                # Get incoming CAUSES and ENABLES edges
                edges = self.tkg.get_temporal_edges_to(current_id)
                causal_edges = [
                    e for e in edges
                    if e['relationship_type'] in ['CAUSES', 'ENABLES', 'LEADS_TO']
                ]
                
                for edge in causal_edges:
                    ancestor_id = edge['from_event_id']
                    if ancestor_id not in visited:
                        ancestor = self.tkg.get_event(ancestor_id)
                        if ancestor:
                            results.append({
                                'event': ancestor,
                                'depth': depth + 1,
                                'relationship': edge['relationship_type'],
                                'via_edge': edge
                            })
                            queue.append((ancestor_id, depth + 1))
            
            return results
    
    def get_causal_descendants(
        self,
        event_id: str,
        max_depth: int = 5
    ) -> List[Dict]:
        """
        Get all events that causally resulted from the given event.
        
        Args:
            event_id: Event to find causal descendants for
            max_depth: Maximum traversal depth
            
        Returns:
            List of causal descendant events with depth info
        """
        with self._lock:
            results = []
            visited = set()
            queue = [(event_id, 0)]
            
            while queue:
                current_id, depth = queue.pop(0)
                
                if current_id in visited or depth > max_depth:
                    continue
                visited.add(current_id)
                
                # Get outgoing CAUSES and ENABLES edges
                edges = self.tkg.get_temporal_edges_from(current_id)
                causal_edges = [
                    e for e in edges
                    if e['relationship_type'] in ['CAUSES', 'ENABLES', 'LEADS_TO']
                ]
                
                for edge in causal_edges:
                    descendant_id = edge['to_event_id']
                    if descendant_id not in visited:
                        descendant = self.tkg.get_event(descendant_id)
                        if descendant:
                            results.append({
                                'event': descendant,
                                'depth': depth + 1,
                                'relationship': edge['relationship_type'],
                                'via_edge': edge
                            })
                            queue.append((descendant_id, depth + 1))
            
            return results
    
    def find_root_causes(self, event_id: str, max_depth: int = 5) -> List[Dict]:
        """
        Find root cause events for a given event.
        
        Root causes are events with no further causal ancestors
        (typically initial_access or reconnaissance).
        
        Args:
            event_id: Event to analyze
            max_depth: Maximum traversal depth
            
        Returns:
            List of root cause events
        """
        ancestors = self.get_causal_ancestors(event_id, max_depth)
        
        # Find ancestors that have no further causal predecessors
        root_causes = []
        for entry in ancestors:
            ancestor_id = entry['event']['properties']['event_id']
            further_ancestors = self.get_causal_ancestors(ancestor_id, max_depth=1)
            if not further_ancestors:
                root_causes.append(entry)
        
        return root_causes
    
    # -------------------------------------------------------------------------
    # Timeline Reconstruction
    # -------------------------------------------------------------------------
    
    def reconstruct_timeline(
        self,
        campaign_id: str = None,
        actor: str = None,
        incident_id: str = None,
        time_range: Tuple[str, str] = None
    ) -> Dict:
        """
        Reconstruct a complete timeline from available data.
        
        Args:
            campaign_id: Campaign to reconstruct timeline for
            actor: Actor to filter by
            incident_id: Specific incident ID
            time_range: (start, end) time range tuple
            
        Returns:
            Timeline dictionary with events, phases, and patterns
        """
        with self._lock:
            events = []
            
            # Get events by criteria
            if campaign_id:
                # Get campaign node and related events
                campaign = self.kg.get_node_by_entity('campaign', campaign_id)
                if campaign:
                    # Find events linked to this campaign
                    for node in self.kg.get_nodes_by_entity_type('event'):
                        if node['properties'].get('campaign') == campaign_id:
                            events.append(node)
            
            elif time_range:
                events = self.tkg.get_events_between(time_range[0], time_range[1])
            
            elif actor:
                all_events = self.kg.get_nodes_by_entity_type('event')
                events = [e for e in all_events if e['properties'].get('actor') == actor]
            
            else:
                events = self.kg.get_nodes_by_entity_type('event')
            
            if not events:
                return {'events': [], 'phases': [], 'patterns': []}
            
            # Sort chronologically
            events.sort(key=lambda e: e['properties'].get('timestamp_unix', 0))
            
            # Identify attack phases
            phases = self._identify_attack_phases(events)
            
            # Detect patterns
            patterns = self.tkg.detect_temporal_patterns(
                [e['properties']['event_id'] for e in events]
            )
            
            # Calculate metrics
            time_span = self._calculate_time_span(events)
            
            return {
                'events': events,
                'phases': phases,
                'patterns': patterns,
                'metrics': {
                    'total_events': len(events),
                    'time_span_minutes': time_span,
                    'unique_techniques': len(set(
                        e['properties'].get('technique') for e in events
                        if e['properties'].get('technique')
                    )),
                    'unique_actors': len(set(
                        e['properties'].get('actor') for e in events
                        if e['properties'].get('actor')
                    ))
                }
            }
    
    def _identify_attack_phases(self, events: List[Dict]) -> List[Dict]:
        """
        Identify attack lifecycle phases from events.
        
        Groups events into MITRE ATT&CK phases based on event types.
        """
        phase_order = [
            'reconnaissance', 'resource_development', 'initial_access',
            'execution', 'persistence', 'privilege_escalation',
            'defense_evasion', 'credential_access', 'discovery',
            'lateral_movement', 'collection', 'command_and_control',
            'exfiltration', 'impact'
        ]
        
        phases = []
        current_phase = None
        phase_events = []
        
        for event in events:
            event_type = event['properties'].get('event_type')
            
            if event_type in phase_order:
                if event_type != current_phase:
                    # Save previous phase
                    if current_phase and phase_events:
                        phases.append({
                            'phase': current_phase,
                            'events': phase_events,
                            'start_time': phase_events[0]['properties'].get('timestamp'),
                            'end_time': phase_events[-1]['properties'].get('timestamp'),
                            'event_count': len(phase_events)
                        })
                    
                    # Start new phase
                    current_phase = event_type
                    phase_events = [event]
                else:
                    phase_events.append(event)
        
        # Save last phase
        if current_phase and phase_events:
            phases.append({
                'phase': current_phase,
                'events': phase_events,
                'start_time': phase_events[0]['properties'].get('timestamp'),
                'end_time': phase_events[-1]['properties'].get('timestamp'),
                'event_count': len(phase_events)
            })
        
        return phases
    
    # -------------------------------------------------------------------------
    # Pattern-Based Retrieval
    # -------------------------------------------------------------------------
    
    def find_similar_attack_patterns(
        self,
        event_chain: List[str],
        similarity_threshold: float = 0.7
    ) -> List[Dict]:
        """
        Find similar attack patterns in the knowledge graph.
        
        Args:
            event_chain: List of event type strings to match
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of similar patterns with similarity scores
        """
        with self._lock:
            # Get all campaigns/incidents with event chains
            all_events = self.kg.get_nodes_by_entity_type('event')
            
            # Group by campaign/incident
            campaigns = {}
            for event in all_events:
                campaign = event['properties'].get('campaign') or event['properties'].get('incident_id')
                if campaign:
                    campaigns.setdefault(campaign, []).append(event)
            
            # Compare chains
            matches = []
            for campaign_id, campaign_events in campaigns.items():
                # Build chain for this campaign
                campaign_chain = [
                    e['properties'].get('event_type') 
                    for e in sorted(campaign_events, key=lambda x: x['properties'].get('timestamp_unix', 0))
                ]
                
                # Calculate similarity
                similarity = self._chain_similarity(event_chain, campaign_chain)
                
                if similarity >= similarity_threshold:
                    matches.append({
                        'campaign_id': campaign_id,
                        'similarity': similarity,
                        'chain': campaign_chain,
                        'event_count': len(campaign_events)
                    })
            
            # Sort by similarity
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            return matches[:10]
    
    def _chain_similarity(self, chain1: List[str], chain2: List[str]) -> float:
        """Calculate similarity between two event chains using sequence matching."""
        if not chain1 or not chain2:
            return 0.0
        
        # Simple Jaccard-like similarity for now
        set1 = set(chain1)
        set2 = set(chain2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    # -------------------------------------------------------------------------
    # Query Interface
    # -------------------------------------------------------------------------
    
    def query(
        self,
        query_type: str,
        **kwargs
    ) -> Dict:
        """
        Unified query interface for temporal graph retrieval.
        
        Args:
            query_type: Type of query to execute
            **kwargs: Query-specific parameters
            
        Returns:
            Query results dictionary
        """
        if query_type == 'events_between':
            return {'events': self.get_events_between(**kwargs)}
        
        elif query_type == 'event_chain':
            return self.get_event_chain(**kwargs)
        
        elif query_type == 'attack_chain':
            return {'chain': self.get_attack_chain(**kwargs)}
        
        elif query_type == 'causal_ancestors':
            return {'ancestors': self.get_causal_ancestors(**kwargs)}
        
        elif query_type == 'causal_descendants':
            return {'descendants': self.get_causal_descendants(**kwargs)}
        
        elif query_type == 'root_causes':
            return {'root_causes': self.find_root_causes(**kwargs)}
        
        elif query_type == 'timeline':
            return self.reconstruct_timeline(**kwargs)
        
        elif query_type == 'similar_patterns':
            return {'patterns': self.find_similar_attack_patterns(**kwargs)}
        
        else:
            return {'error': f'Unknown query type: {query_type}'}
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    def stats(self) -> Dict:
        """Return retriever statistics."""
        tkg_stats = self.tkg.stats()
        
        # Get event type distribution
        events = self.kg.get_nodes_by_entity_type('event')
        type_counts = {}
        for event in events:
            et = event['properties'].get('event_type', 'unknown')
            type_counts[et] = type_counts.get(et, 0) + 1
        
        # Get temporal relationship distribution
        temporal_counts = tkg_stats.get('temporal_edge_types', {})
        
        return {
            **tkg_stats,
            'event_type_distribution': type_counts,
            'temporal_relationship_distribution': temporal_counts,
            'total_events': len(events)
        }
    
    # -------------------------------------------------------------------------
    # CLI / Quick Test
    # -------------------------------------------------------------------------
    
    def quick_test(self):
        """Quick self-test of the temporal retriever."""
        print("TemporalGraphRetriever Quick Test")
        print("=" * 60)
        
        stats = self.stats()
        print(f"\nRetriever Statistics:")
        print(f"  Total events: {stats.get('total_events', 0)}")
        print(f"  Temporal edges: {stats.get('temporal_edges', 0)}")
        print(f"  Event types: {list(stats.get('event_type_distribution', {}).keys())}")
        
        # Test timeline reconstruction
        print("\nTesting timeline reconstruction...")
        timeline = self.reconstruct_timeline()
        print(f"  Events in timeline: {len(timeline.get('events', []))}")
        print(f"  Phases identified: {len(timeline.get('phases', []))}")
        
        print("\nTest complete.")


# =============================================================================
# Global Access
# =============================================================================

_tgr: Optional[TemporalGraphRetriever] = None
_tgr_lock = threading.Lock()


def get_temporal_graph_retriever() -> TemporalGraphRetriever:
    """Get or create the global temporal graph retriever instance."""
    global _tgr
    if _tgr is None:
        with _tgr_lock:
            if _tgr is None:
                _tgr = TemporalGraphRetriever()
    return _tgr


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    retriever = TemporalGraphRetriever()
    retriever.quick_test()
