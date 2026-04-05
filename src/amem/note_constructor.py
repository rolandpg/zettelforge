"""
Note Constructor - LLM-powered note enrichment
A-MEM Agentic Memory Architecture V1.0
"""
import re
import json
from datetime import datetime
from typing import Dict, List, Optional

from amem.note_schema import MemoryNote, Content, Semantic, Embedding, Metadata
from amem.vector_memory import get_embedding


class NoteConstructor:
    """Construct enriched memory notes from raw content"""

    ENTITY_PATTERNS = {
        'cves': re.compile(r'(CVE-\d{4}-\d{4,})', re.IGNORECASE),
        'actors': re.compile(
            r'\b(apt\d+|apt\s+\d+|apt\s+[a-z]+|lazarus|sandworm|\n            volt\s+typhoon|unc\d+|cozy\s+bear|fancy\s+bear)\b',
            re.IGNORECASE
        ),
        'tools': re.compile(
            r'\b(cobalt\s+strike|metasploit|mimikatz|bloodhound|\n            empire| Covenant)\b',
            re.IGNORECASE
        ),
        'campaigns': re.compile(
            r'\b(operation\s+\w+|campaign\s+\w+)\b',
            re.IGNORECASE
        ),
    }

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text using regex patterns."""
        entities = {}
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = pattern.findall(text)
            # Normalize
            entities[entity_type] = list(set(m.lower().replace(' ', '-') for m in matches))
        return entities

    def construct(
        self,
        raw_content: str,
        source_type: str = "conversation",
        source_ref: str = "",
        domain: str = "general"
    ) -> MemoryNote:
        """Construct a note from raw content with automatic enrichment."""
        
        # Extract entities
        entities = self.extract_entities(raw_content)
        all_entities = []
        for entity_list in entities.values():
            all_entities.extend(entity_list)
        
        # Build semantic enrichment (simplified - no LLM)
        context = self._generate_context(raw_content)
        keywords = self._extract_keywords(raw_content)
        tags = [domain] if domain else []
        
        # Generate embedding
        embedding_vector = get_embedding(raw_content[:1000])
        
        return MemoryNote(
            id="",  # Will be set by store
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            content=Content(
                raw=raw_content,
                source_type=source_type,
                source_ref=source_ref
            ),
            semantic=Semantic(
                context=context,
                keywords=keywords[:7],
                tags=tags[:5],
                entities=all_entities
            ),
            embedding=Embedding(
                vector=embedding_vector,
                model="nomic-embed-text"
            ),
            metadata=Metadata(
                domain=domain,
                tier="B"
            )
        )

    def _generate_context(self, text: str) -> str:
        """Generate one-sentence context summary."""
        # Simple extraction: first sentence or first 100 chars
        sentences = text.split('.')
        if sentences:
            context = sentences[0].strip()
            if len(context) > 150:
                context = context[:150] + "..."
            return context
        return text[:100]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # Filter common words
        stopwords = {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they'}
        keywords = [w for w in words if w not in stopwords]
        # Return most common
        from collections import Counter
        return [word for word, count in Counter(keywords).most_common(10)]
