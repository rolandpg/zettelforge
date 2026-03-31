#!/usr/bin/env python3
"""
vector_memory.py — Cross-session semantic memory using LanceDB + Nomic embeddings

Stores memory entries as vectors for semantic search across ALL sessions.
No external API calls. Everything local.

Usage:
    from vector_memory import VectorMemory
    vm = VectorMemory('/path/to/workspace')
    vm.init()                                    # Init DB
    vm.add('something worth remembering', tags=['decision', 'patrick'], session='main')
    results = vm.search('what did we decide about x?')  # Returns top-k matches
    vm.sync_from_memory_files()                  # One-time historical import
"""

import os
import sys
import json
import hashlib
import uuid
import re
from datetime import datetime
from pathlib import Path

# ── Embedding ──────────────────────────────────────────────────────────────────

def get_embedding(text: str, model: str = 'nomic-embed-text-v2-moe:latest') -> list:
    """Generate embedding via local Ollama."""
    import ollama
    resp = ollama.embeddings(model=model, prompt=text)
    return resp.get('embedding', [])


def get_embedding_batch(texts: list, model: str = 'nomic-embed-text-v2-moe:latest') -> list:
    """Batch embed multiple texts via Ollama."""
    import ollama
    embeddings = []
    for text in texts:
        resp = ollama.embeddings(model=model, prompt=text)
        embeddings.append(resp.get('embedding', []))
    return embeddings


# ── LanceDB Schema ────────────────────────────────────────────────────────────

def _build_schema():
    import pyarrow as pa
    return pa.schema([
        ('id',          pa.string()),      # UUID
        ('text',        pa.string()),      # Memory text content
        ('embedding',   pa.list_(pa.float32(), 768)),  # nomic-embed-text-v2-moe
        ('content_hash', pa.string()),     # SHA256 of text — dedup key
        ('timestamp',   pa.string()),     # ISO timestamp when added
        ('source',      pa.string()),      # 'memory', 'daily', 'session', 'briefing'
        ('session_key', pa.string()),      # e.g. 'main', 'telegram:123'
        ('tags',        pa.list_(pa.string())),
        ('metadata',    pa.string()),      # JSON misc field
    ])


# ── VectorMemory ───────────────────────────────────────────────────────────────

