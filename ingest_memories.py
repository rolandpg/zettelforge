import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from memory import get_memory_manager

mm = get_memory_manager()

# Ingest memory architecture work
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

for m in memories:
    note = mm.remember(**m)
    print(f"Created: {note.id}")

print(f"\nTotal notes: {mm.store.count_notes()}")
print(mm.get_stats())