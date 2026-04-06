"""
Entity Indexer - Fast entity-based note retrieval
A-MEM Agentic Memory Architecture V1.0
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class EntityExtractor:
    """Extract entities from text using regex patterns"""

    PATTERNS = {
        'cve': re.compile(r'(CVE-\d{4}-\d{4,})', re.IGNORECASE),
        'actor': re.compile(
            r'\b(apt\d+|apt\s+\d+|lazarus|sandworm|volt\s+typhoon|unc\d+)\b',
            re.IGNORECASE
        ),
        'tool': re.compile(
            r'\b(cobalt\s+strike|metasploit|mimikatz|bloodhound|dropbear)\b',
            re.IGNORECASE
        ),
        'campaign': re.compile(
            r'\b(operation\s+\w+)\b',
            re.IGNORECASE
        ),
    }

    def extract_all(self, text: str) -> Dict[str, List[str]]:
        """Extract all entity types from text."""
        results = {}
        for entity_type, pattern in self.PATTERNS.items():
            matches = pattern.findall(text)
            results[entity_type] = list(set(m.lower().replace(' ', '-') for m in matches))
        return results


class EntityIndexer:
    """Index notes by entities for fast lookup"""

    def __init__(self, index_path: Optional[str] = None):
        from amem.memory_store import get_default_data_dir
        
        if index_path is None:
            index_path = get_default_data_dir() / "entity_index.json"
        self.index_path = Path(index_path)
        self.index: Dict[str, Dict[str, Set[str]]] = {
            'cve': {},
            'actor': {},
            'tool': {},
            'campaign': {},
            'sector': {}
        }
        self.extractor = EntityExtractor()
        self.load()

    def load(self) -> bool:
        """Load index from disk."""
        if not self.index_path.exists():
            return False
        try:
            with open(self.index_path) as f:
                data = json.load(f)
                for entity_type in self.index:
                    if entity_type in data:
                        self.index[entity_type] = {
                            k: set(v) for k, v in data[entity_type].items()
                        }
            return True
        except Exception:
            return False

    def save(self):
        """Save index to disk."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, 'w') as f:
            # Convert sets to lists for JSON
            data = {
                k: {kk: list(vv) for kk, vv in v.items()}
                for k, v in self.index.items()
            }
            json.dump(data, f, indent=2)

    def add_note(self, note_id: str, entities: Dict[str, List[str]]):
        """Add note to entity index."""
        for entity_type, entity_list in entities.items():
            if entity_type not in self.index:
                self.index[entity_type] = {}
            for entity in entity_list:
                entity_lower = entity.lower()
                if entity_lower not in self.index[entity_type]:
                    self.index[entity_type][entity_lower] = set()
                self.index[entity_type][entity_lower].add(note_id)
        self.save()

    def get_note_ids(self, entity_type: str, entity_value: str) -> List[str]:
        """Get note IDs for a specific entity."""
        if entity_type not in self.index:
            return []
        return list(self.index[entity_type].get(entity_value.lower(), []))

    def stats(self) -> Dict:
        """Get index statistics."""
        return {
            entity_type: {
                'unique_entities': len(entities),
                'total_mappings': sum(len(notes) for notes in entities.values())
            }
            for entity_type, entities in self.index.items()
        }

    def build(self) -> Dict:
        """Rebuild index from all notes."""
        from amem.memory_store import MemoryStore
        
        store = MemoryStore()
        self.index = {
            'cve': {},
            'actor': {},
            'tool': {},
            'campaign': {},
            'sector': {}
        }
        
        count = 0
        for note in store.iterate_notes():
            entities = self.extractor.extract_all(note.content.raw)
            self.add_note(note.id, entities)
            count += 1
        
        return {'notes_indexed': count, 'stats': self.stats()}
