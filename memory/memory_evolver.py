"""
Memory Evolution Pipeline - A-MEM Zettelkasten-inspired
Roland Fleet Agentic Memory Architecture V1.0

Implements memory evolution: when new information arrives, existing memories
can be refined based on what the new information reveals.
"""
import json
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from note_schema import MemoryNote
from memory_store import MemoryStore


class EvolutionDecider:
    """Decide if new note should trigger updates to existing memories"""
    
    SYSTEM_PROMPT = """You are a memory evolution assessor. Given a new note and a candidate existing note,
determine if the existing note should be updated based on the new information.

Decision options:
- NO_CHANGE: The notes are independent, no update needed
- UPDATE_CONTEXT: The existing note's context summary should be revised
- UPDATE_TAGS: The existing note's tags should be updated
- UPDATE_BOTH: Both context and tags need revision
- SUPERSEDE: The new information fundamentally changes understanding; archive old note

Respond ONLY with valid JSON:
{"decision": "NO_CHANGE|UPDATE_CONTEXT|UPDATE_TAGS|UPDATE_BOTH|SUPERSEDE", "reason": "brief explanation"}"""
    
    def __init__(self, llm_model: str = "nemotron-3-nano"):
        self.llm_model = llm_model
    
    def assess(
        self, 
        new_note: MemoryNote, 
        existing_note: MemoryNote
    ) -> Tuple[str, str]:
        """
        Assess whether existing_note should evolve based on new_note.
        
        Returns: (decision, reason)
        """
        try:
            import ollama
            
            prompt = f"""{self.SYSTEM_PROMPT}

NEW NOTE:
Keywords: {', '.join(new_note.semantic.keywords)}
Tags: {', '.join(new_note.semantic.tags)}
Context: {new_note.semantic.context}
Content: {new_note.content.raw[:300]}

EXISTING NOTE ({existing_note.id}):
Keywords: {', '.join(existing_note.semantic.keywords)}
Tags: {', '.join(existing_note.semantic.tags)}  
Context: {existing_note.semantic.context}
Content: {existing_note.content.raw[:300]}
Confidence: {existing_note.metadata.confidence}
Evolution count: {existing_note.metadata.evolution_count}

Assess if the existing note should evolve."""
            
            response = ollama.generate(
                model=self.llm_model,
                prompt=prompt,
                format='json',
                options={'temperature': 0.3, 'num_predict': 150}
            )
            
            data = json.loads(response['response'])
            decision = data.get('decision', 'NO_CHANGE')
            reason = data.get('reason', '')[:100]
            
            # Enforce evolution hop limit
            if decision != 'NO_CHANGE' and existing_note.metadata.evolution_count >= 5:
                decision = 'NO_CHANGE'
                reason = 'Max evolution limit reached (5)'
            
            return decision, reason
            
        except Exception as e:
            print(f"Evolution assessment failed: {e}")
            return 'NO_CHANGE', f'Assessment error: {e}'


