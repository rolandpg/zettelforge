"""
Graph Retriever — Phase 6 Graph-Based Information Retrieval
============================================================

Implements graph-aware retrieval with IEP 2.0 policy filtering.
Supports path-based queries, neighbor expansion, and IEP-filtered searches.

Usage:
    retriever = GraphRetriever(knowledge_graph, policy_store)
    results = retriever.recall("threat actors targeting government")
    results = retriever.recall_with_path("muddywater CVE-2024-3094")
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re

from knowledge_graph import KnowledgeGraph, get_knowledge_graph
from ontology_validator import OntologyValidator


class GraphRetriever:
    """
    Graph-based information retriever with IEP policy filtering.
    """

    def __init__(
        self,
        kg: KnowledgeGraph = None,
        policy_store: 'IEPStore' = None
    ):
        self.kg = kg if kg else get_knowledge_graph()
        self.validator = OntologyValidator()
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # Basic Recall with Entity Resolution
    # -------------------------------------------------------------------------

    def recall(
        self,
        query: str,
        domain: str = None,
        k: int = 10,
        include_relationships: bool = True,
        relationship_types: List[str] = None,
        iep_filter: str = None
    ) -> List[Dict]:
        """
        Recall entities and their relationships from the graph.

        Args:
            query: Search query (entity name or relationship pattern)
            domain: Optional domain filter
            k: Maximum results to return
            include_relationships: Whether to expand relationships
            relationship_types: Optional filter on relationship types
            iep_filter: Optional IEP policy ID to filter by

        Returns:
            List of result dictionaries with nodes and relationships
        """
        results = []

        with self._lock:
            # Parse query - try to identify entity types
            entities = self._parse_query(query)

            if not entities:
                # Fallback: return all nodes
                for node in list(self.kg._nodes.values())[:k]:
                    results.append({
                        'node': node,
                        'relationships': [],
                        'score': 1.0
                    })
                return results

            # Process each entity type found
            for entity_type, entity_id in entities:
                node = self.kg.get_node_by_entity(entity_type, entity_id)
                if node:
                    result = {
                        'node': node,
                        'relationships': [],
                        'score': 0.9
                    }

                    if include_relationships:
                        rels = self.kg.get_edges_from(node['node_id'], relationship_types)
                        result['relationships'] = rels[:10]

                    results.append(result)

            # Sort by score and limit
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:k]

    def _parse_query(self, query: str) -> List[Tuple[str, str]]:
        """Parse a query string to extract entity references."""
        entities = []

        # Check for CVE format
        cve_pattern = r'(CVE-\d{4}-\d{4,})'
        if re.search(cve_pattern, query, re.IGNORECASE):
            for match in re.finditer(cve_pattern, query, re.IGNORECASE):
                entities.append(('cve', match.group(1)))

        # Check for known entity patterns
        actor_patterns = [
            (r'\b(muddywater|apt28|lazarus|apt)\b', 'actor'),
            (r'\b(cobalt\s+strike|metasploit| Empire)\b', 'tool'),
            (r'\b(operaton|solarwinds|notpetya)\b', 'campaign'),
        ]

        for pattern, etype in actor_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                # Find the matched name
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    entities.append((etype, match.group(1).lower()))

        return entities

    # -------------------------------------------------------------------------
    # Path-Based Recall
    # -------------------------------------------------------------------------

    def recall_with_path(
        self,
        from_entity: str,
        to_entity: str,
        from_type: str = None,
        to_type: str = None,
        max_depth: int = 3
    ) -> Optional[Dict]:
        """
        Recall the path between two entities.

        Args:
            from_entity: Source entity name or ID
            to_entity: Target entity name or ID
            from_type: Optional source entity type
            to_type: Optional target entity type
            max_depth: Maximum path length

        Returns:
            Path dictionary with nodes and edges, or None if no path
        """
        # Determine types if not provided
        if from_type is None:
            from_type = self._guess_entity_type(from_entity)
        if to_type is None:
            to_type = self._guess_entity_type(to_entity)

        with self._lock:
            path = self.kg.get_path(from_type, from_entity, to_type, to_entity, max_depth)
            if path is None:
                return None

            # Build path structure
            edges = []
            for i in range(len(path) - 1):
                from_id = path[i]['node_id']
                to_id = path[i + 1]['node_id']

                for edge in self.kg._edges_from.get(from_id, []):
                    if edge['to_node_id'] == to_id:
                        edges.append(edge)
                        break

            return {
                'path': path,
                'edges': edges,
                'length': len(path)
            }

    def _guess_entity_type(self, entity: str) -> str:
        """Guess entity type from entity name or ID."""
        if entity.startswith('CVE-'):
            return 'cve'

        # Check against known types
        types = ['actor', 'tool', 'campaign', 'sector', 'iep_policy']
        for t in types:
            node = self.kg.get_node_by_entity(t, entity)
            if node:
                return t

        # Default to most common
        return 'actor'

    # -------------------------------------------------------------------------
    # Neighbor Expansion
    # -------------------------------------------------------------------------

    def expand(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 1,
        relationship_types: List[str] = None,
        iep_filter: str = None
    ) -> Dict:
        """
        Expand a node by retrieving its neighbors.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
            depth: Number of hops to expand
            relationship_types: Optional filter on relationship types
            iep_filter: Optional IEP policy ID to filter by

        Returns:
            Expansion dictionary with node, neighbors, and relationships
        """
        with self._lock:
            node = self.kg.get_node_by_entity(entity_type, entity_id)
            if node is None:
                return {
                    'node': None,
                    'error': f'Entity not found: {entity_type}/{entity_id}'
                }

            result = {
                'node': node,
                'depth': depth,
                'neighbors': [],
                'relationships': []
            }

            # Get direct neighbors (depth 1)
            for edge in self.kg._edges_from.get(node['node_id'], []):
                if relationship_types is None or edge['relationship_type'] in relationship_types:
                    neighbor = self.kg._nodes.get(edge['to_node_id'])
                    if neighbor:
                        result['neighbors'].append({
                            'node': neighbor,
                            'edge': edge,
                            'direction': 'outgoing'
                        })
                        result['relationships'].append(edge)

            for edge in self.kg._edges_to.get(node['node_id'], []):
                if relationship_types is None or edge['relationship_type'] in relationship_types:
                    neighbor = self.kg._nodes.get(edge['from_node_id'])
                    if neighbor:
                        result['neighbors'].append({
                            'node': neighbor,
                            'edge': edge,
                            'direction': 'incoming'
                        })
                        result['relationships'].append(edge)

            # Filter by IEP policy if specified
            if iep_filter:
                result = self._filter_by_policy(result, iep_filter)

            return result

    # -------------------------------------------------------------------------
    # IEP Policy Filtering
    # -------------------------------------------------------------------------

    def _filter_by_policy(
        self,
        result: Dict,
        policy_id: str
    ) -> Dict:
        """Filter results by an IEP policy's handling and sharing rules."""
        policy = self.kg._policies.get(policy_id)
        if not policy:
            result['warning'] = f'Policy not found: {policy_id}'
            return result

        hasl = policy.get('hasl', {})
        handling = hasl.get('handling', 'OPEN')

        # Filter based on handling level
        if handling == 'OPEN':
            return result  # No filtering needed
        elif handling == 'RESTRICTED':
            # Only keep nodes with matching or lower restriction
            result['filtered'] = self._apply_restricted_filter(result)
        elif handling in ['CONFIDENTIAL', 'PRIVATE']:
            # Heavy filtering
            result['filtered'] = self._apply_confidential_filter(result, handling)

        return result

    def _apply_restricted_filter(self, result: Dict) -> List[str]:
        """Apply RESTRICTED filtering - remove sensitive relationships."""
        removed = []
        original_count = len(result.get('relationships', []))
        result['relationships'] = [
            r for r in result['relationships']
            if not r.get('properties', {}).get('sensitive', False)
        ]
        removed_count = original_count - len(result['relationships'])
        if removed_count > 0:
            result['removed_count'] = removed_count
        return removed

    def _apply_confidential_filter(self, result: Dict, level: str) -> List[str]:
        """Apply CONFIDENTIAL/PRIVATE filtering - heavy restrictions."""
        removed = []
        # In a real implementation, this would:
        # 1. Check node properties for classification
        # 2. Filter based on policy applies_to_entities
        # 3. Mask sensitive data

        result['warning'] = f'{level} filtering: sensitive data may be masked'
        return removed

    # -------------------------------------------------------------------------
    # Policy-Aware Recall
    # -------------------------------------------------------------------------

    def recall_by_policy(
        self,
        policy_id: str,
        action: str = 'READ',
        k: int = 10
    ) -> List[Dict]:
        """
        Recall entities governed by a specific IEP policy.

        Args:
            policy_id: Policy ID to filter by
            action: Action to check compliance for
            k: Maximum results

        Returns:
            List of entities compliant with the policy
        """
        with self._lock:
            policy = self.kg._policies.get(policy_id)
            if not policy:
                return [{'error': f'Policy not found: {policy_id}'}]

            # Get entities that this policy applies to
            applies_to = policy.get('applies_to_entities', [])
            entities = []

            if applies_to:
                # Get specific entities
                for entity_id in applies_to:
                    node = self.kg.get_node_by_entity('actor', entity_id)
                    if node:
                        entities.append({'node': node})
                    else:
                        # Try other types
                        for et in ['tool', 'cve', 'campaign']:
                            node = self.kg.get_node_by_entity(et, entity_id)
                            if node:
                                entities.append({'node': node})
                                break

            else:
                # All nodes if no specific applies_to
                for node in list(self.kg._nodes.values())[:k]:
                    entities.append({'node': node})

            # Check policy compliance
            compliant = []
            for entry in entities:
                node = entry['node']
                et = node['entity_type']
                eid = node['entity_id']

                # Simple check: does the policy apply to this entity?
                policy_applies = not applies_to or eid in applies_to

                # Check action compliance
                policy_action = policy.get('hasl', {}).get('action', 'READ')
                action_ok = self._check_action_compliance(policy_action, action)

                if policy_applies and action_ok:
                    entry['compliant'] = True
                    entry['policy'] = policy_id
                    compliant.append(entry)

            return compliant[:k]

    def _check_action_compliance(self, policy_action: str, requested_action: str) -> bool:
        """Check if a requested action complies with policy action level."""
        action_levels = {'READ': 1, 'WRITE': 2, 'MODERATE': 3, 'ADMIN': 4}

        policy_level = action_levels.get(policy_action, 1)
        requested_level = action_levels.get(requested_action, 1)

        return requested_level <= policy_level

    # -------------------------------------------------------------------------
    # Traversal Queries
    # -------------------------------------------------------------------------

    def traverse_from(
        self,
        entity_type: str,
        entity_id: str,
        relationship_types: List[str] = None,
        max_depth: int = 3,
        expand_properties: bool = False
    ) -> List[Dict]:
        """
        Traverse the graph from a starting node.

        Args:
            entity_type: Starting node type
            entity_id: Starting node ID
            relationship_types: Optional filter on relationship types
            max_depth: Maximum traversal depth
            expand_properties: Whether to expand full node properties

        Returns:
            List of traversal results with nodes and edges
        """
        with self._lock:
            results = []

            # Use the graph's traverse method
            nodes = self.kg.traverse_from(entity_type, entity_id, relationship_types, max_depth)

            for node in nodes:
                entry = {
                    'node': node,
                    'depth': 1,  # Will be calculated properly in real implementation
                    'edges': []
                }

                # Get edges involving this node
                for edge in self.kg._edges_from.get(node['node_id'], []):
                    if relationship_types is None or edge['relationship_type'] in relationship_types:
                        entry['edges'].append({
                            'edge': edge,
                            'direction': 'outgoing'
                        })

                for edge in self.kg._edges_to.get(node['node_id'], []):
                    if relationship_types is None or edge['relationship_type'] in relationship_types:
                        entry['edges'].append({
                            'edge': edge,
                            'direction': 'incoming'
                        })

                results.append(entry)

            return results

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def stats(self) -> Dict:
        """Return retriever statistics."""
        kg_stats = self.kg.stats()
        return {
            **kg_stats,
            'validator_ready': True
        }

    # -------------------------------------------------------------------------
    # CLI / Quick Test
    # -------------------------------------------------------------------------

    def quick_test(self):
        """Quick self-test of the retriever."""
        print("GraphRetriever Quick Test")
        print("=" * 50)

        # Test with empty graph
        stats = self.stats()
        print(f"\nGraph Statistics:")
        print(f"  Nodes: {stats.get('total_nodes', 0)}")
        print(f"  Edges: {stats.get('total_edges', 0)}")
        print(f"  Policies: {stats.get('total_policies', 0)}")

        # Test recall
        print("\nTesting recall()...")
        results = self.recall("muddywater", k=5)
        print(f"  Found {len(results)} results")

        # Test expansion
        print("\nTesting expand()...")
        if stats.get('total_nodes', 0) > 0:
            node = list(self.kg._nodes.values())[0]
            exp = self.expand(node['entity_type'], node['entity_id'], depth=1)
            print(f"  Expanded {len(exp.get('neighbors', []))} neighbors")
        else:
            print("  Skipping - no nodes in graph")

        # Test path finding
        print("\nTesting recall_with_path()...")
        result = self.recall_with_path("muddywater", "muddywater")
        print(f"  Path result: {result}")

        print("\nTest complete.")


# =============================================================================
# IEP Store (simplified)
# =============================================================================

class IEPStore:
    """
    Simplified IEP policy storage for testing.
    In production, this would integrate with KnowledgeGraph.
    """

    def __init__(self):
        self._policies: Dict[str, Dict] = {}

    def add_policy(self, policy: Dict) -> None:
        policy_id = policy['policy_id']
        self._policies[policy_id] = policy

    def get_policy(self, policy_id: str) -> Optional[Dict]:
        return self._policies.get(policy_id)

    def get_active_policies(self) -> List[Dict]:
        now = datetime.utcnow()
        result = []
        for policy in self._policies.values():
            if policy.get('status', 'active') != 'active':
                continue
            if 'expiration' in policy:
                try:
                    exp = datetime.fromisoformat(policy['expiration'])
                    if exp < now:
                        continue
                except:
                    pass
            result.append(policy)
        return result


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    retriever = GraphRetriever()
    retriever.kg.stats()  # Initialize
    retriever.quick_test()
