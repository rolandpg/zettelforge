"""
Entity Indexer - Fast Lookup by Known Entity
Extracts and indexes: CVE-IDs, Threat Actors, Tools/Campaigns, Sectors
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

# Known actor patterns (case-insensitive)
KNOWN_ACTORS = {
    # China-Nexus
    "volt typhoon", "volty typhoon", "vult typhoon",
    "apt28", "apt29", "apt30", "apt41",
    "saviorthrop", "thallium", "zinc", "magnallium",
    "menupass", "leviathan", "pass栗", "leafly",
    # Russia-Nexus
    "apt28", "fancy bear", "sednit", "兵", "snake",
    "turla", "waterbug", "kyrill",
    "wizard polar", "venomous bear", "gamaredon",
    # North Korea-Nexus
    "lazarus group", "lazarus", "hidden cobra", "zinc",
    "labyrinth chollima", "stone panda", "matryoshka",
    "andariel", "thallium", "bright star",
    " UNC1069", "unc1069", "unc2452", "jade",
    # Iran-Nexus
    "phosphorus", "ajax", "charming kitten", "pargasite",
    "mint sandstone", "news", "clever zINC",
    # MOIS-linked
    "muddywater", "muddy cylc", "stateneptune",
    "helminth", "dewdrop", "ramsom",
    # Named threat groups
    "handala hack", "handala", "killnet",
    "lockbit", "lockbit 3.0", "alphv", "blackcat",
    "rhysida", "8base", "doppelpaymer",
    "revil", "Sodinokibi", "wizard polar",
    "nozomi networks lab", "elastic security labs",
    "truechaos", "roadk1ll", "road k1ll", "silver fox",
    "atlascross", "waveshaper", "waveshaper",
    # General
    "cyber army", "threat actor", "apt"
}

# Known tools/campaigns
KNOWN_TOOLS = {
    "havoc", "cobalt strike", "metasploit", "mimikatz",
    "bloodhound", "sharphound", "powertool", "seatbelt",
    "koadic", "empire", "covenant", "sliver", "brute ratel",
    "xworm", "AsyncRAT", "Nanocore", "netwire",
    "trueconf", "trivy", "sonicwall", "citrix",
    "sentinelone", "crowdstrike", "defender", "sentinel",
    "manageengine", "zoho", "joomla", "ivanti", "palo alto",
    "vmware", "workspace one", "coldfusion", "ofbiz",
    "openvas", "nessus", "qualys", "rapid7", "tenable",
}

# Sector keywords
SECTOR_KEYWORDS = {
    "dib": ["DIB", "defense industrial base", "contractor", "supplier"],
    "healthcare": ["healthcare", "hospital", "medical", "phi", "hipaa"],
    "mssp": ["mssp", "managed security", "soc", "mdr", "threat detection"],
    "ot": ["ot", "operational technology", "ics", "scada", "industrial"],
    "federal": ["federal", "dod", "cia", "fbi", "government", "goc"],
    "state_local": ["state", "local government", "municipal", "county"],
    "finance": ["financial", "banking", "insurance", "fintech"],
    "retail": ["retail", "point of sale", "pos"],
    "telecom": ["telecom", "isp", "communications", "voip"],
}

# CVE pattern
CVE_PATTERN = re.compile(r'CVE-\d{4}-\d{4,}', re.IGNORECASE)


class EntityExtractor:
    """Extract entities from raw text content"""

    def __init__(self):
        self.actor_pattern = re.compile(
            '|'.join(re.escape(a) for a in KNOWN_ACTORS),
            re.IGNORECASE
        )
        self.tool_pattern = re.compile(
            '|'.join(re.escape(t) for t in KNOWN_TOOLS),
            re.IGNORECASE
        )
        # Campaign pattern: "Operation X" or "OperationX"
        self.campaign_pattern = re.compile(
            r'Operation\s+([A-Za-z0-9]+)',
            re.IGNORECASE
        )

    def extract_all(self, text: str) -> Dict[str, List[str]]:
        """Extract all entities from text"""
        cves = self._extract_cves(text)
        actors = self._extract_actors(text)
        tools = self._extract_tools(text)
        campaigns = self._extract_campaigns(text)
        sectors = self._extract_sectors(text)

        return {
            'cves': cves,
            'actors': actors,
            'tools': tools,
            'campaigns': campaigns,
            'sectors': sectors
        }

    def _extract_cves(self, text: str) -> List[str]:
        return CVE_PATTERN.findall(text)

    def _extract_actors(self, text: str) -> List[str]:
        found = set()
        for match in self.actor_pattern.finditer(text):
            found.add(match.group().lower())
        return sorted(found)

    def _extract_tools(self, text: str) -> List[str]:
        found = set()
        for match in self.tool_pattern.finditer(text):
            found.add(match.group().lower())
        return sorted(found)

    def _extract_campaigns(self, text: str) -> List[str]:
        found = set()
        for match in self.campaign_pattern.finditer(text):
            found.add(f"Operation {match.group(1)}")
        return sorted(found)

    def _extract_sectors(self, text: str) -> List[str]:
        found = set()
        text_lower = text.lower()
        for sector, keywords in SECTOR_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    found.add(sector)
                    break
        return sorted(found)


class EntityIndexer:
    """
    Persistent secondary index for entity → note mapping.
    Reads from existing notes.jsonl, builds entity_index.json.
    """
    def __init__(
        self,
        jsonl_path: str = "/home/rolandpg/.openclaw/workspace/memory/notes.jsonl",
        index_path: str = "/home/rolandpg/.openclaw/workspace/memory/entity_index.json"
    ):
        self.jsonl_path = Path(jsonl_path)
        self.index_path = Path(index_path)
        self.extractor = EntityExtractor()

        # In-memory index structure
        # entity_type -> entity_value -> [note_ids]
        self.index: Dict[str, Dict[str, List[str]]] = {
            'cve': {},
            'actor': {},
            'tool': {},
            'campaign': {},
            'sector': {}
        }

    def build(self) -> Dict[str, int]:
        """Rebuild index from all notes"""
        counts = {'notes': 0, 'entities': 0}

        for note in self._iterate_notes():
            counts['notes'] += 1
            self._index_note(note)

        self._save()
        counts['entities'] = sum(
            sum(len(ids) for ids in by_type.values())
            for by_type in self.index.values()
        )
        return counts

    def add_note(self, note_id: str, content_raw: str) -> Dict[str, List[str]]:
        """Index a single new note, save index immediately"""
        entities = self.extractor.extract_all(content_raw)
        self._index_note_entities(note_id, entities)
        self._save()
        return entities

    def remove_note(self, note_id: str) -> None:
        """Remove note from index"""
        for entity_type in self.index:
            for entity_value in list(self.index[entity_type].keys()):
                if note_id in self.index[entity_type][entity_value]:
                    self.index[entity_type][entity_value].remove(note_id)
                if not self.index[entity_type][entity_value]:
                    del self.index[entity_type][entity_value]
        self._save()

    def get_note_ids(self, entity_type: str, entity_value: str) -> List[str]:
        """Get all note IDs for an entity"""
        return self.index.get(entity_type, {}).get(entity_value.lower(), [])

    def has_entity(self, entity_type: str, entity_value: str) -> bool:
        """Check if entity exists in index"""
        return entity_value.lower() in self.index.get(entity_type, {})

    def get_cves(self) -> List[str]:
        return list(self.index['cve'].keys())

    def get_actors(self) -> List[str]:
        return list(self.index['actor'].keys())

    def get_tools(self) -> List[str]:
        return list(self.index['tool'].keys())

    def get_all_entities(self) -> Dict[str, int]:
        return {k: len(v) for k, v in self.index.items()}

    def stats(self) -> Dict:
        return {
            'total_entities': sum(len(v) for v in self.index.values()),
            'by_type': {k: len(v) for k, v in self.index.items()},
            'index_path': str(self.index_path)
        }

    def _index_note(self, note) -> None:
        """Extract and index entities from a note"""
        content = note.content.raw if hasattr(note, 'content') else str(note)
        entities = self.extractor.extract_all(content)
        self._index_note_entities(note.id, entities)

    def _index_note_entities(
        self,
        note_id: str,
        entities: Dict[str, List[str]]
    ) -> None:
        """Map entities to note ID"""
        mapping = {
            'cves': 'cve',
            'actors': 'actor',
            'tools': 'tool',
            'campaigns': 'campaign',
            'sectors': 'sector'
        }
        for src_key, dst_type in mapping.items():
            for entity in entities.get(src_key, []):
                key = entity.lower()
                if key not in self.index[dst_type]:
                    self.index[dst_type][key] = []
                if note_id not in self.index[dst_type][key]:
                    self.index[dst_type][key].append(note_id)

    def _iterate_notes(self):
        """Iterate all notes from JSONL"""
        if not self.jsonl_path.exists():
            return
        with open(self.jsonl_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        import sys
                        sys.path.insert(0, '/home/rolandpg/.openclaw/workspace')
                        from memory.note_schema import MemoryNote
                        yield MemoryNote(**json.loads(line))
                    except Exception:
                        pass

    def _save(self) -> None:
        """Persist index to disk"""
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f, indent=2)

    def load(self) -> bool:
        """Load index from disk"""
        if not self.index_path.exists():
            return False
        try:
            with open(self.index_path, 'r') as f:
                self.index = json.load(f)
            return True
        except Exception:
            return False


class Deduplicator:
    """
    Check for duplicate/similar notes before saving.
    Uses entity index (same CVE = auto-dup) + semantic similarity.
    """
    def __init__(
        self,
        indexer: EntityIndexer,
        similarity_threshold: float = 0.85
    ):
        self.indexer = indexer
        self.threshold = similarity_threshold

    def check_duplicate(
        self,
        content: str,
        domain: str = "general"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Check if content is a duplicate.
        Returns: (is_dup, reason, existing_note_id)
        """
        entities = self.indexer.extractor.extract_all(content)

        # Rule 1: Same CVE → auto duplicate
        for cve in entities.get('cves', []):
            if self.indexer.has_entity('cve', cve):
                note_ids = self.indexer.get_note_ids('cve', cve)
                return True, f"same CVE {cve}", note_ids[0] if note_ids else None

        # Rule 2: Same actor + same content hash → duplicate
        # (implemented via content hash later)

        return False, "", None

    def find_similar(
        self,
        content: str,
        k: int = 5
    ) -> List[Tuple[str, float, str]]:
        """
        Find notes with similar content.
        Returns: [(note_id, similarity, context), ...]
        """
        # Import here to avoid circular
        import sys
        sys.path.insert(0, '/home/rolandpg/.openclaw/workspace')
        from memory.vector_retriever import VectorRetriever

        retriever = VectorRetriever()
        results = retriever.retrieve(query=content, k=k)

        similar = []
        for note in results:
            # Recompute similarity on content field
            score = self._jaccard_similarity(
                content.lower(),
                note.content.raw.lower()
            )
            if score >= self.threshold:
                similar.append((note.id, score, note.semantic.context))

        return similar

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Simple word-level Jaccard similarity"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0


