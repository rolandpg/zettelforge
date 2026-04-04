#!/usr/bin/env python3
import sys
import json
from datetime import datetime
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from memory_store import MemoryStore
from note_schema import MemoryNote, Content, Semantic, Embedding, Links, Metadata

def create_basic_note(content, source_type, source_ref, domain):
    """Create a basic note without Ollama enrichment"""
    note_id = f"note_{int(datetime.now().timestamp()*1000)}"
    
    note = MemoryNote(
        id=note_id,
        version=1,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        content=Content(
            raw=content,
            source_type=source_type,
            source_ref=source_ref
        ),
        semantic=Semantic(
            context="Ingested memory content",
            keywords=[],
            tags=[],
            entities=[]
        ),
        embedding=Embedding(
            model="ingested",
            vector=[0.0] * 768,  # Placeholder vector
            dimensions=768
        ),
        links=Links(
            related=[],
            superseded_by=None,
            causal_chain=[]
        ),
        metadata=Metadata(
            access_count=0,
            confidence=0.8,  # Default confidence for ingested content
            evolution_count=0,
            domain=domain
        )
    )
    
    return note

def main():
    # Initialize store
    store = MemoryStore(
        jsonl_path="/home/rolandpg/.openclaw/workspace/memory/notes.jsonl",
        lance_path="/home/rolandpg/.openclaw/workspace/vectordb/"
    )
    
    # Memories to ingest
    memories = [
        {
            'content': '''Completed Roland Fleet Agentic Memory System Architecture V1.1 on DGX Spark GB10.

Storage: Hot tier (1TB NVMe SSD) for active notes and vector DB. Cold tier (8TB USB HDD) for archives and backups.

Stack: LanceDB for vectors, nomic-embed-text-v2-moe for embeddings, nemotron-3-nano for memory ops, nemotron-3-super for reasoning.

Four operations: Note Construction (LLM semantic enrichment), Link Generation (SUPPORTS/CONTRADICTS/EXTENDS/CAUSES/RELATED), Memory Evolution (versioned with confidence decay), Retrieval (vector + link expansion).

Phases 1-6 complete. Version tracking, confidence scoring, max 5 evolution hops. systemd timers for daily/weekly maintenance.

Load test: 103-271ms retrieval, 2.7s construction, 100% evolution accuracy.''',
            'source_type': 'task_output',
            'source_ref': 'memory_architecture_build',
            'domain': 'project'
        },
        {
            'content': '''Article published on X/Twitter: "Building an Agentic Memory System for AI Agents: The Roland Fleet Experience"

Cognee failure story included - weeks of CUDA/ARM issues before finding A-MEM. A-MEM inspired lean implementation.

Key message: For local-first, privacy-preserving memory for agent fleets, A-MEM approach with production safeguards (versioning, rollback, confidence tracking) gets you most of the way there.

Benchmarks: 85-93% token reduction vs context-stuffing, 103-271ms retrieval latency, 2.7s note construction.''',
            'source_type': 'social_media',
            'source_ref': 'x_post_thread',
            'domain': 'project'
        },
        {
            'content': '''CTI Pipeline Status: Dark web observatory running with 25 workers. IOC validation needs BTC wallet regex fix (26-35 chars, 1/3/bc1 prefix).

Alert system: Cron at 6AM/6PM daily. Rules: Critical CVEs (CVSS>=9), Summit 7 brand mentions, APT activity, DIB sector targeting.

Recent IOCs: Volt Typhoon (PRC, AA24-038A, network equipment, LOTL), Stryker attack (CISA alert), CVE-2024-3094 (liblzma, CVSS 10.0, supply chain).

Workspace: ~/cti-workspace/ with graph DB at data/cti/cti.db.''',
            'source_type': 'cti_ingestion',
            'source_ref': 'cti_pipeline_status',
            'domain': 'security_ops'
        }
    ]
    
    # Create and store notes
    notes_created = []
    for mem_data in memories:
        note = create_basic_note(
            content=mem_data['content'],
            source_type=mem_data['source_type'],
            source_ref=mem_data['source_ref'],
            domain=mem_data['domain']
        )
        
        # Write to store
        store.write_note(note)
        notes_created.append(note.id)
        print(f"Created: {note.id}")
    
    # Print final stats
    print(f"\nTotal notes: {store.count_notes()}")
    
    # Get additional stats if available
    try:
        stats = {
            'total_notes': store.count_notes(),
            'store_path': str(store.jsonl_path)
        }
        print(f"Stats: {json.dumps(stats, indent=2)}")
    except Exception as e:
        print(f"Could not get detailed stats: {e}")

if __name__ == "__main__":
    main()