"""
Link Generation Pipeline - A-MEM Zettelkasten-inspired
Roland Fleet Agentic Memory Architecture V1.0

Generates conceptual links between notes beyond pure vector similarity.
Relationship types: SUPPORTS, CONTRADICTS, EXTENDS, CAUSES, RELATED
"""
import json
import ollama
from typing import List, Dict, Tuple, Optional
from note_schema import MemoryNote


class LinkGenerator:
    """Generate conceptual links between memory notes"""
    
    SYSTEM_PROMPT = """You are a link analysis assistant for a memory system.
Given a new note and candidate related notes, determine which notes have 
meaningful relationships.

Relationship types:
- SUPPORTS: Corroborates or confirms the information
- CONTRADICTS: Conflicts or refutes the information  
- EXTENDS: Builds upon or adds nuance to the information
- CAUSES: Has a causal relationship with the information
- RELATED: Topically connected but not in above categories

Respond ONLY with valid JSON array of link pairs:
[{"target_id": "note_xxx", "relationship": "TYPE", "reason": "brief explanation"}, ...]

Only include pairs with meaningful relationships. Empty array if none found."""

    def __init__(self, llm_model: str = "qwen2.5:3b", similarity_threshold: float = 0.65):
        self.llm_model = llm_model
        self.similarity_threshold = similarity_threshold
        self._embedder = None  # Lazy load
    
    def _get_embedder(self):
        if self._embedder is None:
            from embedding_utils import EmbeddingGenerator
            self._embedder = EmbeddingGenerator()
        return self._embedder
    
    def generate_links(
        self, 
        new_note: MemoryNote, 
        candidate_notes: List[MemoryNote],
        max_candidates: int = 20
    ) -> List[Dict]:
        """Generate links from new_note to candidate notes"""
        
        if not candidate_notes:
            return []
        
        # Limit candidates
        candidates = candidate_notes[:max_candidates]
        
        # Also pull entity-matched candidates for more targeted linking
        entity_candidates = self._get_entity_correlated_notes(new_note, candidate_notes)
        
        # Deduplicate — entity candidates are already in candidate_notes but prioritizing them
        candidate_ids = {n.id for n in candidates}
        prioritized = candidates + [n for n in entity_candidates if n.id not in candidate_ids]
        prioritized = prioritized[:max_candidates + 5]
        
        # Build prompt with note content (use prioritized candidates)
        prompt = self._build_link_prompt(new_note, prioritized)
        
        # Get LLM analysis
        try:
            response = ollama.generate(
                model=self.llm_model,
                prompt=prompt,
                format='json',
                options={'temperature': 0.3, 'num_predict': 1000}
            )
            raw_response = response['response']
            print(f"DEBUG LLM response: {raw_response[:200]}...")
            
            # Try to extract JSON from response
            try:
                links = json.loads(raw_response)
                print(f"DEBUG: Parsed JSON directly, type={type(links)}")
            except json.JSONDecodeError as je:
                # Try to find JSON array in response
                import re
                print(f"DEBUG: JSON parse failed: {je}")
                print(f"DEBUG: Raw response length: {len(raw_response)}")
                json_match = re.search(r'\[.*\]', raw_response, re.DOTALL)
                if json_match:
                    links = json.loads(json_match.group())
                    print(f"DEBUG: Extracted JSON array, len={len(links)}")
                else:
                    print(f"Failed to find JSON array in response")
                    return []
            
            # Handle different response structures
            # Structure 1: {"relationships": [...]} 
            # Structure 2: [...]
            # Structure 3: {"links": [...]} 
            if isinstance(links, dict):
                if 'relationships' in links:
                    links = links['relationships']
                elif 'links' in links:
                    links = links['links']
                else:
                    links = []
            
            # Validate and filter links
            valid_links = []
            valid_relationships = {'SUPPORTS', 'CONTRADICTS', 'EXTENDS', 'CAUSES', 'RELATED'}
            valid_ids = {n.id for n in prioritized}
            
            for link in links:
                if isinstance(link, dict) and link.get('target_id') in valid_ids:
                    if link.get('relationship') in valid_relationships:
                        valid_links.append({
                            'target_id': link['target_id'],
                            'relationship': link['relationship'],
                            'reason': link.get('reason', '')[:100]
                        })
            
            return valid_links
            
        except Exception as e:
            print(f"Link generation failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_entity_correlated_notes(
        self,
        new_note: MemoryNote,
        candidate_notes: List[MemoryNote]
    ) -> List[MemoryNote]:
        """
        Pull entity-correlated notes for targeted link generation.
        Uses entity index for fast lookup of same CVE/actor/tool/campaign notes.
        """
        try:
            import sys
            sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')
            from entity_indexer import EntityExtractor, EntityIndexer
            
            extractor = EntityExtractor()
            entities = extractor.extract_all(new_note.content.raw)
            
            if not entities or all(not v for v in entities.values()):
                return []
            
            idx = EntityIndexer()
            idx.load()
            
            correlated = []
            candidate_ids = {n.id for n in candidate_notes}
            
            entity_map = [
                ('cves', 'cve'),
                ('actors', 'actor'),
                ('tools', 'tool'),
                ('campaigns', 'campaign'),
            ]
            
            for src_key, dst_type in entity_map:
                for entity in entities.get(src_key, []):
                    for nid in idx.get_note_ids(dst_type, entity.lower()):
                        if nid not in candidate_ids and nid != new_note.id:
                            note = self._get_note_by_id(nid)
                            if note and note.id not in {c.id for c in correlated}:
                                correlated.append(note)
            
            return correlated
            
        except Exception as e:
            print(f"Entity correlation failed: {e}")
            return []
    
    def _get_note_by_id(self, note_id: str) -> Optional[MemoryNote]:
        """Retrieve a note by ID from the store"""
        try:
            from memory_store import MemoryStore
            store = MemoryStore()
            return store.get_note_by_id(note_id)
        except Exception:
            return None

    def _build_link_prompt(self, new_note: MemoryNote, candidates: List[MemoryNote]) -> str:
        """Build prompt for link analysis"""
        
        # New note summary - keep short
        new_note_text = f"""NEW NOTE ({new_note.id}):
Keywords: {', '.join(new_note.semantic.keywords)}
Tags: {', '.join(new_note.semantic.tags)}
Summary: {new_note.semantic.context}"""
        
        # Candidate summaries - truncate content
        candidate_texts = []
        for i, note in enumerate(candidates[:10], 1):  # Limit to 10 candidates
            candidate_texts.append(f"""CANDIDATE {i} ({note.id}):
Keywords: {', '.join(note.semantic.keywords)}
Tags: {', '.join(note.semantic.tags)}
Summary: {note.semantic.context}""")
        
        return f"""{self.SYSTEM_PROMPT}

{new_note_text}

{''.join(candidate_texts)}

Return JSON with links for the NEW NOTE."""
    
    def update_note_links(
        self, 
        note: MemoryNote, 
        outgoing_links: List[Dict],
        all_notes: List[MemoryNote]
    ) -> MemoryNote:
        """Update note with generated links (bidirectional)"""
        
        # Add outgoing links
        note.links.related = [
            l['target_id'] for l in outgoing_links 
            if l['relationship'] != 'SUPERSEDED_BY'
        ]
        
        # Track superseded relationships
        for link in outgoing_links:
            if link['relationship'] == 'SUPERSEDES':
                note.links.superseded_by = link['target_id']
        
        # Add causal chain links
        for link in outgoing_links:
            if link['relationship'] == 'CAUSES':
                note.links.causal_chain.append(link['target_id'])
        
        return note