# CLI for testing
if __name__ == "__main__":
    import sys

    indexer = EntityIndexer()
    extractor = EntityExtractor()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "build":
            print("Building entity index...")
            counts = indexer.build()
            print(f"Done: {counts['notes']} notes, {counts['entities']} entity mappings")

        elif cmd == "stats":
            indexer.load()
            print(json.dumps(indexer.stats(), indent=2))

        elif cmd == "cves":
            indexer.load()
            print(f"CVEs tracked: {len(indexer.get_cves())}")
            for cve in indexer.get_cves()[:10]:
                print(f"  {cve}")

        elif cmd == "actors":
            indexer.load()
            print(f"Actors tracked: {len(indexer.get_actors())}")
            for actor in indexer.get_actors():
                print(f"  {actor}")

        elif cmd == "lookup" and len(sys.argv) > 3:
            etype = sys.argv[2]
            evalue = sys.argv[3]
            indexer.load()
            ids = indexer.get_note_ids(etype, evalue)
            print(f"{etype} '{evalue}': {len(ids)} notes")
            for i in ids:
                print(f"  {i}")

        elif cmd == "extract" and len(sys.argv) > 2:
            text = ' '.join(sys.argv[2:])
            ents = extractor.extract_all(text)
            print(json.dumps(ents, indent=2))

        elif cmd == "check" and len(sys.argv) > 2:
            content = ' '.join(sys.argv[2:])
            indexer.load()
            dedup = Deduplicator(indexer)
            is_dup, reason, note_id = dedup.check_duplicate(content)
            print(f"Duplicate: {is_dup} | Reason: {reason} | Note: {note_id}")
            if is_dup:
                similar = dedup.find_similar(content)
                print(f"Similar: {len(similar)} notes above threshold")
                for sid, score, ctx in similar[:3]:
                    print(f"  [{score:.2f}] {sid}: {ctx[:60]}")

    else:
        indexer.load()
        print(json.dumps(indexer.stats(), indent=2))
