"""
Entity Indexer - Fast entity-based note retrieval
A-MEM Agentic Memory Architecture V1.0

Conversational Entity Extension (RFC-001):
- Added LLM-based NER for conversational entity types
- Regex fast-path preserved for CTI entity types (CVE, actor, tool, campaign)
- New entity types: person, location, organization, event, activity, temporal
- EntityExtractor is now the single source of truth (NoteConstructor delegates here)
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class EntityExtractor:
    """Extract entities from text using regex (CTI) and LLM (conversational) patterns."""

    # Regex fast-path for CTI entities — deterministic, zero-latency
    REGEX_PATTERNS: Dict[str, re.Pattern] = {
        "cve": re.compile(r"(CVE-\d{4}-\d{4,})", re.IGNORECASE),
        "actor": re.compile(
            r"\b(apt\d+|apt\s+\d+|lazarus|sandworm|volt\s+typhoon|unc\d+)\b",
            re.IGNORECASE,
        ),
        "tool": re.compile(
            r"\b(cobalt\s+strike|metasploit|mimikatz|bloodhound|dropbear|empire|covenant)\b",
            re.IGNORECASE,
        ),
        "campaign": re.compile(
            r"\b(operation\s+\w+)\b",
            re.IGNORECASE,
        ),
    }

    # All entity types the system recognizes
    ENTITY_TYPES: List[str] = [
        # CTI (regex)
        "cve", "actor", "tool", "campaign",
        # Conversational (LLM)
        "person", "location", "organization", "event", "activity", "temporal",
    ]

    # NER prompt for conversational entity extraction
    NER_SYSTEM_PROMPT = (
        "You are a named entity recognizer. Extract entities from the text. "
        "Return ONLY a JSON object with these keys: "
        "person, location, organization, event, activity, temporal. "
        "Each key maps to a list of strings. "
        'Use empty lists for types not found. Example: {"person": ["Alice"], '
        '"location": ["Paris"], "organization": [], "event": ["birthday party"], '
        '"activity": ["swimming"], "temporal": ["last Tuesday"]}'
    )

    def extract_regex(self, text: str) -> Dict[str, List[str]]:
        """Extract CTI entities using regex patterns. Fast-path, no LLM needed."""
        results: Dict[str, List[str]] = {}
        for entity_type, pattern in self.REGEX_PATTERNS.items():
            matches = pattern.findall(text)
            results[entity_type] = list(
                set(m.lower().replace(" ", "-") for m in matches)
            )
        return results

    def extract_llm(self, text: str) -> Dict[str, List[str]]:
        """Extract conversational entities using LLM NER.

        Returns dict with person, location, organization, event, activity, temporal keys.
        Falls back to empty dicts on failure.
        """
        conversational_types = ["person", "location", "organization", "event", "activity", "temporal"]
        empty = {t: [] for t in conversational_types}

        if len(text.strip()) < 10:
            return empty

        try:
            from zettelforge.llm_client import generate

            prompt = f"Extract named entities from this text:\n\n{text[:2000]}\n\nJSON:"
            output = generate(
                prompt,
                max_tokens=300,
                temperature=0.0,
                system=self.NER_SYSTEM_PROMPT,
            )

            return self._parse_ner_output(output, conversational_types)

        except Exception:
            return empty

    def _parse_ner_output(
        self, output: str, expected_types: List[str]
    ) -> Dict[str, List[str]]:
        """Parse LLM NER output into normalized entity dict."""
        empty = {t: [] for t in expected_types}

        if not output or not output.strip():
            return empty

        # Strip markdown code fences if present
        cleaned = output.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            for part in parts:
                if part.strip().startswith("{"):
                    cleaned = part.strip()
                    break

        # Find JSON object in output
        json_match = re.search(r"\{[^}]+\}", cleaned, re.DOTALL)
        if not json_match:
            return empty

        try:
            parsed = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return empty

        if not isinstance(parsed, dict):
            return empty

        # Normalize values
        results: Dict[str, List[str]] = {}
        for etype in expected_types:
            values = parsed.get(etype, [])
            if isinstance(values, list):
                results[etype] = list(
                    set(
                        str(v).lower().strip()
                        for v in values
                        if v and isinstance(v, str) and len(v.strip()) > 1
                    )
                )
            else:
                results[etype] = []

        return results

    def extract_all(self, text: str, use_llm: bool = True) -> Dict[str, List[str]]:
        """Extract all entity types from text.

        Uses regex for CTI types (always) and LLM for conversational types
        (when use_llm=True and text is long enough).

        Args:
            text: Input text to extract entities from.
            use_llm: Whether to use LLM for conversational NER. Set False
                     for fast regex-only extraction.

        Returns:
            Dict mapping entity type to list of normalized entity values.
        """
        # Regex fast-path for CTI entities
        results = self.extract_regex(text)

        # LLM NER for conversational entities
        if use_llm:
            llm_results = self.extract_llm(text)
            results.update(llm_results)
        else:
            # Ensure all conversational types present with empty lists
            for etype in ["person", "location", "organization", "event", "activity", "temporal"]:
                if etype not in results:
                    results[etype] = []

        return results


class EntityIndexer:
    """Index notes by entities for fast lookup"""

    def __init__(self, index_path: Optional[str] = None):
        from zettelforge.memory_store import get_default_data_dir

        if index_path is None:
            index_path = get_default_data_dir() / "entity_index.json"
        self.index_path = Path(index_path)
        self.index: Dict[str, Dict[str, Set[str]]] = {
            etype: {} for etype in EntityExtractor.ENTITY_TYPES
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

    def save(self) -> None:
        """Save index to disk."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w") as f:
            data = {
                k: {kk: list(vv) for kk, vv in v.items()}
                for k, v in self.index.items()
            }
            json.dump(data, f, indent=2)

    def add_note(self, note_id: str, entities: Dict[str, List[str]]) -> None:
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

    def search_entities(self, query: str, limit: int = 10) -> Dict[str, List[str]]:
        """Search for entities matching a query across all types.

        Useful for recall when the entity type is unknown.

        Args:
            query: Search term (case-insensitive prefix match).
            limit: Maximum results per entity type.

        Returns:
            Dict mapping entity type to list of matching entity values.
        """
        query_lower = query.lower()
        results: Dict[str, List[str]] = {}
        for etype, entities in self.index.items():
            matches = [
                ev for ev in entities.keys() if ev.startswith(query_lower)
            ][:limit]
            if matches:
                results[etype] = matches
        return results

    def stats(self) -> Dict:
        """Get index statistics."""
        return {
            entity_type: {
                "unique_entities": len(entities),
                "total_mappings": sum(len(notes) for notes in entities.values()),
            }
            for entity_type, entities in self.index.items()
        }

    def build(self) -> Dict:
        """Rebuild index from all notes."""
        from zettelforge.memory_store import MemoryStore

        store = MemoryStore()
        self.index = {etype: {} for etype in EntityExtractor.ENTITY_TYPES}

        count = 0
        for note in store.iterate_notes():
            entities = self.extractor.extract_all(note.content.raw)
            self.add_note(note.id, entities)
            count += 1

        return {"notes_indexed": count, "stats": self.stats()}