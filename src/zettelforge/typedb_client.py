"""
TypeDB Knowledge Graph Client — Drop-in replacement for KnowledgeGraph.

Provides the same public API as knowledge_graph.py but backed by TypeDB 3.x
with STIX 2.1 schema. Uses the same method signatures so all existing code
(memory_manager, graph_retriever, etc.) works without changes.

Requires:
  - TypeDB server running on localhost:1729
  - pip install typedb-driver
  - Schema loaded via _load_schema()

Falls back to JSONL KnowledgeGraph if TypeDB is unavailable.
"""
import os
import uuid
import threading
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple

from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType


# STIX entity type mapping: ZettelForge type -> TypeDB entity type
ENTITY_TYPE_MAP = {
    "actor": "threat-actor",
    "threat-actor": "threat-actor",
    "tool": "tool",
    "malware": "malware",
    "cve": "vulnerability",
    "vulnerability": "vulnerability",
    "campaign": "campaign",
    "attack-pattern": "attack-pattern",
    "indicator": "indicator",
    "infrastructure": "infrastructure",
    "note": "zettel-note",
}

# Reverse map for TypeDB type -> ZettelForge type
REVERSE_TYPE_MAP = {
    "threat-actor": "actor",
    "tool": "tool",
    "malware": "malware",
    "vulnerability": "cve",
    "campaign": "campaign",
    "attack-pattern": "attack-pattern",
    "indicator": "indicator",
    "infrastructure": "infrastructure",
    "zettel-note": "note",
}

# Relationship type mapping: ZettelForge relationship -> TypeDB relation + roles
RELATION_MAP = {
    "USES_TOOL": ("uses", "user", "used"),
    "EXPLOITS_CVE": ("targets", "source", "target"),
    "TARGETS_ASSET": ("targets", "source", "target"),
    "CONDUCTS_CAMPAIGN": ("attributed-to", "attributing", "attributed"),
    "MENTIONED_IN": ("mentioned-in", "mentioned-entity", "note"),
    "SUPERSEDES": ("supersedes", "newer", "older"),
    "ATTRIBUTED_TO": ("attributed-to", "attributing", "attributed"),
    "INDICATES": ("indicates", "indicating", "indicated"),
    "MITIGATES": ("mitigates", "mitigating", "mitigated"),
    # Causal triples from LLM extraction
    "uses": ("uses", "user", "used"),
    "targets": ("targets", "source", "target"),
    "exploits": ("targets", "source", "target"),
    "attributed_to": ("attributed-to", "attributing", "attributed"),
    "causes": ("indicates", "indicating", "indicated"),
    "enables": ("uses", "user", "used"),
    "related_to": ("uses", "user", "used"),
}


