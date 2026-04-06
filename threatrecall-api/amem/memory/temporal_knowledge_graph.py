"""
Temporal Knowledge Graph — Phase 6 Temporal Extension
========================================================

Extends the Knowledge Graph with explicit temporal relationships:
- [Event A] → PRECEDES → [Event B]
- [Event A] → FOLLOWS → [Event B]  
- [Event A] → CONCURRENT_WITH → [Event B]
- [Event A] → CAUSES → [Event B] (temporal+causal)

Enables chronological reasoning over the CTI knowledge base:
- Find events before/after a given timestamp
- Trace attack chains through time
- Detect temporal patterns in campaigns
- Validate timeline consistency

Usage:
    tkg = TemporalKnowledgeGraph()
    
    # Add events with timestamps
    event1 = tkg.add_event(
        event_id="initial_access_001",
        event_type="initial_access",
        timestamp="2024-03-15T09:30:00Z",
        properties={"technique": "T1566.001", "target": "email_gateway"}
    )
    
    event2 = tkg.add_event(
        event_id="execution_001", 
        event_type="execution",
        timestamp="2024-03-15T10:15:00Z",
        properties={"technique": "T1059.001", "parent": "initial_access_001"}
    )
    
    # Create temporal relationship
    tkg.add_temporal_edge("initial_access_001", "execution_001", "PRECEDES")
    
    # Query temporal relationships
    chain = tkg.get_event_chain("initial_access_001")
    before = tkg.get_events_before("2024-03-15T10:00:00Z")
    after = tkg.get_events_after("2024-03-15T09:00:00Z")
"""

import json
import uuid
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
import threading

from knowledge_graph import KnowledgeGraph, get_knowledge_graph


# =============================================================================
# Temporal Relationship Types
# =============================================================================

class TemporalRelationship(str, Enum):
    """Temporal relationship types between events."""
    # Primary relationships
    PRECEDES = "PRECEDES"              # Event A happens before Event B
    FOLLOWS = "FOLLOWS"                # Event A happens after Event B (inverse of PRECEDES)
    CONCURRENT_WITH = "CONCURRENT_WITH"  # Events happen at roughly the same time
    IMMEDIATELY_PRECEDED_BY = "IMMEDIATELY_PRECEDED_BY"  # Event B immediately follows Event A
    IMMEDIATELY_FOLLOWED_BY = "IMMEDIATELY_FOLLOWED_BY"  # Event A immediately follows Event B
    OVERLAPS = "OVERLAPS"              # Event A time range overlaps with Event B
    CONTAINS = "CONTAINS"              # Event A time range contains Event B
    CAUSES = "CAUSES"                  # Event A causes Event B (temporal + causal)
    ENABLES = "ENABLES"                # Event A enables/preconditions Event B
    LEADS_TO = "LEADS_TO"              # Event A probabilistically leads to Event B
    
    # Inverse relationships (for completeness)
    CONTAINED_BY = "CONTAINED_BY"      # Event A is contained by Event B
    CAUSED_BY = "CAUSED_BY"            # Event A is caused by Event B
    ENABLED_BY = "ENABLED_BY"          # Event A is enabled by Event B
    LED_FROM = "LED_FROM"              # Event A probabilistically led from Event B


# Temporal relationship inverses
TEMPORAL_INVERSE = {
    TemporalRelationship.PRECEDES: TemporalRelationship.FOLLOWS,
    TemporalRelationship.FOLLOWS: TemporalRelationship.PRECEDES,
    TemporalRelationship.CONCURRENT_WITH: TemporalRelationship.CONCURRENT_WITH,
    TemporalRelationship.IMMEDIATELY_PRECEDED_BY: TemporalRelationship.IMMEDIATELY_FOLLOWED_BY,
    TemporalRelationship.IMMEDIATELY_FOLLOWED_BY: TemporalRelationship.IMMEDIATELY_PRECEDED_BY,
    TemporalRelationship.OVERLAPS: TemporalRelationship.OVERLAPS,
    TemporalRelationship.CONTAINS: TemporalRelationship.CONTAINED_BY,
    TemporalRelationship.CONTAINED_BY: TemporalRelationship.CONTAINS,
    TemporalRelationship.CAUSES: TemporalRelationship.CAUSED_BY,
    TemporalRelationship.CAUSED_BY: TemporalRelationship.CAUSES,
    TemporalRelationship.ENABLES: TemporalRelationship.ENABLED_BY,
    TemporalRelationship.ENABLED_BY: TemporalRelationship.ENABLES,
    TemporalRelationship.LEADS_TO: TemporalRelationship.LED_FROM,
    TemporalRelationship.LED_FROM: TemporalRelationship.LEADS_TO,
}


