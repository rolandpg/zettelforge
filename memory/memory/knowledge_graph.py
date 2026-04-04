"""
Knowledge Graph — Phase 6 Ontology & Knowledge Graph Storage
=============================================================

Implements a Neo4j-inspired knowledge graph for A-MEM with:
- Entity nodes (CVE, Actor, Tool, Campaign, Sector, IEP_Policy)
- Relationship edges with semantic types
- IEP 2.0 policy temporal resolution
- JSONL persistence with atomic writes

Usage:
    kg = KnowledgeGraph()
    kg.add_node('cve', 'CVE-2024-3094', {'description': 'ProxyLogon'})
    kg.add_node('actor', 'muddywater', {'type': 'apt'})
    kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import threading

MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
NODES_FILE = MEMORY_DIR / "kg_nodes.jsonl"
EDGES_FILE = MEMORY_DIR / "kg_edges.jsonl"
POLICIES_FILE = MEMORY_DIR / "kg_policies.jsonl"


class KnowledgeGraph:
    """
    Knowledge graph storage with IEP 2.0 governance.
    Uses JSONL for append-only persistence.
    """

    def __init__(
        self,
        nodes_file: str = None,
        edges_file: str = None,
        policies_file: str = None
    ):
        self.nodes_file = Path(nodes_file) if nodes_file else NODES_FILE
        self.edges_file = Path(edges_file) if edges_file else EDGES_FILE
        self.policies_file = Path(policies_file) if policies_file else POLICIES_FILE

        # In-memory caches
        self._nodes: Dict[str, Dict] = {}  # node_id -> node data
        self._node_index: Dict[str, Dict[str, str]] = {}  # entity_type -> entity_id -> node_id
        self._edges: Dict[str, Dict] = {}  # edge_id -> edge data
        self._policies: Dict[str, Dict] = {}  # policy_id -> policy data
        self._edges_from: Dict[str, List[Dict]] = {}  # node_id -> outgoing edges
        self._edges_to: Dict[str, List[Dict]] = {}  # node_id -> incoming edges

        self._lock = threading.RLock()
        self._load_all()

    # -------------------------------------------------------------------------
    # Core Loading
    # -------------------------------------------------------------------------

    def _load_all(self) -> None:
        """Load all graph data from disk."""
        with self._lock:
            self._nodes = {}
            self._node_index = {}
            self._edges = {}
            self._policies = {}
            self._edges_from = {}
            self._edges_to = {}

            # Load nodes
            if self.nodes_file.exists():
                with open(self.nodes_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                node = json.loads(line)
                                self._nodes[node['node_id']] = node
                                et = node['entity_type']
                                eid = node['entity_id']
                                self._node_index.setdefault(et, {})[eid] = node['node_id']
                            except (json.JSONDecodeError, KeyError):
                                continue

            # Load edges
            if self.edges_file.exists():
                with open(self.edges_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                edge = json.loads(line)
                                self._edges[edge['edge_id']] = edge
                                self._edges_from.setdefault(edge['from_node_id'], []).append(edge)
                                self._edges_to.setdefault(edge['to_node_id'], []).append(edge)
                            except (json.JSONDecodeError, KeyError):
                                continue

            # Load policies
            if self.policies_file.exists():
                with open(self.policies_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                policy = json.loads(line)
                                self._policies[policy['policy_id']] = policy
                            except (json.JSONDecodeError, KeyError):
                                continue

    def _save_nodes(self) -> None:
        """Persist nodes to disk."""
        tmp_file = self.nodes_file.with_suffix('.jsonl.tmp')
        with open(tmp_file, 'w') as f:
            for node in self._nodes.values():
                f.write(json.dumps(node) + '\n')
        tmp_file.rename(self.nodes_file)

    def _save_edges(self) -> None:
        """Persist edges to disk."""
        tmp_file = self.edges_file.with_suffix('.jsonl.tmp')
        with open(tmp_file, 'w') as f:
            for edge in self._edges.values():
                f.write(json.dumps(edge) + '\n')
        tmp_file.rename(self.edges_file)

    def _save_policies(self) -> None:
        """Persist policies to disk."""
        tmp_file = self.policies_file.with_suffix('.jsonl.tmp')
        with open(tmp_file, 'w') as f:
            for policy in self._policies.values():
                f.write(json.dumps(policy) + '\n')
        tmp_file.rename(self.policies_file)

    # -------------------------------------------------------------------------
    # Node Operations
    # -------------------------------------------------------------------------

    def add_node(
        self,
        entity_type: str,
        entity_id: str,
        properties: Dict,
        node_id: str = None
    ) -> Dict:
        """
        Add a node to the knowledge graph.

        Args:
            entity_type: One of cve, actor, tool, campaign, sector, iep_policy
            entity_id: The canonical entity identifier
            properties: Node properties (must include entity_type, created_at)
            node_id: Optional custom node ID (auto-generated if None)

        Returns:
            The created node dictionary
        """
        with self._lock:
            if entity_type not in self._node_index:
                self._node_index[entity_type] = {}

            if node_id is None:
                node_id = str(uuid.uuid4())

            now = datetime.utcnow().isoformat() + 'Z'

            node = {
                'node_id': node_id,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'properties': properties,
                'created_at': properties.get('created_at', now),
                'updated_at': now
            }

            # Update index
            self._nodes[node_id] = node
            self._node_index[entity_type][entity_id] = node_id

            # Persist
            self._save_nodes()
            return node

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get a node by its ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def get_node_by_entity(self, entity_type: str, entity_id: str) -> Optional[Dict]:
        """Get a node by its entity type and ID."""
        with self._lock:
            node_id = self._node_index.get(entity_type, {}).get(entity_id)
            if node_id:
                return self._nodes.get(node_id)
            return None

    def update_node(self, node_id: str, properties: Dict) -> bool:
        """Update a node's properties."""
        with self._lock:
            if node_id not in self._nodes:
                return False

            self._nodes[node_id]['properties'].update(properties)
            self._nodes[node_id]['updated_at'] = datetime.utcnow().isoformat() + 'Z'
            self._save_nodes()
            return True

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its associated edges."""
        with self._lock:
            if node_id not in self._nodes:
                return False

            node = self._nodes[node_id]
            entity_type = node['entity_type']
            entity_id = node['entity_id']

            # Delete associated edges
            outgoing = list(self._edges_from.get(node_id, []))
            incoming = list(self._edges_to.get(node_id, []))

            for edge in outgoing + incoming:
                del self._edges[edge['edge_id']]

            # Update indices
            del self._nodes[node_id]
            if entity_type in self._node_index:
                del self._node_index[entity_type][entity_id]
            self._edges_from.pop(node_id, None)
            self._edges_to.pop(node_id, None)

            # Persist
            self._save_nodes()
            self._save_edges()
            return True

    def get_nodes_by_entity_type(self, entity_type: str) -> List[Dict]:
        """Get all nodes of a given entity type."""
        with self._lock:
            result = []
            for node in self._nodes.values():
                if node['entity_type'] == entity_type:
                    result.append(node)
            return result

    # -------------------------------------------------------------------------
    # Edge Operations
    # -------------------------------------------------------------------------

    def add_edge(
        self,
        from_entity_type: str,
        from_entity_id: str,
        to_entity_type: str,
        to_entity_id: str,
        relationship_type: str,
        properties: Dict = None
    ) -> Dict:
        """
        Add a relationship edge between two nodes.

        Args:
            from_entity_type: Source entity type
            from_entity_id: Source entity ID
            to_entity_type: Target entity type
            to_entity_id: Target entity ID
            relationship_type: One of USES, TARGETS, EXPLOITS, etc.
            properties: Optional edge properties

        Returns:
            The created edge dictionary
        """
        with self._lock:
            # Get or create source node
            from_node = self.get_node_by_entity(from_entity_type, from_entity_id)
            if from_node is None:
                from_node = self.add_node(from_entity_type, from_entity_id, {})
                if from_node is None:
                    raise ValueError(f"Failed to create source node: {from_entity_type}/{from_entity_id}")

            # Get or create target node
            to_node = self.get_node_by_entity(to_entity_type, to_entity_id)
            if to_node is None:
                to_node = self.add_node(to_entity_type, to_entity_id, {})
                if to_node is None:
                    raise ValueError(f"Failed to create target node: {to_entity_type}/{to_entity_id}")

            # Create edge
            edge_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat() + 'Z'

            edge = {
                'edge_id': edge_id,
                'from_node_id': from_node['node_id'],
                'to_node_id': to_node['node_id'],
                'relationship_type': relationship_type,
                'properties': properties or {},
                'created_at': now
            }

            self._edges[edge_id] = edge
            self._edges_from.setdefault(from_node['node_id'], []).append(edge)
            self._edges_to.setdefault(to_node['node_id'], []).append(edge)

            self._save_edges()
            return edge

    def get_edges_from(self, node_id: str, relationship_type: str = None) -> List[Dict]:
        """Get outgoing edges from a node, optionally filtered by relationship type."""
        with self._lock:
            edges = self._edges_from.get(node_id, [])
            if relationship_type:
                edges = [e for e in edges if e['relationship_type'] == relationship_type]
            return edges

    def get_edges_to(self, node_id: str, relationship_type: str = None) -> List[Dict]:
        """Get incoming edges to a node, optionally filtered by relationship type."""
        with self._lock:
            edges = self._edges_to.get(node_id, [])
            if relationship_type:
                edges = [e for e in edges if e['relationship_type'] == relationship_type]
            return edges

    def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge."""
        with self._lock:
            if edge_id not in self._edges:
                return False

            edge = self._edges[edge_id]
            from_id = edge['from_node_id']
            to_id = edge['to_node_id']

            del self._edges[edge_id]
            self._edges_from.setdefault(from_id, [])
            self._edges_to.setdefault(to_id, [])
            self._edges_from[from_id] = [e for e in self._edges_from[from_id] if e['edge_id'] != edge_id]
            self._edges_to[to_id] = [e for e in self._edges_to[to_id] if e['edge_id'] != edge_id]

            self._save_edges()
            return True

    # -------------------------------------------------------------------------
    # Policy (IEP) Operations
    # -------------------------------------------------------------------------

    def add_policy(self, policy: Dict) -> Dict:
        """
        Add an IEP 2.0 policy to the graph.

        Args:
            policy: Policy data including policy_id, hasl, etc.

        Returns:
            The created policy dictionary
        """
        with self._lock:
            policy_id = policy['policy_id']
            now = datetime.utcnow().isoformat() + 'Z'

            # Ensure timestamps
            policy.setdefault('created_at', now)
            if 'modified_at' not in policy:
                policy['modified_at'] = now

            self._policies[policy_id] = policy
            self._save_policies()
            return policy

    def get_policy(self, policy_id: str) -> Optional[Dict]:
        """Get a policy by its ID."""
        with self._lock:
            return self._policies.get(policy_id)

    def get_active_policies(self) -> List[Dict]:
        """Get all active (non-expired, non-revoked) policies."""
        with self._lock:
            now = datetime.utcnow()
            result = []

            for policy in self._policies.values():
                if policy.get('status', 'active') != 'active':
                    continue

                # Check expiration
                if 'expiration' in policy:
                    try:
                        exp_date = datetime.fromisoformat(policy['expiration'].replace('Z', '+00:00').replace('+00:00', ''))
                        if exp_date < now.replace(tzinfo=None):
                            continue
                    except (ValueError, TypeError):
                        pass

                # Check revocation
                if 'revocation_date' in policy:
                    try:
                        rev_date = datetime.fromisoformat(policy['revocation_date'].replace('Z', '+00:00').replace('+00:00', ''))
                        if rev_date < now.replace(tzinfo=None):
                            continue
                    except (ValueError, TypeError):
                        pass

                result.append(policy)

            return result

    def check_policy_compliance(self, entity_type: str, entity_id: str, action: str) -> Tuple[bool, str]:
        """
        Check if an action on an entity complies with applicable policies.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            action: Action to perform (READ, WRITE, MODERATE, ADMIN)

        Returns:
            (compliant: bool, reason: str)
        """
        with self._lock:
            # Get node
            node = self.get_node_by_entity(entity_type, entity_id)
            if node is None:
                return True, "No policy applies - entity not in graph"

            # Get applicable policies (active ones)
            policies = self.get_active_policies()

            if not policies:
                return True, "No active policies exist"

            # Find applicable policies
            for policy in policies:
                # Check if policy applies to this entity type
                applies_to = policy.get('applies_to_entities', [])
                if applies_to and entity_id not in applies_to:
                    continue

                # Check policy action
                policy_action = policy.get('hasl', {}).get('action', 'READ')
                if policy_action == 'ADMIN':
                    return False, f"Policy {policy['policy_id']} requires ADMIN action level"
                elif policy_action == 'MODERATE' and action in ['ADMIN']:
                    return False, f"Policy {policy['policy_id']} restricts ADMIN actions"
                elif policy_action == 'WRITE' and action in ['MODERATE', 'ADMIN']:
                    return False, f"Policy {policy['policy_id']} restricts MODERATE/ADMIN actions"

            return True, "Action compliant with all applicable policies"

    # -------------------------------------------------------------------------
    # Graph Traversal
    # -------------------------------------------------------------------------

    def get_neighbors(self, node_id: str, relationship_type: str = None) -> List[Dict]:
        """Get all neighbor nodes of a node."""
        with self._lock:
            neighbors = []
            edges = self._edges_from.get(node_id, []) + self._edges_to.get(node_id, [])

            if relationship_type:
                edges = [e for e in edges if e['relationship_type'] == relationship_type]

            for edge in edges:
                neighbor_id = edge['to_node_id'] if edge['from_node_id'] == node_id else edge['from_node_id']
                neighbor = self._nodes.get(neighbor_id)
                if neighbor:
                    neighbors.append(neighbor)

            return neighbors

    def get_path(
        self,
        from_entity_type: str,
        from_entity_id: str,
        to_entity_type: str,
        to_entity_id: str,
        max_depth: int = 3
    ) -> Optional[List[Dict]]:
        """
        Find a path between two nodes using BFS.

        Returns:
            List of nodes from source to target, or None if no path exists
        """
        with self._lock:
            start_node = self.get_node_by_entity(from_entity_type, from_entity_id)
            if not start_node:
                return None

            end_node = self.get_node_by_entity(to_entity_type, to_entity_id)
            if not end_node:
                return None

            # BFS
            visited = {start_node['node_id']}
            queue = [(start_node['node_id'], [start_node['node_id']])]

            while queue:
                current_id, path = queue.pop(0)

                if current_id == end_node['node_id']:
                    return [self._nodes[nid] for nid in path]

                if len(path) >= max_depth:
                    continue

                # Get neighbors
                for edge in self._edges_from.get(current_id, []):
                    neighbor_id = edge['to_node_id']
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, path + [neighbor_id]))

                for edge in self._edges_to.get(current_id, []):
                    neighbor_id = edge['from_node_id']
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, path + [neighbor_id]))

            return None

    def traverse_from(
        self,
        entity_type: str,
        entity_id: str,
        relationship_type: str = None,
        max_depth: int = 3
    ) -> List[Dict]:
        """Get all reachable nodes from a starting node."""
        with self._lock:
            start_node = self.get_node_by_entity(entity_type, entity_id)
            if not start_node:
                return []

            visited = set()
            queue = [(start_node['node_id'], 0)]
            result = []

            while queue:
                current_id, depth = queue.pop(0)

                if current_id in visited:
                    continue
                visited.add(current_id)

                if depth > 0:
                    result.append(self._nodes[current_id])

                if depth >= max_depth:
                    continue

                for edge in self._edges_from.get(current_id, []):
                    if relationship_type is None or edge['relationship_type'] == relationship_type:
                        queue.append((edge['to_node_id'], depth + 1))

                for edge in self._edges_to.get(current_id, []):
                    if relationship_type is None or edge['relationship_type'] == relationship_type:
                        queue.append((edge['from_node_id'], depth + 1))

            return result

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def stats(self) -> Dict:
        """Return graph statistics."""
        with self._lock:
            # Count by entity type
            by_type = {}
            for node in self._nodes.values():
                et = node['entity_type']
                by_type[et] = by_type.get(et, 0) + 1

            # Count edges by type
            edge_counts = {}
            for edge in self._edges.values():
                rt = edge['relationship_type']
                edge_counts[rt] = edge_counts.get(rt, 0) + 1

            # Count policies
            active_policies = len(self.get_active_policies())

            return {
                'total_nodes': len(self._nodes),
                'total_edges': len(self._edges),
                'total_policies': len(self._policies),
                'active_policies': active_policies,
                'nodes_by_type': by_type,
                'edges_by_type': edge_counts,
                'nodes_file': str(self.nodes_file),
                'edges_file': str(self.edges_file),
                'policies_file': str(self.policies_file)
            }

    def clear(self) -> None:
        """Clear all graph data."""
        with self._lock:
            self._nodes.clear()
            self._node_index.clear()
            self._edges.clear()
            self._policies.clear()
            self._edges_from.clear()
            self._edges_to.clear()

            # Clear files
            self.nodes_file.unlink(missing_ok=True)
            self.edges_file.unlink(missing_ok=True)
            self.policies_file.unlink(missing_ok=True)


