"""
Note Construction Pipeline - A-MEM Zettelkasten-inspired
Roland Fleet Agentic Memory Architecture V1.0

Constructs structured memory notes from raw content with LLM-generated
semantic enrichment (keywords, tags, context, entities).
"""
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from note_schema import MemoryNote, Content, Semantic, Embedding, Links, Metadata
from embedding_utils import EmbeddingGenerator


class NoteConstructor:
    """Construct structured memory notes from raw content"""
    
    SYSTEM_PROMPT = """You are a semantic enrichment assistant for a memory system.
Given raw content, generate:
- context: A single sentence summarizing the key information (max 100 chars)
- keywords: 3-7 single-word or short-phrase key concepts
- tags: 3-5 category tags from: security_ops, project, personal, research, 
  cti, financial, social_media, infrastructure, or custom
- entities: Named entities (CVE-IDs, actor names, tool names, etc.)

Respond ONLY with valid JSON in this format:
{"context": "...", "keywords": [...], "tags": [...], "entities": [...]}"""
    
    def __init__(self, llm_model: str = "nemotron-3-nano"):
        self.llm_model = llm_model
        self.embedder = EmbeddingGenerator()
    
    def enrich(self, raw_content: str, source_type: str = "conversation",
               source_ref: str = "", domain: str = "general") -> MemoryNote:
        """Construct a complete memory note from raw content"""
        
        # Generate semantic enrichment via LLM
        semantic = self._generate_semantic(raw_content)
        
        # Generate embedding
        vector = self.embedder.embed_note_fields(
            raw_content,
            semantic.context,
            semantic.keywords,
            semantic.tags
        )
        
        # Compute input hash
        input_hash = self._compute_input_hash(raw_content, semantic)
        
        # Build note
        note = MemoryNote(
            id=self._generate_note_id(),
            version=1,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            evolved_from=None,
            evolved_by=[],
            content=Content(
                raw=raw_content,
                source_type=source_type,
                source_ref=source_ref
            ),
            semantic=semantic,
            embedding=Embedding(
                model=self.embedder.model,
                vector=vector,
                dimensions=len(vector),
                input_hash=input_hash
            ),
            links=Links(),
            metadata=Metadata(domain=domain)
        )
        
        return note
    
    def _generate_semantic(self, raw_content: str) -> Semantic:
        """Use LLM to generate semantic enrichment"""
        try:
            import ollama
            
            response = ollama.generate(
                model=self.llm_model,
                prompt=f"{self.SYSTEM_PROMPT}\n\nContent to enrich:\n{raw_content[:2000]}",
                format='json',
                options={'temperature': 0.3, 'num_predict': 200}
            )
            
            data = json.loads(response['response'])
            return Semantic(
                context=data.get('context', '')[:100],
                keywords=data.get('keywords', [])[:7],
                tags=data.get('tags', [])[:5],
                entities=data.get('entities', [])
            )
        except Exception as e:
            print(f"LLM enrichment failed: {e}")
            # Fallback: extract basic keywords
            words = raw_content.split()[:10]
            return Semantic(
                context=raw_content[:100],
                keywords=words,
                tags=['general'],
                entities=[]
            )
    
    def _compute_input_hash(self, raw_content: str, semantic: Semantic) -> str:
        """Compute SHA256 hash for change detection"""
        text = (
            raw_content +
            semantic.context +
            " ".join(semantic.keywords) +
            " ".join(semantic.tags)
        )
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _generate_note_id(self) -> str:
        """Generate unique note ID"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        import random
        suffix = str(random.randint(0, 9999)).zfill(4)
        return f"note_{ts}_{suffix}"


def test_note_construction():
    """Test the note construction pipeline"""
    print("Testing note construction pipeline...")
    
    constructor = NoteConstructor()
    
    # Test with sample content
    test_content = """
    Security Alert: Threat actor 'Volt Typhoon' (associated with PRC) has been observed
    targeting networking equipment from Asus, Cisco, Netgear, and others. The actor uses
    'living off the land' techniques and has maintained persistent access to victim
    networks for extended periods. CISA and FBI released joint advisory AA24-038A.
    IOCs include multiple IP addresses and战术Tactics: T1071, T1106, affecting 
    sectors: Defense Industrial Base, Communications, and Government.
    """
    
    note = constructor.enrich(
        raw_content=test_content,
        source_type="cti_ingestion",
        source_ref="cisa_advisory_aa24_038a",
        domain="security_ops"
    )
    
    print(f"✓ Note constructed: {note.id}")
    print(f"  Version: {note.version}")
    print(f"  Context: {note.semantic.context}")
    print(f"  Keywords: {note.semantic.keywords}")
    print(f"  Tags: {note.semantic.tags}")
    print(f"  Entities: {note.semantic.entities}")
    print(f"  Embedding dims: {len(note.embedding.vector)}")
    print(f"  Domain: {note.metadata.domain}")
    
    # Save to store
    from memory_store import MemoryStore
    store = MemoryStore()
    store.write_note(note)
    print(f"✓ Note written to store")
    print(f"  Total notes in store: {store.count_notes()}")
    
    return note


if __name__ == "__main__":
    test_note_construction()