# =============================================================================
# Event Types for CTI
# =============================================================================

class EventType(str, Enum):
    """CTI event types for temporal modeling."""
    # MITRE ATT&CK Lifecycle
    RECONNAISSANCE = "reconnaissance"           # T1595-T1599
    RESOURCE_DEVELOPMENT = "resource_development"  # T1583-T1589
    INITIAL_ACCESS = "initial_access"           # T1566-T1195
    EXECUTION = "execution"                     # T1053-T1204
    PERSISTENCE = "persistence"                 # T1098-T1547
    PRIVILEGE_ESCALATION = "privilege_escalation"  # T1548-T1078
    DEFENSE_EVASION = "defense_evasion"         # T1218-T1222
    CREDENTIAL_ACCESS = "credential_access"     # T1003-T1552
    DISCOVERY = "discovery"                     # T1087-T1120
    LATERAL_MOVEMENT = "lateral_movement"       # T1021-T1210
    COLLECTION = "collection"                   # T1005-T1125
    C2 = "command_and_control"                  # T1071-T1219
    EXFILTRATION = "exfiltration"               # T1020-T1048
    IMPACT = "impact"                           # T1485-T1496
    
    # External Events
    CVE_PUBLISHED = "cve_published"
    PATCH_RELEASED = "patch_released"
    THREAT_REPORT = "threat_report"
    CAMPAIGN_START = "campaign_start"
    CAMPAIGN_END = "campaign_end"
    INCIDENT_DECLARED = "incident_declared"
    INCIDENT_RESOLVED = "incident_resolved"
    
    # Custom
    CUSTOM = "custom"


# =============================================================================
# Temporal Knowledge Graph
# =============================================================================