def test_link_generation():
    """Test link generation between notes"""
    print("Testing link generation pipeline...")
    
    from memory_store import MemoryStore
    from note_constructor import NoteConstructor
    
    store = MemoryStore()
    constructor = NoteConstructor()
    generator = LinkGenerator()
    
    # Create test notes with intentionally related content
    notes_data = [
        {
            'content': "Volt Typhoon threat actor (PRC-linked) targeting network equipment from Asus, Cisco, Netgear. Using living-off-the-land techniques. CISA advisory AA24-038A.",
            'domain': 'security_ops',
            'source': 'cisa_advisory'
        },
        {
            'content': "CISA and FBI joint advisory AA24-038A details Volt Typhoon TTPs: T1071 (Application Layer Protocol), T1106 (Native API). Sectors: DIB, Communications, Government.",
            'domain': 'security_ops',
            'source': 'cisa_advisory'
        },
        {
            'content': "AA24-038A recommends: segment networks, monitor for LOTL techniques, implement EDR and logging. IOCs include IP addresses 192.168.1.x range.",
            'domain': 'security_ops',
            'source': 'cisa_advisory'
        },
        {
            'content': "MSSP market showing 15% YoY growth. PE firms increasingly acquiring MSSPs for DIB consolidation. CMMC compliance driving demand.",
            'domain': 'financial',
            'source': 'market_analysis'
        },
        {
            'content': "New CVE-2024-3094 critical vulnerability in liblzma. Affects Fedora, Debian, Ubuntu. Supply chain compromise suspected. CVSS 10.0.",
            'domain': 'security_ops',
            'source': 'cve_alert'
        },
    ]
    
    # Construct and store notes
    print("\n1. Creating test notes...")
    for data in notes_data:
        note = constructor.enrich(
            raw_content=data['content'],
            source_type='test',
            source_ref=data['source'],
            domain=data['domain']
        )
        store.write_note(note)
        print(f"   ✓ Created {note.id} [{note.metadata.domain}]")
    
    # Get all notes
    all_notes = store.read_all_notes()
    print(f"\n2. Total notes in store: {len(all_notes)}")
    
    # Test link generation for the last note (most recent)
    new_note = all_notes[-1]
    candidates = [n for n in all_notes if n.id != new_note.id]
    
    print(f"\n3. Generating links for {new_note.id}...")
    print(f"   Candidates: {len(candidates)} notes")
    
    links = generator.generate_links(new_note, candidates)
    
    print(f"\n4. Link generation results: {len(links)} links found")
    for link in links:
        print(f"   - {new_note.id} --[{link['relationship']}]--> {link['target_id']}")
        print(f"     Reason: {link['reason']}")
    
    # Update and re-write note with links
    updated_note = generator.update_note_links(new_note, links, all_notes)
    
    print(f"\n✓ Link generation test PASSED")
    print(f"  Note {updated_note.id} now has {len(updated_note.links.related)} related links")
    
    return updated_note


if __name__ == "__main__":
    test_link_generation()