class MemoryEvolver:
    """Execute memory evolution with versioning and archival"""
    
    COLD_ARCHIVE = "/media/rolandpg/USB-HDD/archive"
    
    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        evolver: Optional[EvolutionDecider] = None
    ):
        self.store = store or MemoryStore()
        self.evolver = evolver or EvolutionDecider()
    
    def evolve_note(
        self,
        new_note: MemoryNote,
        existing_note: MemoryNote,
        decision: str,
        reason: str
    ) -> MemoryNote:
        """
        Apply evolution decision to existing note.
        Creates new version, archives old version to cold storage.
        """
        
        # Archive current version to cold storage
        self._archive_version(existing_note)
        
        # Apply updates based on decision
        if decision == 'UPDATE_CONTEXT':
            existing_note.semantic.context = self._generate_updated_context(
                existing_note, new_note
            )
        elif decision == 'UPDATE_TAGS':
            existing_note.semantic.tags = self._merge_tags(
                existing_note.semantic.tags, new_note.semantic.tags
            )
        elif decision == 'UPDATE_BOTH':
            existing_note.semantic.context = self._generate_updated_context(
                existing_note, new_note
            )
            existing_note.semantic.tags = self._merge_tags(
                existing_note.semantic.tags, new_note.semantic.tags
            )
        
        # Update evolution metadata
        existing_note.metadata.evolution_count += 1
        existing_note.evolved_by.append(new_note.id)
        existing_note.evolved_from = existing_note.id  # Mark as evolved
        
        # Confidence decay
        existing_note.metadata.confidence = min(existing_note.metadata.confidence, 0.95)
        
        # Version bump
        existing_note.version += 1
        existing_note.updated_at = datetime.now().isoformat()
        
        return existing_note
    
    def _archive_version(self, note: MemoryNote) -> None:
        """Archive note version to cold storage"""
        try:
            archive_dir = Path(self.COLD_ARCHIVE)
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Write archived version with metadata
            archive_file = archive_dir / f"{note.id}_v{note.version}.jsonl"
            with open(archive_file, 'w') as f:
                f.write(note.model_dump_json() + "\n")
            
            print(f"  Archived: {note.id} v{note.version} -> {archive_file}")
        except Exception as e:
            print(f"Archive failed: {e}")
    
    def _generate_updated_context(
        self, 
        existing: MemoryNote, 
        new: MemoryNote
    ) -> str:
        """Generate updated context summary"""
        try:
            import ollama
            
            prompt = f"""Update this note's context summary based on new information.

ORIGINAL CONTEXT: {existing.semantic.context}
ORIGINAL CONTENT: {existing.content.raw[:200]}

NEW INFORMATION: {new.content.raw[:200]}
NEW CONTEXT: {new.semantic.context}

Write a revised context summary that incorporates the new information while
preserving essential truth from the original. Max 100 characters.
Response: """
            
            response = ollama.generate(
                model=self.evolver.llm_model,
                prompt=prompt,
                options={'temperature': 0.3, 'num_predict': 50}
            )
            
            return response['response'].strip()[:100]
            
        except Exception as e:
            print(f"Context update failed: {e}")
            return existing.semantic.context
    
    def _merge_tags(
        self, 
        existing_tags: List[str], 
        new_tags: List[str]
    ) -> List[str]:
        """Merge tags from new note into existing tags"""
        merged = list(set(existing_tags + new_tags))
        return merged[:5]  # Max 5 tags
    

    def _get_entity_related_notes(
        self,
        new_note: MemoryNote
    ) -> List[MemoryNote]:
        """Get notes that share entities with new_note but aren't linked yet"""
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
            
            related = []
            related_ids = set(new_note.links.related)
            related_ids.add(new_note.id)
            
            entity_map = [
                ('cves', 'cve'),
                ('actors', 'actor'),
                ('tools', 'tool'),
                ('campaigns', 'campaign'),
            ]
            
            for src_key, dst_type in entity_map:
                for entity in entities.get(src_key, []):
                    for nid in idx.get_note_ids(dst_type, entity.lower()):
                        if nid not in related_ids:
                            note = self._get_note_by_id(nid)
                            if note and note.id not in {n.id for n in related}:
                                related.append(note)
                                related_ids.add(nid)
            
            return related
            
        except Exception as e:
            print(f"Entity correlation for evolution failed: {e}")
            return []
    
    def _get_note_by_id(self, note_id: str) -> Optional[MemoryNote]:
        """Retrieve a note by ID from the store"""
        try:
            store = MemoryStore()
            return store.get_note_by_id(note_id)
        except Exception:
            return None

    def run_evolution_cycle(self, new_note: MemoryNote) -> Dict:
        """
        Run full evolution cycle: assess all related notes, apply updates.
        Now also checks entity-correlated notes (same CVE/actor/tool/campaign)
        even if they aren't yet linked.
        Returns summary of changes made.
        """
        
        print(f"\n=== Evolution Cycle for {new_note.id} ===")
        
        # Get all existing notes (deduplicate by id)
        all_notes_map = {n.id: n for n in self.store.iterate_notes()}
        all_notes = list(all_notes_map.values())
        
        # Find related notes via links
        related_ids = set(new_note.links.related)
        
        # Also find notes that link TO this new note
        for note in all_notes:
            if new_note.id in note.links.related:
                related_ids.add(note.id)
        
        # NEW: Add entity-correlated notes to evolution assessment
        entity_related = self._get_entity_related_notes(new_note)
        for note in entity_related:
            if note.id != new_note.id:
                related_ids.add(note.id)
        
        if not related_ids:
            print("  No related notes found, skipping evolution")
            return {'evolved': [], 'assessed': 0}
        
        # Assess each related note
        evolved = []
        for note in all_notes:
            if note.id not in related_ids:
                continue
            
            if note.id == new_note.id:
                continue
            
            decision, reason = self.evolver.assess(new_note, note)
            
            print(f"  Assessed {note.id[:20]}... -> {decision}")
            
            if decision != 'NO_CHANGE':
                updated = self.evolve_note(new_note, note, decision, reason)
                # Re-write updated note to store (via store object)
                self.store._rewrite_note(updated)
                evolved.append({
                    'note_id': note.id,
                    'decision': decision,
                    'reason': reason
                })
        
        print(f"  Evolved {len(evolved)} notes")
        return {'evolved': evolved, 'assessed': len(related_ids)}