class TypeDBKnowledgeGraph:
    """
    TypeDB-backed knowledge graph with STIX 2.1 schema.
    Drop-in replacement for KnowledgeGraph — same public API.
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        username: str = "admin",
        password: str = "password",
    ):
        self.host = host or os.environ.get("TYPEDB_HOST", "localhost")
        self.port = port or int(os.environ.get("TYPEDB_PORT", "1729"))
        self.database = database or os.environ.get("TYPEDB_DATABASE", "zettelforge")
        self.username = username
        self.password = password

        self._driver = None
        self._lock = threading.RLock()
        self._schema_loaded = False

        # Compatibility: graph_retriever.py accesses these directly for BFS.
        # We maintain lightweight in-memory indexes for backward compat.
        self._nodes: Dict[str, Dict] = {}
        self._node_index: Dict[str, Dict[str, str]] = {}
        self._edges_from: Dict[str, List[Dict]] = {}
        self._edges_to: Dict[str, List[Dict]] = {}
        self._edges: Dict[str, Dict] = {}
        self._temporal_index: Dict[str, List[Dict]] = {}
        self._entity_timeline: Dict[str, List[Dict]] = {}

        # Query cache: (entity_type, entity_value) -> (result, timestamp)
        self._cache: Dict[Tuple[str, str], Tuple[Any, float]] = {}
        self._cache_ttl: float = 300.0  # 5 minutes

        self._connect()

    def _connect(self):
        """Connect to TypeDB and ensure database + schema exist."""
        try:
            self._driver = TypeDB.driver(
                f"{self.host}:{self.port}",
                Credentials(self.username, self.password),
                DriverOptions(False, None),
            )
            self._ensure_database()
            self._load_schema()
            self._rebuild_indexes()
        except Exception as e:
            raise ConnectionError(f"TypeDB connection failed: {e}") from e

    def _cache_get(self, key: Tuple[str, str]) -> Optional[Any]:
        """Get from cache if not expired."""
        import time
        entry = self._cache.get(key)
        if entry and (time.time() - entry[1]) < self._cache_ttl:
            return entry[0]
        return None

    def _cache_set(self, key: Tuple[str, str], value: Any):
        """Set cache entry with current timestamp."""
        import time
        self._cache[key] = (value, time.time())

    def _cache_invalidate(self, entity_type: str = None, entity_value: str = None):
        """Invalidate cache entries. If no args, clear all."""
        if entity_type is None:
            self._cache.clear()
        else:
            keys_to_remove = [k for k in self._cache if k[0] == entity_type]
            if entity_value:
                keys_to_remove = [k for k in keys_to_remove if k[1] == entity_value]
            for k in keys_to_remove:
                self._cache.pop(k, None)

    def _ensure_database(self):
        """Create database if it doesn't exist."""
        if not self._driver.databases.contains(self.database):
            self._driver.databases.create(self.database)

    def _load_schema(self):
        """Load STIX schema into the database if not already loaded."""
        if self._schema_loaded:
            return

        schema_dir = Path(__file__).parent / "schema"
        for schema_file in ["stix_core.tql", "stix_rules.tql"]:
            path = schema_dir / schema_file
            if not path.exists():
                continue
            try:
                tx = self._driver.transaction(self.database, TransactionType.SCHEMA)
                tx.query(path.read_text()).resolve()
                tx.commit()
            except Exception:
                # Schema may already be loaded (idempotent types)
                pass

        self._schema_loaded = True

    def _rebuild_indexes(self):
        """Rebuild in-memory indexes from TypeDB for backward compat with graph_retriever."""
        self._nodes.clear()
        self._node_index.clear()
        self._edges_from.clear()
        self._edges_to.clear()
        self._edges.clear()

        try:
            tx = self._driver.transaction(self.database, TransactionType.READ)

            # Load all entities
            for typedb_type, zf_type in REVERSE_TYPE_MAP.items():
                if typedb_type == "zettel-note":
                    rows = list(tx.query(
                        f'match $e isa {typedb_type}, has note-id $nid; select $e, $nid;'
                    ).resolve())
                    for row in rows:
                        entity = row.get("e")
                        nid = str(row.get("nid")).split(": ")[1].strip('")')
                        node_id = f"node_{entity.get_iid()}" if hasattr(entity, 'get_iid') else f"node_{nid}"
                        node = {
                            "node_id": node_id,
                            "entity_type": "note",
                            "entity_value": nid,
                            "properties": {},
                        }
                        self._nodes[node_id] = node
                        if "note" not in self._node_index:
                            self._node_index["note"] = {}
                        self._node_index["note"][nid] = node_id
                else:
                    rows = list(tx.query(
                        f'match $e isa {typedb_type}, has name $n; select $e, $n;'
                    ).resolve())
                    for row in rows:
                        entity = row.get("e")
                        name_attr = row.get("n")
                        name = str(name_attr).split(": ")[1].strip('")')
                        node_id = f"node_{entity.get_iid()}" if hasattr(entity, 'get_iid') else f"node_{name}"
                        node = {
                            "node_id": node_id,
                            "entity_type": zf_type,
                            "entity_value": name.lower(),
                            "properties": {},
                        }
                        self._nodes[node_id] = node
                        if zf_type not in self._node_index:
                            self._node_index[zf_type] = {}
                        self._node_index[zf_type][name.lower()] = node_id

            # Load edges for each relation type
            for zf_rel, (typedb_rel, role_from, role_to) in RELATION_MAP.items():
                try:
                    rows = list(tx.query(
                        f'match ($rf: $from, $rt: $to) isa {typedb_rel}; select $from, $to;'
                    ).resolve())
                    for row in rows:
                        from_entity = row.get("from")
                        to_entity = row.get("to")
                        from_id = self._entity_to_node_id(from_entity)
                        to_id = self._entity_to_node_id(to_entity)
                        if from_id and to_id:
                            edge_id = f"edge_{uuid.uuid4().hex[:12]}"
                            edge = {
                                "edge_id": edge_id,
                                "from_node_id": from_id,
                                "to_node_id": to_id,
                                "relationship": zf_rel,
                                "properties": {},
                            }
                            self._edges[edge_id] = edge
                            if from_id not in self._edges_from:
                                self._edges_from[from_id] = []
                            self._edges_from[from_id].append(edge)
                            if to_id not in self._edges_to:
                                self._edges_to[to_id] = []
                            self._edges_to[to_id].append(edge)
                except Exception:
                    continue

            tx.close()
        except Exception:
            pass  # Empty graph is fine

    def _entity_to_node_id(self, entity) -> Optional[str]:
        """Convert a TypeDB entity concept to a node_id from the index."""
        # Search through _nodes for matching IID
        iid = entity.get_iid() if hasattr(entity, 'get_iid') else None
        if iid:
            for nid, node in self._nodes.items():
                if nid == f"node_{iid}":
                    return nid
        return None

    def _stix_id(self, entity_type: str, entity_value: str) -> str:
        """Generate deterministic STIX 2.1 ID."""
        namespace = uuid.UUID("00abedb4-aa42-466c-9c01-fed23315a9b7")
        typedb_type = ENTITY_TYPE_MAP.get(entity_type, entity_type)
        return f"{typedb_type}--{uuid.uuid5(namespace, entity_value.lower())}"

    # ── Public API (same as KnowledgeGraph) ──────────────────

    def add_node(self, entity_type: str, entity_value: str, properties: Optional[Dict] = None) -> str:
        """Add or update an entity node. Returns node_id."""
        with self._lock:
            typedb_type = ENTITY_TYPE_MAP.get(entity_type, None)
            if not typedb_type:
                return ""

            stix_id = self._stix_id(entity_type, entity_value)
            value_lower = entity_value.lower()

            # Check if already exists in local index
            if entity_type in self._node_index and value_lower in self._node_index[entity_type]:
                return self._node_index[entity_type][value_lower]

            # Insert into TypeDB
            try:
                tx = self._driver.transaction(self.database, TransactionType.WRITE)
                if typedb_type == "zettel-note":
                    tx.query(
                        f'insert $e isa zettel-note, has note-id "{value_lower}";'
                    ).resolve()
                else:
                    tx.query(
                        f'insert $e isa {typedb_type}, has name "{value_lower}", has stix-id "{stix_id}";'
                    ).resolve()
                tx.commit()
            except Exception:
                pass  # May already exist (duplicate insert)

            # Update local index
            node_id = f"node_{stix_id}"
            node = {
                "node_id": node_id,
                "entity_type": entity_type,
                "entity_value": value_lower,
                "properties": properties or {},
                "created_at": datetime.now().isoformat(),
            }
            self._nodes[node_id] = node
            if entity_type not in self._node_index:
                self._node_index[entity_type] = {}
            self._node_index[entity_type][value_lower] = node_id
            self._cache_invalidate(entity_type, value_lower)

            return node_id

    def add_edge(
        self,
        from_type: str,
        from_value: str,
        to_type: str,
        to_value: str,
        relationship: str,
        properties: Optional[Dict] = None,
    ) -> str:
        """Add a relationship edge. Auto-creates nodes."""
        with self._lock:
            from_id = self.add_node(from_type, from_value)
            to_id = self.add_node(to_type, to_value)

            if not from_id or not to_id:
                return ""

            # Check for duplicate
            for edge in self._edges_from.get(from_id, []):
                if edge["to_node_id"] == to_id and edge["relationship"] == relationship:
                    return edge["edge_id"]

            # Map to TypeDB relation
            rel_info = RELATION_MAP.get(relationship)
            if rel_info:
                typedb_rel, role_from, role_to = rel_info
            else:
                typedb_rel, role_from, role_to = "uses", "user", "used"

            from_typedb = ENTITY_TYPE_MAP.get(from_type, from_type)
            to_typedb = ENTITY_TYPE_MAP.get(to_type, to_type)
            from_val = from_value.lower()
            to_val = to_value.lower()

            # Build match + insert
            if from_typedb == "zettel-note":
                from_match = f'$from isa zettel-note, has note-id "{from_val}"'
            else:
                from_stix = self._stix_id(from_type, from_value)
                from_match = f'$from isa {from_typedb}, has stix-id "{from_stix}"'

            if to_typedb == "zettel-note":
                to_match = f'$to isa zettel-note, has note-id "{to_val}"'
            else:
                to_stix = self._stix_id(to_type, to_value)
                to_match = f'$to isa {to_typedb}, has stix-id "{to_stix}"'

            conf = properties.get("confidence", 0.5) if properties else 0.5

            try:
                tx = self._driver.transaction(self.database, TransactionType.WRITE)
                tx.query(
                    f'match {from_match}; {to_match}; '
                    f'insert ({role_from}: $from, {role_to}: $to) isa {typedb_rel}, has confidence {conf};'
                ).resolve()
                tx.commit()
            except Exception:
                pass  # May already exist or role mismatch

            # Update local index
            edge_id = f"edge_{uuid.uuid4().hex[:12]}"
            edge = {
                "edge_id": edge_id,
                "from_node_id": from_id,
                "to_node_id": to_id,
                "relationship": relationship,
                "properties": properties or {},
                "created_at": datetime.now().isoformat(),
            }
            self._edges[edge_id] = edge
            if from_id not in self._edges_from:
                self._edges_from[from_id] = []
            self._edges_from[from_id].append(edge)
            if to_id not in self._edges_to:
                self._edges_to[to_id] = []
            self._edges_to[to_id].append(edge)
            self._cache_invalidate(from_type, from_value.lower())
            self._cache_invalidate(to_type, to_value.lower())

            return edge_id

    def add_temporal_edge(
        self,
        from_type: str,
        from_value: str,
        to_type: str,
        to_value: str,
        relationship: str,
        timestamp: str,
        properties: Optional[Dict] = None,
    ) -> str:
        """Add a temporal edge with timestamp."""
        props = properties or {}
        props["timestamp"] = timestamp
        edge_id = self.add_edge(from_type, from_value, to_type, to_value, relationship, props)

        # Index temporal edge
        if timestamp:
            if timestamp not in self._temporal_index:
                self._temporal_index[timestamp] = []
            edge = self._edges.get(edge_id, {})
            self._temporal_index[timestamp].append(edge)

            entity_key = f"{from_type}:{from_value.lower()}"
            if entity_key not in self._entity_timeline:
                self._entity_timeline[entity_key] = []
            self._entity_timeline[entity_key].append({
                "edge": edge,
                "timestamp": timestamp,
                "to_entity": f"{to_type}:{to_value.lower()}",
            })

        return edge_id

    def get_node(self, entity_type: str, entity_value: str) -> Optional[Dict]:
        """Get node by type and value."""
        node_id = self._node_index.get(entity_type, {}).get(entity_value.lower())
        if node_id:
            return self._nodes.get(node_id)
        return None

    def get_neighbors(self, entity_type: str, entity_value: str, relationship: Optional[str] = None) -> List[Dict]:
        """Get adjacent nodes (outgoing edges)."""
        node_id = self._node_index.get(entity_type, {}).get(entity_value.lower())
        if not node_id:
            return []

        neighbors = []
        for edge in self._edges_from.get(node_id, []):
            if relationship and edge["relationship"] != relationship:
                continue
            to_node = self._nodes.get(edge["to_node_id"])
            if to_node:
                neighbors.append({
                    "node": to_node,
                    "relationship": edge["relationship"],
                    "edge_properties": edge.get("properties", {}),
                })
        return neighbors

    def traverse(self, start_type: str, start_value: str, max_depth: int = 2) -> List[Dict]:
        """DFS traversal up to max_depth. Returns list of paths."""
        start_node_id = self._node_index.get(start_type, {}).get(start_value.lower())
        if not start_node_id:
            return []

        visited: Set[str] = set()
        results = []

        def _dfs(current_id, depth, path):
            if depth > max_depth or current_id in visited:
                return
            visited.add(current_id)

            for edge in self._edges_from.get(current_id, []):
                to_id = edge["to_node_id"]
                to_node = self._nodes.get(to_id)
                if not to_node:
                    continue

                step = {
                    "from_type": self._nodes[current_id]["entity_type"],
                    "from_value": self._nodes[current_id]["entity_value"],
                    "relationship": edge["relationship"],
                    "to_type": to_node["entity_type"],
                    "to_value": to_node["entity_value"],
                }
                new_path = path + [step]
                results.append(new_path)
                _dfs(to_id, depth + 1, new_path)

        _dfs(start_node_id, 1, [])
        return results

    def get_entity_timeline(self, entity_type: str, entity_value: str) -> List[Dict]:
        """Get timeline of states for an entity."""
        entity_key = f"{entity_type}:{entity_value.lower()}"
        timeline = self._entity_timeline.get(entity_key, [])
        timeline.sort(key=lambda x: x.get("timestamp", ""))
        return timeline

    def get_changes_since(self, timestamp: str) -> List[Dict]:
        """Get all entity changes since a given timestamp."""
        changes = []
        for ts, edges in self._temporal_index.items():
            if ts >= timestamp:
                for edge in edges:
                    from_node = self._nodes.get(edge.get("from_node_id"), {})
                    to_node = self._nodes.get(edge.get("to_node_id"), {})
                    changes.append({
                        "timestamp": ts,
                        "from": f"{from_node.get('entity_type')}:{from_node.get('entity_value')}",
                        "relationship": edge.get("relationship"),
                        "to": f"{to_node.get('entity_type')}:{to_node.get('entity_value')}",
                    })
        changes.sort(key=lambda x: x.get("timestamp", ""))
        return changes

    def get_latest_state(self, entity_type: str, entity_value: str) -> Optional[Dict]:
        """Get the latest known state of an entity."""
        timeline = self.get_entity_timeline(entity_type, entity_value)
        return timeline[-1] if timeline else None

    def close(self):
        """Close the TypeDB driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None


# ── Global Singleton ─────────────────────────────────────────

_typedb_kg: Optional[TypeDBKnowledgeGraph] = None
_typedb_lock = threading.Lock()


def get_typedb_knowledge_graph() -> TypeDBKnowledgeGraph:
    """Get global TypeDB knowledge graph instance."""
    global _typedb_kg
    if _typedb_kg is None:
        with _typedb_lock:
            if _typedb_kg is None:
                _typedb_kg = TypeDBKnowledgeGraph()
    return _typedb_kg