# =============================================================================
# Global Access
# =============================================================================

_kg: Optional[KnowledgeGraph] = None
_kg_lock = threading.Lock()


def get_knowledge_graph() -> KnowledgeGraph:
    """Get or create the global knowledge graph instance."""
    global _kg
    if _kg is None:
        with _kg_lock:
            if _kg is None:
                _kg = KnowledgeGraph()
    return _kg


# =============================================================================
# CLI / Quick Test
# =============================================================================

if __name__ == "__main__":
    kg = KnowledgeGraph()

    # Test basic operations
    print("Knowledge Graph CLI")
    print("=" * 50)

    # Add some nodes
    print("\n1. Adding nodes...")

    cve = kg.add_node('cve', 'CVE-2024-3094', {
        'description': 'ProxyLogon vulnerability',
        'cvss_score': 9.8,
        'severity': 'critical',
        'published_date': '2024-03-03'
    })
    print(f"   CVE: {cve['node_id']}")

    actor = kg.add_node('actor', 'muddywater', {
        'type': 'apt',
        'first_seen': '2023-01-01'
    })
    print(f"   Actor: {actor['node_id']}")

    # Add edge
    print("\n2. Adding relationships...")
    edge = kg.add_edge('actor', 'muddywater', 'cve', 'CVE-2024-3094', 'EXPLOITS')
    print(f"   Edge: {edge['edge_id']} ({edge['relationship_type']})")

    # Test traversal
    print("\n3. Testing traversal...")
    neighbors = kg.get_neighbors(cve['node_id'])
    print(f"   CVE-2024-3094 neighbors: {len(neighbors)}")

    path = kg.get_path('actor', 'muddywater', 'cve', 'CVE-2024-3094')
    print(f"   Path found: {path is not None}")

    # Test policies
    print("\n4. Testing policies...")
    policy = {
        'policy_id': 'IEP-US-0001',
        'name': 'US Gov Threat Intel',
        'description': 'Threat intelligence for US government',
        'hasl': {
            'handling': 'RESTRICTED',
            'action': 'READ',
            'sharing': 'TLP_GREEN',
            'licensing': 'CC-BY'
        },
        'created_by': 'admin',
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }
    kg.add_policy(policy)
    print(f"   Policy added: {policy['policy_id']}")

    # Stats
    print("\n5. Graph statistics:")
    stats = kg.stats()
    print(f"   Nodes: {stats['total_nodes']}")
    print(f"   Edges: {stats['total_edges']}")
    print(f"   Policies: {stats['active_policies']}")