def test_evolution():
    """Test memory evolution with contradictory information"""
    print("=" * 60)
    print("Testing Memory Evolution Pipeline")
    print("=" * 60)
    
    from note_constructor import NoteConstructor
    
    store = MemoryStore()
    evolver = EvolutionDecider()
    constructor = NoteConstructor()
    
    # Create initial note
    print("\n1. Creating initial note about Volt Typhoon...")
    initial_content = """Volt Typhoon is a PRC-linked threat actor that primarily conducts
espionage and data theft. They target government agencies and defense contractors.
TTPs include living-off-the-land techniques."""
    
    initial_note = constructor.enrich(
        raw_content=initial_content,
        source_type="test",
        source_ref="evolution_test_1",
        domain="security_ops"
    )
    store.write_note(initial_note)
    print(f"   Created: {initial_note.id}")
    print(f"   Context: {initial_note.semantic.context}")
    print(f"   Version: {initial_note.version}, Confidence: {initial_note.metadata.confidence}")
    
    # Create contradictory update
    print("\n2. Creating update with new intelligence...")
    update_content = """UPDATE: Volt Typhoon has been observed conducting DESTRUCTIVE attacks
on infrastructure, not just espionage. FBI and CISA confirm destructive wiper malware
deployment against power grids and water treatment facilities in Hawaii."""
    
    update_note = constructor.enrich(
        raw_content=update_content,
        source_type="test",
        source_ref="evolution_test_2",
        domain="security_ops"
    )
    update_note.links.related = [initial_note.id]
    store.write_note(update_note)
    print(f"   Created: {update_note.id}")
    print(f"   Context: {update_note.semantic.context}")
    
    # Run evolution
    print("\n3. Running evolution cycle...")
    memory_evolver = MemoryEvolver(store, evolver)
    result = memory_evolver.run_evolution_cycle(update_note)
    
    print(f"\n4. Evolution results:")
    print(f"   Assessed: {result['assessed']} notes")
    print(f"   Evolved: {len(result['evolved'])} notes")
    
    for e in result['evolved']:
        print(f"   - {e['note_id']}: {e['decision']}")
        print(f"     Reason: {e['reason']}")
    
    # Check evolved note
    print("\n5. Verifying evolved note...")
    evolved_note = store.get_note_by_id(initial_note.id)
    if evolved_note:
        print(f"   ID: {evolved_note.id}")
        print(f"   Version: {evolved_note.version}")
        print(f"   Context: {evolved_note.semantic.context}")
        print(f"   Confidence: {evolved_note.metadata.confidence}")
        print(f"   Evolution count: {evolved_note.metadata.evolution_count}")
        print(f"   Evolved by: {evolved_note.evolved_by}")
    
    # Check archive
    print("\n6. Checking cold storage archive...")
    archive_dir = Path("/media/rolandpg/USB-HDD/archive")
    if archive_dir.exists():
        archives = list(archive_dir.glob("*.jsonl"))
        print(f"   Archived versions: {len(archives)}")
        for a in archives[-3:]:
            print(f"   - {a.name}")
    
    print("\n" + "=" * 60)
    print("✓ Memory Evolution test complete")
    print("=" * 60)


if __name__ == "__main__":
    test_evolution()