class VectorMemory:
    """
    Local cross-session semantic memory store.

    Stores entries in LanceDB with Nomic embeddings. Enables semantic search
    across all past sessions, not just today's notes.
    """

    def __init__(self, workspace_path: str = None):
        if workspace_path is None:
            workspace_path = os.path.expanduser('~/.openclaw/workspace')
        self.workspace = Path(workspace_path)
        self.db_path = self.workspace / 'memory' / 'vector_memory.lance'
        self.db = None
        self.table = None
        self.embedding_model = 'nomic-embed-text-v2-moe:latest'
        self._embedding_cache = {}  # content_hash -> embedding

    # ── Init ──────────────────────────────────────────────────────────────────

    def init(self):
        """Connect to or create the LanceDB database."""
        import lancedb
        self.db = lancedb.connect(str(self.db_path))
        self._ensure_table()

    def _ensure_table(self):
        """Create table if it doesn't exist."""
        if 'memories' not in self.db.list_tables():
            self.db.create_table('memories', schema=_build_schema())
        self.table = self.db.open_table('memories')

    # ── Core Ops ───────────────────────────────────────────────────────────────

    def _content_hash(self, text: str) -> str:
        """Stable hash of text content for dedup."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]

    def _chunk_text(self, text: str, max_tokens: int = 512, overlap: int = 128) -> list:
        """
        Simple token-aware text chunker.
        Splits on sentence boundaries, groups up to max_tokens.
        Overlap ensures context continuity.
        """
        # Rough token estimate: 1 token ≈ 4 chars
        max_chars = max_tokens * 4
        overlap_chars = overlap * 4

        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks, current = [], ''

        for sent in sentences:
            if len(current) + len(sent) < max_chars:
                current += ' ' + sent
            else:
                if current.strip():
                    chunks.append(current.strip())
                # Overlap: keep last overlap_chars of previous chunk
                current = current[-overlap_chars:].strip() + ' ' + sent

        if current.strip():
            chunks.append(current.strip())

        return [c for c in chunks if len(c) > 50]  # Drop tiny fragments

    def add(
        self,
        text: str,
        tags: list = None,
        session_key: str = 'main',
        source: str = 'session',
        metadata: dict = None,
        chunk: bool = True,
        overwrite: bool = False,
    ) -> list:
        """
        Add a memory entry. Returns list of chunk IDs added.

        If chunk=True, long text is split into overlapping semantic chunks
        so individual chunks can be retrieved precisely.

        If overwrite=False and content_hash already exists, skips silently.
        """
        if self.table is None:
            self.init()

        tags = tags or []
        content_hash = self._content_hash(text)
        timestamp = datetime.now().isoformat()

        # Check dedup
        if not overwrite:
            existing = self.table.search().where(f"content_hash = '{content_hash}'").to_list()
            if existing:
                return []

        if chunk and len(text) > 2000:
            chunks = self._chunk_text(text)
        else:
            chunks = [text]

        ids = []
        for chunk_text in chunks:
            chunk_hash = self._content_hash(chunk_text)
            chunk_id = str(uuid.uuid4())

            # Embed (with simple cache)
            if chunk_hash not in self._embedding_cache:
                self._embedding_cache[chunk_hash] = get_embedding(chunk_text)
            embedding = self._embedding_cache[chunk_hash]

            row = {
                'id': chunk_id,
                'text': chunk_text,
                'embedding': embedding,
                'content_hash': chunk_hash,
                'timestamp': timestamp,
                'source': source,
                'session_key': session_key,
                'tags': tags,
                'metadata': json.dumps(metadata or {}),
            }
            self.table.add([row])
            ids.append(chunk_id)

        return ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str = None,
        session_filter: str = None,
        tags_filter: list = None,
    ) -> list:
        """
        Semantic search across all memory entries.

        Returns top_k matches with text, source, timestamp, session, tags, and score.
        """
        if self.table is None:
            self.init()

        query_emb = get_embedding(query)

        # Build where clause filters
        where_clauses = []
        if source_filter:
            where_clauses.append(f"source = '{source_filter}'")
        if session_filter:
            where_clauses.append(f"session_key = '{session_filter}'")

        search = self.table.search(query_emb, vector_column_name='embedding')
        if where_clauses:
            search = search.where(' AND '.join(where_clauses))

        results = search.limit(top_k).to_list()

        # Filter by tags if specified
        if tags_filter:
            filtered = []
            for r in results:
                entry_tags = json.loads(r.get('metadata', '{}')).get('tags', r.get('tags', []))
                if any(t in entry_tags for t in tags_filter):
                    filtered.append(r)
            results = filtered

        return [
            {
                'id': r['id'],
                'text': r['text'],
                'source': r['source'],
                'session_key': r['session_key'],
                'tags': r.get('tags', []),
                'timestamp': r['timestamp'],
                'score': r.get('_score', 0),
                'content_hash': r.get('content_hash', ''),
            }
            for r in results
        ]

    def search_text(self, query: str, top_k: int = 5) -> list:
        """
        Plain text search (faster, no embedding). Uses BM25-like matching.
        Good for exact keyword searches.
        """
        if self.table is None:
            self.init()

        results = (
            self.table.search()
            .where('text LIKE $query', query=f'%{query}%')
            .limit(top_k)
            .to_list()
        )
        return results

    def get_recent(self, session_key: str = None, limit: int = 20) -> list:
        """Get most recent memory entries."""
        if self.table is None:
            self.init()

        q = self.table.search().order_by('timestamp', descending=True).limit(limit)
        if session_key:
            q = q.where(f"session_key = '{session_key}'")

        return q.to_list()

    def delete(self, content_hash: str = None, entry_id: str = None):
        """Delete by content_hash or entry ID."""
        if self.table is None:
            self.init()

        if content_hash:
            # Find and delete all chunks with this hash
            self.table.delete(f"content_hash = '{content_hash}'")
        elif entry_id:
            self.table.delete(f"id = '{entry_id}'")

    def count(self) -> int:
        """Total entry count."""
        if self.table is None:
            self.init()
        return len(self.table.to_list())

    def stats(self) -> dict:
        """Return memory store statistics."""
        if self.table is None:
            self.init()

        all_entries = self.table.to_list()
        sources = {}
        for e in all_entries:
            s = e.get('source', 'unknown')
            sources[s] = sources.get(s, 0) + 1

        return {
            'total_entries': len(all_entries),
            'by_source': sources,
            'db_path': str(self.db_path),
            'embedding_model': self.embedding_model,
        }

    # ── Sync from existing files ───────────────────────────────────────────────

    def sync_from_memory_files(self, dry_run: bool = False) -> dict:
        """
        One-time historical import of MEMORY.md and all daily notes into vector store.

        Call this once to backfill historical context.
        Skips entries already in the store (by content_hash).
        """
        if self.table is None:
            self.init()

        stats = {'added': 0, 'skipped': 0, 'errors': 0}

        # ── MEMORY.md ──
        memory_path = self.workspace / 'MEMORY.md'
        if memory_path.exists():
            content = memory_path.read_text()
            # Parse § delimited entries
            entries = [e.strip() for e in content.split('§') if e.strip()]
            for entry in entries:
                h = self._content_hash(entry)
                existing = self.table.search().where(f"content_hash = '{h}'").to_list()
                if existing:
                    stats['skipped'] += 1
                    continue
                try:
                    if not dry_run:
                        self.add(entry, tags=['memory', 'long-term'], source='memory', chunk=True)
                    stats['added'] += 1
                except Exception as e:
                    stats['errors'] += 1
                    print(f"Error importing MEMORY entry: {e}")

        # ── Daily notes ──
        memory_dir = self.workspace / 'memory'
        if memory_dir.exists():
            for day_file in sorted(memory_dir.glob('YYYY-MM-DD.md')):
                if day_file.name == 'YYYY-MM-DD.md':
                    continue
                date_marker = day_file.stem  # e.g. '2026-03-31'
                content = day_file.read_text()
                # Split by date headers or ## markers
                sections = re.split(r'(?=^##?\s)', content, flags=re.MULTILINE)
                for section in sections:
                    section = section.strip()
                    if len(section) < 30:
                        continue
                    h = self._content_hash(section)
                    existing = self.table.search().where(f"content_hash = '{h}'").to_list()
                    if existing:
                        stats['skipped'] += 1
                        continue
                    try:
                        if not dry_run:
                            self.add(
                                section,
                                tags=['daily', date_marker],
                                source='daily',
                                session_key=date_marker,
                                chunk=True,
                            )
                        stats['added'] += 1
                    except Exception as e:
                        stats['errors'] += 1
                        print(f"Error importing {day_file.name} section: {e}")

        # ── Briefings ──
        briefings_dir = memory_dir / 'briefings'
        if briefings_dir.exists():
            for bf in briefings_dir.glob('*.md'):
                content = bf.read_text()
                h = self._content_hash(content)
                existing = self.table.search().where(f"content_hash = '{h}'").to_list()
                if existing:
                    stats['skipped'] += 1
                    continue
                try:
                    if not dry_run:
                        self.add(
                            content,
                            tags=['briefing', bf.stem],
                            source='briefing',
                            chunk=True,
                        )
                    stats['added'] += 1
                except Exception as e:
                    stats['errors'] += 1

        return stats

    # ── Session summary (call at end of session) ───────────────────────────────

    def save_session_summary(self, summary_text: str, session_key: str, tags: list = None):
        """
        Save a session-level summary at the end of each session.
        Call this from a session-end hook or as part of shutdown.
        """
        self.add(
            summary_text,
            tags=tags or ['session-summary'],
            session_key=session_key,
            source='session-summary',
            chunk=False,
        )


# ── CLI for testing ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Cross-session vector memory')
    parser.add_argument('--init', action='store_true', help='Init/reset the database')
    parser.add_argument('--sync', action='store_true', help='Sync from existing memory files')
    parser.add_argument('--dry-run', action='store_true', help='Dry run for sync')
    parser.add_argument('--search', type=str, help='Search query')
    parser.add_argument('--stats', action='store_true', help='Show stats')
    parser.add_argument('--add', type=str, help='Add a memory entry')
    parser.add_argument('--workspace', default='~/.openclaw/workspace', help='Workspace path')
    args = parser.parse_args()

    vm = VectorMemory(args.workspace)

    if args.init:
        vm.init()
        print(f"Initialized at {vm.db_path}")

    if args.stats:
        print(json.dumps(vm.stats(), indent=2))

    if args.sync:
        print("Syncing from memory files...")
        result = vm.sync_from_memory_files(dry_run=args.dry_run)
        print(f"Added: {result['added']}, Skipped: {result['skipped']}, Errors: {result['errors']}")

    if args.search:
        results = vm.search(args.search, top_k=5)
        for r in results:
            print(f"\n[{r['source']} | {r['session_key']} | score:{r['score']:.3f}]")
            print(r['text'][:300])

    if args.add:
        ids = vm.add(args.add, source='cli', session_key='cli-test')
        print(f"Added {len(ids)} chunk(s)")