class TemporalKnowledgeGraph:
    """
    Knowledge graph with explicit temporal relationships.
    
    Extends the base KnowledgeGraph with:
    - Event nodes with temporal properties
    - Temporal relationship edges (PRECEDES, FOLLOWS, etc.)
    - Time-based queries and traversal
    - Timeline construction and validation
    """
    
    def __init__(
        self,
        kg: KnowledgeGraph = None,
        temporal_edges_file: str = None
    ):
        """
        Initialize temporal knowledge graph.
        
        Args:
            kg: Base KnowledgeGraph instance (creates new if None)
            temporal_edges_file: Path to temporal edges JSONL file
        """
        self.kg = kg if kg else get_knowledge_graph()
        
        # Temporal edges storage
        if temporal_edges_file:
            self.temporal_edges_file = Path(temporal_edges_file)
        else:
            self.temporal_edges_file = Path(self.kg.edges_file).parent / "kg_temporal_edges.jsonl"
        
        # In-memory temporal index
        self._temporal_edges: Dict[str, Dict] = {}  # edge_id -> edge data
        self._event_timestamps: Dict[str, datetime] = {}  # event_id -> timestamp
        self._temporal_from: Dict[str, List[Dict]] = {}  # event_id -> outgoing temporal edges
        self._temporal_to: Dict[str, List[Dict]] = {}    # event_id -> incoming temporal edges
        
        self._lock = threading.RLock()
        self._load_temporal_edges()
    
    # -------------------------------------------------------------------------
    # Event Management
    # -------------------------------------------------------------------------
    
    def add_event(
        self,
        event_id: str,
        event_type: str,
        timestamp: str,
        properties: Dict = None,
        duration_minutes: Optional[int] = None
    ) -> Dict:
        """
        Add an event node with temporal properties.
        
        Args:
            event_id: Unique event identifier (e.g., "incident_001_recon")
            event_type: EventType or string
            timestamp: ISO 8601 timestamp (e.g., "2024-03-15T09:30:00Z")
            properties: Additional event properties
            duration_minutes: Optional event duration
            
        Returns:
            Created event node dictionary
        """
        with self._lock:
            # Parse and validate timestamp
            parsed_ts = self._parse_timestamp(timestamp)
            if not parsed_ts:
                raise ValueError(f"Invalid timestamp format: {timestamp}")
            
            # Build event properties
            props = properties or {}
            props.update({
                'event_id': event_id,
                'event_type': event_type,
                'timestamp': timestamp,
                'timestamp_unix': parsed_ts.timestamp(),
            })
            if duration_minutes:
                props['duration_minutes'] = duration_minutes
                props['end_timestamp'] = (parsed_ts + timedelta(minutes=duration_minutes)).isoformat()
            
            # Add as node in base KG
            node = self.kg.add_node('event', event_id, props)
            
            # Index timestamp
            self._event_timestamps[event_id] = parsed_ts
            
            return node
    
    def get_event(self, event_id: str) -> Optional[Dict]:
        """Get an event node by its ID."""
        return self.kg.get_node_by_entity('event', event_id)
    
    def get_event_timestamp(self, event_id: str) -> Optional[datetime]:
        """Get the parsed timestamp for an event."""
        with self._lock:
            return self._event_timestamps.get(event_id)
    
    # -------------------------------------------------------------------------
    # Temporal Relationships
    # -------------------------------------------------------------------------
    
    def add_temporal_edge(
        self,
        from_event_id: str,
        to_event_id: str,
        relationship: TemporalRelationship,
        properties: Dict = None,
        auto_inverse: bool = True
    ) -> Dict:
        """
        Add a temporal relationship between two events.
        
        Args:
            from_event_id: Source event ID
            to_event_id: Target event ID  
            relationship: Temporal relationship type
            properties: Optional edge properties
            auto_inverse: Automatically create inverse relationship
            
        Returns:
            Created temporal edge dictionary
        """
        with self._lock:
            # Validate events exist
            from_event = self.get_event(from_event_id)
            to_event = self.get_event(to_event_id)
            
            if not from_event:
                raise ValueError(f"Source event not found: {from_event_id}")
            if not to_event:
                raise ValueError(f"Target event not found: {to_event_id}")
            
            # Validate temporal consistency
            from_ts = self._event_timestamps.get(from_event_id)
            to_ts = self._event_timestamps.get(to_event_id)
            
            if from_ts and to_ts:
                self._validate_temporal_consistency(from_ts, to_ts, relationship)
            
            # Create edge
            edge_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat() + 'Z'
            
            edge = {
                'edge_id': edge_id,
                'edge_type': 'temporal',
                'from_event_id': from_event_id,
                'to_event_id': to_event_id,
                'relationship_type': relationship.value if isinstance(relationship, TemporalRelationship) else relationship,
                'properties': properties or {},
                'created_at': now
            }
            
            self._temporal_edges[edge_id] = edge
            self._temporal_from.setdefault(from_event_id, []).append(edge)
            self._temporal_to.setdefault(to_event_id, []).append(edge)
            
            # Create inverse relationship
            if auto_inverse:
                inverse_rel = TEMPORAL_INVERSE.get(TemporalRelationship(edge['relationship_type']))
                if inverse_rel:
                    inverse_edge_id = str(uuid.uuid4())
                    inverse_edge = {
                        'edge_id': inverse_edge_id,
                        'edge_type': 'temporal',
                        'from_event_id': to_event_id,
                        'to_event_id': from_event_id,
                        'relationship_type': inverse_rel.value,
                        'properties': {'inverse_of': edge_id, **(properties or {})},
                        'created_at': now
                    }
                    self._temporal_edges[inverse_edge_id] = inverse_edge
                    self._temporal_from.setdefault(to_event_id, []).append(inverse_edge)
                    self._temporal_to.setdefault(from_event_id, []).append(inverse_edge)
            
            self._save_temporal_edges()
            return edge
    
    def _validate_temporal_consistency(
        self,
        from_ts: datetime,
        to_ts: datetime,
        relationship: TemporalRelationship
    ) -> bool:
        """Validate that a temporal relationship is chronologically consistent."""
        rel = relationship.value if isinstance(relationship, TemporalRelationship) else relationship
        
        # PRECEDES: from must be before to
        if rel in ['PRECEDES', 'CAUSES', 'ENABLES', 'LEADS_TO', 'IMMEDIATELY_FOLLOWED_BY']:
            if from_ts >= to_ts:
                raise ValueError(
                    f"Temporal inconsistency: {rel} requires from_time < to_time, "
                    f"got {from_ts} >= {to_ts}"
                )
        
        # FOLLOWS: from must be after to
        elif rel in ['FOLLOWS', 'IMMEDIATELY_PRECEDED_BY']:
            if from_ts <= to_ts:
                raise ValueError(
                    f"Temporal inconsistency: {rel} requires from_time > to_time, "
                    f"got {from_ts} <= {to_ts}"
                )
        
        # CONCURRENT_WITH: times should be close (within 1 hour default)
        elif rel == 'CONCURRENT_WITH':
            time_diff = abs((from_ts - to_ts).total_seconds())
            if time_diff > 3600:  # 1 hour threshold
                # Warning only, not error
                pass  # Allow with warning logged elsewhere
        
        return True
    
    def get_temporal_edges_from(
        self,
        event_id: str,
        relationship_type: str = None
    ) -> List[Dict]:
        """Get outgoing temporal edges from an event."""
        with self._lock:
            edges = self._temporal_from.get(event_id, [])
            if relationship_type:
                edges = [e for e in edges if e['relationship_type'] == relationship_type]
            return edges
    
    def get_temporal_edges_to(
        self,
        event_id: str,
        relationship_type: str = None
    ) -> List[Dict]:
        """Get incoming temporal edges to an event."""
        with self._lock:
            edges = self._temporal_to.get(event_id, [])
            if relationship_type:
                edges = [e for e in edges if e['relationship_type'] == relationship_type]
            return edges
    
    def get_preceding_events(self, event_id: str, max_depth: int = 5) -> List[Dict]:
        """
        Get all events that precede the given event.
        
        Args:
            event_id: Event to find predecessors for
            max_depth: Maximum traversal depth
            
        Returns:
            List of preceding event dictionaries with edge info
        """
        return self._traverse_temporal(
            event_id,
            ['PRECEDES', 'CAUSES', 'ENABLES', 'IMMEDIATELY_FOLLOWED_BY'],
            direction='incoming',
            max_depth=max_depth
        )
    
    def get_following_events(self, event_id: str, max_depth: int = 5) -> List[Dict]:
        """
        Get all events that follow the given event.
        
        Args:
            event_id: Event to find successors for
            max_depth: Maximum traversal depth
            
        Returns:
            List of following event dictionaries with edge info
        """
        return self._traverse_temporal(
            event_id,
            ['PRECEDES', 'CAUSES', 'ENABLES', 'IMMEDIATELY_FOLLOWED_BY'],
            direction='outgoing',
            max_depth=max_depth
        )
    
    def _traverse_temporal(
        self,
        event_id: str,
        relationship_types: List[str],
        direction: str,
        max_depth: int
    ) -> List[Dict]:
        """Traverse temporal edges from an event."""
        with self._lock:
            results = []
            visited = set()
            queue = [(event_id, 0, None)]  # (event_id, depth, via_edge)
            
            while queue:
                current_id, depth, via_edge = queue.pop(0)
                
                if current_id in visited or depth > max_depth:
                    continue
                visited.add(current_id)
                
                if depth > 0:  # Skip starting node
                    event = self.get_event(current_id)
                    if event:
                        results.append({
                            'event': event,
                            'depth': depth,
                            'via_edge': via_edge,
                            'hops_from_start': depth
                        })
                
                # Get next edges
                if direction == 'outgoing':
                    edges = self._temporal_from.get(current_id, [])
                else:
                    edges = self._temporal_to.get(current_id, [])
                
                for edge in edges:
                    if edge['relationship_type'] in relationship_types:
                        if direction == 'outgoing':
                            next_id = edge['to_event_id']
                        else:
                            next_id = edge['from_event_id']
                        
                        if next_id not in visited:
                            queue.append((next_id, depth + 1, edge))
            
            return results
    
    def get_event_chain(self, event_id: str, max_length: int = 10) -> List[Dict]:
        """
        Get the full event chain starting from an event.
        
        Traces both backward (what led to this) and forward (what followed).
        Returns events in chronological order.
        
        Args:
            event_id: Starting event
            max_length: Maximum chain length
            
        Returns:
            List of events in chronological order
        """
        with self._lock:
            # Get preceding events (what led to this)
            before = self.get_preceding_events(event_id, max_depth=max_length // 2)
            
            # Get following events (what resulted from this)
            after = self.get_following_events(event_id, max_depth=max_length // 2)
            
            # Build chain
            chain = []
            
            # Add preceding events (oldest first)
            for entry in reversed(before):
                chain.append(entry['event'])
            
            # Add starting event
            start_event = self.get_event(event_id)
            if start_event:
                chain.append(start_event)
            
            # Add following events
            for entry in after:
                chain.append(entry['event'])
            
            # Sort by timestamp
            chain.sort(key=lambda e: e['properties'].get('timestamp_unix', 0))
            
            return chain[:max_length]
    
    # -------------------------------------------------------------------------
    # Time-Based Queries
    # -------------------------------------------------------------------------
    
    def get_events_before(
        self,
        timestamp: str,
        event_type: str = None,
        k: int = 100
    ) -> List[Dict]:
        """
        Get all events that occurred before a given timestamp.
        
        Args:
            timestamp: ISO 8601 timestamp
            event_type: Optional filter by event type
            k: Maximum results
            
        Returns:
            List of events before timestamp (newest first)
        """
        with self._lock:
            ts = self._parse_timestamp(timestamp)
            if not ts:
                return []
            
            results = []
            for event_id, event_ts in self._event_timestamps.items():
                if event_ts < ts:
                    event = self.get_event(event_id)
                    if event:
                        if event_type and event['properties'].get('event_type') != event_type:
                            continue
                        results.append(event)
            
            # Sort by timestamp descending (newest first)
            results.sort(
                key=lambda e: e['properties'].get('timestamp_unix', 0),
                reverse=True
            )
            return results[:k]
    
    def get_events_after(
        self,
        timestamp: str,
        event_type: str = None,
        k: int = 100
    ) -> List[Dict]:
        """
        Get all events that occurred after a given timestamp.
        
        Args:
            timestamp: ISO 8601 timestamp
            event_type: Optional filter by event type
            k: Maximum results
            
        Returns:
            List of events after timestamp (oldest first)
        """
        with self._lock:
            ts = self._parse_timestamp(timestamp)
            if not ts:
                return []
            
            results = []
            for event_id, event_ts in self._event_timestamps.items():
                if event_ts > ts:
                    event = self.get_event(event_id)
                    if event:
                        if event_type and event['properties'].get('event_type') != event_type:
                            continue
                        results.append(event)
            
            # Sort by timestamp ascending (oldest first)
            results.sort(key=lambda e: e['properties'].get('timestamp_unix', 0))
            return results[:k]
    
    def get_events_between(
        self,
        start_timestamp: str,
        end_timestamp: str,
        event_type: str = None
    ) -> List[Dict]:
        """
        Get all events within a time range.
        
        Args:
            start_timestamp: ISO 8601 start timestamp
            end_timestamp: ISO 8601 end timestamp
            event_type: Optional filter by event type
            
        Returns:
            List of events in time range (chronological order)
        """
        with self._lock:
            start_ts = self._parse_timestamp(start_timestamp)
            end_ts = self._parse_timestamp(end_timestamp)
            
            if not start_ts or not end_ts:
                return []
            
            results = []
            for event_id, event_ts in self._event_timestamps.items():
                if start_ts <= event_ts <= end_ts:
                    event = self.get_event(event_id)
                    if event:
                        if event_type and event['properties'].get('event_type') != event_type:
                            continue
                        results.append(event)
            
            # Sort chronologically
            results.sort(key=lambda e: e['properties'].get('timestamp_unix', 0))
            return results
    
    def get_events_by_date(
        self,
        date: str,
        event_type: str = None
    ) -> List[Dict]:
        """
        Get all events on a specific date.
        
        Args:
            date: Date string (YYYY-MM-DD)
            event_type: Optional filter by event type
            
        Returns:
            List of events on that date
        """
        start = f"{date}T00:00:00Z"
        end = f"{date}T23:59:59Z"
        return self.get_events_between(start, end, event_type)
    
    # -------------------------------------------------------------------------
    # Timeline Construction
    # -------------------------------------------------------------------------
    
    def build_timeline(
        self,
        event_ids: List[str],
        include_temporal_edges: bool = True
    ) -> Dict:
        """
        Build a timeline from a set of events.
        
        Args:
            event_ids: List of event IDs to include
            include_temporal_edges: Whether to include temporal relationships
            
        Returns:
            Timeline dictionary with events and edges
        """
        with self._lock:
            events = []
            for event_id in event_ids:
                event = self.get_event(event_id)
                if event:
                    events.append(event)
            
            # Sort by timestamp
            events.sort(key=lambda e: e['properties'].get('timestamp_unix', 0))
            
            timeline = {
                'events': events,
                'start_time': events[0]['properties'].get('timestamp') if events else None,
                'end_time': events[-1]['properties'].get('timestamp') if events else None,
                'event_count': len(events),
            }
            
            if include_temporal_edges:
                edges = []
                for event_id in event_ids:
                    for edge in self._temporal_from.get(event_id, []):
                        if edge['to_event_id'] in event_ids:
                            edges.append(edge)
                timeline['temporal_edges'] = edges
                timeline['edge_count'] = len(edges)
            
            return timeline
    
    def infer_temporal_edges(self, event_ids: List[str] = None) -> List[Dict]:
        """
        Automatically infer temporal edges between events based on timestamps.
        
        Creates PRECEDES edges between events that are chronologically ordered.
        
        Args:
            event_ids: Optional list of event IDs to process (all events if None)
            
        Returns:
            List of created temporal edges
        """
        with self._lock:
            if event_ids is None:
                event_ids = list(self._event_timestamps.keys())
            
            # Get events with timestamps
            events_with_ts = []
            for event_id in event_ids:
                ts = self._event_timestamps.get(event_id)
                if ts:
                    events_with_ts.append((event_id, ts))
            
            # Sort by timestamp
            events_with_ts.sort(key=lambda x: x[1])
            
            # Create PRECEDES edges between consecutive events
            created_edges = []
            for i in range(len(events_with_ts) - 1):
                from_id = events_with_ts[i][0]
                to_id = events_with_ts[i + 1][0]
                
                # Check if edge already exists
                existing = self._has_temporal_edge(from_id, to_id, 'PRECEDES')
                if not existing:
                    edge = self.add_temporal_edge(from_id, to_id, TemporalRelationship.PRECEDES)
                    created_edges.append(edge)
            
            return created_edges
    
    def _has_temporal_edge(self, from_id: str, to_id: str, rel_type: str) -> bool:
        """Check if a temporal edge already exists."""
        edges = self._temporal_from.get(from_id, [])
        for edge in edges:
            if edge['to_event_id'] == to_id and edge['relationship_type'] == rel_type:
                return True
        return False
    
    def detect_temporal_patterns(self, event_ids: List[str] = None) -> List[Dict]:
        """
        Detect common temporal patterns in events.
        
        Patterns:
        - Chain: A -> B -> C (sequential progression)
        - Fan-out: A -> B, A -> C (single event leads to multiple)
        - Fan-in: A -> C, B -> C (multiple events converge)
        - Diamond: A -> B, A -> C, B -> D, C -> D
        
        Args:
            event_ids: Optional list of event IDs (all if None)
            
        Returns:
            List of detected patterns
        """
        with self._lock:
            if event_ids is None:
                event_ids = list(self._event_timestamps.keys())
            
            patterns = []
            
            for event_id in event_ids:
                # Check for chain pattern
                following = self.get_following_events(event_id, max_depth=2)
                if len(following) >= 2:
                    patterns.append({
                        'type': 'chain',
                        'start_event': event_id,
                        'length': len(following) + 1,
                        'events': [event_id] + [e['event']['properties']['event_id'] for e in following]
                    })
                
                # Check for fan-out
                outgoing = self.get_temporal_edges_from(event_id)
                if len(outgoing) >= 2:
                    patterns.append({
                        'type': 'fan_out',
                        'source_event': event_id,
                        'target_count': len(outgoing),
                        'targets': [e['to_event_id'] for e in outgoing]
                    })
                
                # Check for fan-in
                incoming = self.get_temporal_edges_to(event_id)
                if len(incoming) >= 2:
                    patterns.append({
                        'type': 'fan_in',
                        'target_event': event_id,
                        'source_count': len(incoming),
                        'sources': [e['from_event_id'] for e in incoming]
                    })
            
            return patterns
    
    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------
    
    def _load_temporal_edges(self) -> None:
        """Load temporal edges from disk."""
        with self._lock:
            self._temporal_edges.clear()
            self._temporal_from.clear()
            self._temporal_to.clear()
            
            if self.temporal_edges_file.exists():
                with open(self.temporal_edges_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                edge = json.loads(line)
                                self._temporal_edges[edge['edge_id']] = edge
                                self._temporal_from.setdefault(edge['from_event_id'], []).append(edge)
                                self._temporal_to.setdefault(edge['to_event_id'], []).append(edge)
                            except (json.JSONDecodeError, KeyError):
                                continue
    
    def _save_temporal_edges(self) -> None:
        """Persist temporal edges to disk."""
        tmp_file = self.temporal_edges_file.with_suffix('.jsonl.tmp')
        with open(tmp_file, 'w') as f:
            for edge in self._temporal_edges.values():
                f.write(json.dumps(edge) + '\n')
        tmp_file.rename(self.temporal_edges_file)
    
    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    
    def _parse_timestamp(self, timestamp: str) -> Optional[datetime]:
        """Parse an ISO 8601 timestamp."""
        try:
            # Handle various ISO formats
            ts = timestamp.replace('Z', '+00:00')
            if '+' in ts:
                return datetime.fromisoformat(ts.replace('+00:00', ''))
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return None
    
    def stats(self) -> Dict:
        """Return temporal graph statistics."""
        with self._lock:
            base_stats = self.kg.stats()
            
            # Count temporal edges by type
            edge_counts = {}
            for edge in self._temporal_edges.values():
                rt = edge['relationship_type']
                edge_counts[rt] = edge_counts.get(rt, 0) + 1
            
            # Get event count
            event_nodes = self.kg.get_nodes_by_entity_type('event')
            
            return {
                **base_stats,
                'temporal_edges': len(self._temporal_edges),
                'events_with_temporal_data': len(event_nodes),
                'temporal_edge_types': edge_counts,
                'temporal_edges_file': str(self.temporal_edges_file)
            }
    
    def clear_temporal_data(self) -> None:
        """Clear all temporal edges and event data."""
        with self._lock:
            self._temporal_edges.clear()
            self._temporal_from.clear()
            self._temporal_to.clear()
            self._event_timestamps.clear()
            self.temporal_edges_file.unlink(missing_ok=True)


# =============================================================================
# Global Access
# =============================================================================

_tkg: Optional[TemporalKnowledgeGraph] = None
_tkg_lock = threading.Lock()


def get_temporal_knowledge_graph() -> TemporalKnowledgeGraph:
    """Get or create the global temporal knowledge graph instance."""
    global _tkg
    if _tkg is None:
        with _tkg_lock:
            if _tkg is None:
                _tkg = TemporalKnowledgeGraph()
    return _tkg


# =============================================================================
# CLI / Quick Test
# =============================================================================

if __name__ == "__main__":
    print("Temporal Knowledge Graph CLI")
    print("=" * 60)
    
    tkg = TemporalKnowledgeGraph()
    
    # Create sample attack chain
    print("\n1. Creating attack chain events...")
    
    events = [
        ("recon_001", "reconnaissance", "2024-03-15T08:00:00Z", {"technique": "T1595"}),
        ("initial_access_001", "initial_access", "2024-03-15T09:30:00Z", {"technique": "T1566.001"}),
        ("execution_001", "execution", "2024-03-15T10:15:00Z", {"technique": "T1059.001"}),
        ("persistence_001", "persistence", "2024-03-15T11:00:00Z", {"technique": "T1547.001"}),
        ("c2_001", "command_and_control", "2024-03-15T12:30:00Z", {"technique": "T1071.001"}),
    ]
    
    for event_id, event_type, ts, props in events:
        tkg.add_event(event_id, event_type, ts, props)
        print(f"   Created: {event_id} ({event_type})")
    
    # Add temporal relationships
    print("\n2. Adding temporal edges (PRECEDES)...")
    for i in range(len(events) - 1):
        from_id = events[i][0]
        to_id = events[i + 1][0]
        tkg.add_temporal_edge(from_id, to_id, TemporalRelationship.PRECEDES)
        print(f"   {from_id} → PRECEDES → {to_id}")
    
    # Add causal relationship
    print("\n3. Adding causal edge (CAUSES)...")
    tkg.add_temporal_edge("initial_access_001", "execution_001", TemporalRelationship.CAUSES)
    print("   initial_access_001 → CAUSES → execution_001")
    
    # Query temporal relationships
    print("\n4. Querying temporal relationships...")
    
    chain = tkg.get_event_chain("initial_access_001")
    print(f"   Event chain from initial_access_001:")
    for event in chain:
        print(f"      {event['properties']['event_id']} @ {event['properties']['timestamp']}")
    
    preceding = tkg.get_preceding_events("execution_001")
    print(f"\n   Events preceding execution_001:")
    for entry in preceding:
        print(f"      {entry['event']['properties']['event_id']} (depth {entry['depth']})")
    
    following = tkg.get_following_events("initial_access_001")
    print(f"\n   Events following initial_access_001:")
    for entry in following:
        print(f"      {entry['event']['properties']['event_id']} (depth {entry['depth']})")
    
    # Time-based queries
    print("\n5. Time-based queries...")
    before = tkg.get_events_before("2024-03-15T10:00:00Z")
    print(f"   Events before 10:00: {len(before)}")
    
    after = tkg.get_events_after("2024-03-15T10:00:00Z")
    print(f"   Events after 10:00: {len(after)}")
    
    # Detect patterns
    print("\n6. Detecting temporal patterns...")
    patterns = tkg.detect_temporal_patterns()
    for pattern in patterns:
        print(f"   {pattern['type']}: {pattern.get('events', pattern.get('targets', pattern.get('sources')))}")
    
    # Stats
    print("\n7. Temporal graph statistics:")
    stats = tkg.stats()
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Events: {stats['events_with_temporal_data']}")
    print(f"   Temporal edges: {stats['temporal_edges']}")
    print(f"   Edge types: {stats['temporal_edge_types']}")
    
    print("\nTest complete!")
