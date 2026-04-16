"""
ZettelForge Web UI — FastAPI backend + minimal HTML frontend.

A search-and-recall interface for ZettelForge's CTI memory system.

Usage:
    python web/app.py                    # Start on port 8088
    python web/app.py --port 9000        # Custom port
    uvicorn web.app:app --reload         # Dev mode

Endpoints:
    GET  /                    → Search UI (HTML)
    POST /api/recall          → Blended recall (vector + graph)
    POST /api/remember        → Store a note
    POST /api/synthesize      → RAG synthesis
    GET  /api/stats           → Memory system stats
    POST /api/sync            → Trigger OpenCTI sync
"""

# isort: skip_file

import logging
import os
import secrets
import sys
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# Ensure zettelforge is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

os.environ.setdefault("ZETTELFORGE_BACKEND", "sqlite")

from zettelforge import MemoryManager, __version__  # noqa: E402
from zettelforge.edition import edition_name, is_enterprise  # noqa: E402
from web.auth import get_mm_for_request, register_auth_routes  # noqa: E402

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ZettelForge",
    description=edition_name(),
    version=__version__,
)

# Register OAuth/JWT auth routes (Enterprise: full OAuth, Community: pass-through)
register_auth_routes(app)

# Default memory manager (for unauthenticated/single-tenant mode)
mm = MemoryManager()

MAX_QUERY_CHARS = int(os.environ.get("ZETTELFORGE_WEB_MAX_QUERY_CHARS", "1000"))
MAX_CONTENT_CHARS = int(os.environ.get("ZETTELFORGE_WEB_MAX_CONTENT_CHARS", "50000"))
MAX_K = int(os.environ.get("ZETTELFORGE_WEB_MAX_K", "50"))
MAX_SYNC_LIMIT = int(os.environ.get("ZETTELFORGE_WEB_MAX_SYNC_LIMIT", "200"))
API_KEY = os.environ.get("ZETTELFORGE_WEB_API_KEY", "")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("ZETTELFORGE_WEB_RATE_LIMIT_PER_MINUTE", "60"))
WRITE_CONCURRENCY = int(os.environ.get("ZETTELFORGE_WEB_WRITE_CONCURRENCY", "2"))
SYNTHESIS_FORMATS = {
    "direct_answer",
    "synthesized_brief",
    "timeline_analysis",
    "relationship_map",
}

_rate_lock = threading.Lock()
_rate_windows = defaultdict(deque)
_write_slots = threading.BoundedSemaphore(max(1, WRITE_CONCURRENCY))


# ── Pydantic models ──────────────────────────────────────────────────────────


class RecallRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    k: int = Field(default=10, ge=1, le=MAX_K)
    domain: Optional[str] = Field(default=None, max_length=100)


class RememberRequest(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)
    domain: str = Field(default="cti", min_length=1, max_length=100)
    source_type: str = Field(default="manual", min_length=1, max_length=100)
    source_ref: str = Field(default="", max_length=500)
    evolve: bool = True


class SynthesizeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    format: str = Field(default="direct_answer", max_length=50)
    k: int = Field(default=10, ge=1, le=MAX_K)


class SyncRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=MAX_SYNC_LIMIT)
    entity_types: Optional[List[str]] = None


# ── API endpoints ────────────────────────────────────────────────────────────


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _is_loopback(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}


def _check_rate_limit(key: str) -> None:
    now = time.monotonic()
    window_start = now - 60
    with _rate_lock:
        hits = _rate_windows[key]
        while hits and hits[0] < window_start:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
        hits.append(now)


async def require_api_guard(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> None:
    client_ip = _client_ip(request)
    supplied_key = x_api_key
    if not supplied_key and authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            supplied_key = value

    if API_KEY:
        if not supplied_key or not secrets.compare_digest(supplied_key, API_KEY):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid API key required",
            )
    elif not _is_loopback(client_ip):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Set ZETTELFORGE_WEB_API_KEY before exposing the web API",
        )

    _check_rate_limit(supplied_key or client_ip)


@app.post("/api/recall", dependencies=[Depends(require_api_guard)])
async def recall(request: Request, req: RecallRequest):
    tenant_mm = get_mm_for_request(request)
    start = time.perf_counter()
    results = tenant_mm.recall(req.query, domain=req.domain, k=req.k, exclude_superseded=False)
    latency = time.perf_counter() - start

    return {
        "query": req.query,
        "results": [
            {
                "id": n.id,
                "content": n.content.raw[:500],
                "domain": n.metadata.domain,
                "tier": n.metadata.tier,
                "confidence": n.metadata.confidence,
                "created_at": n.created_at,
                "entities": n.semantic.entities[:10],
                "context": n.semantic.context,
            }
            for n in results
        ],
        "count": len(results),
        "latency_ms": round(latency * 1000),
    }


@app.post("/api/remember", dependencies=[Depends(require_api_guard)])
async def remember(request: Request, req: RememberRequest):
    tenant_mm = get_mm_for_request(request)
    start = time.perf_counter()
    if not _write_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Write capacity exhausted; retry shortly",
        )
    try:
        note, status_text = tenant_mm.remember(
            content=req.content,
            source_type=req.source_type,
            source_ref=req.source_ref,
            domain=req.domain,
            evolve=req.evolve,
        )
    finally:
        _write_slots.release()
    latency = time.perf_counter() - start

    return {
        "note_id": note.id,
        "status": status_text,
        "entities": note.semantic.entities[:10],
        "latency_ms": round(latency * 1000),
    }


@app.post("/api/synthesize", dependencies=[Depends(require_api_guard)])
async def synthesize(request: Request, req: SynthesizeRequest):
    if req.format not in SYNTHESIS_FORMATS:
        raise HTTPException(status_code=400, detail="Unsupported synthesis format")
    tenant_mm = get_mm_for_request(request)
    start = time.perf_counter()
    if not _write_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Synthesis capacity exhausted; retry shortly",
        )
    try:
        result = tenant_mm.synthesize(req.query, format=req.format, k=req.k)
    finally:
        _write_slots.release()
    latency = time.perf_counter() - start

    return {
        "query": req.query,
        "format": req.format,
        "synthesis": result.get("synthesis", {}),
        "sources_count": result.get("metadata", {}).get("sources_count", 0),
        "latency_ms": round(latency * 1000),
    }


@app.get("/api/stats", dependencies=[Depends(require_api_guard)])
async def stats(request: Request):
    tenant_mm = get_mm_for_request(request)
    s = tenant_mm.get_stats()
    return {
        "version": __version__,
        "edition": "enterprise" if is_enterprise() else "community",
        "edition_name": edition_name(),
        "total_notes": s.get("total_notes", 0),
        "notes_created": s.get("notes_created", 0),
        "retrievals": s.get("retrievals", 0),
        "entity_index": s.get("entity_index", {}),
    }


@app.get("/api/edition", dependencies=[Depends(require_api_guard)])
async def edition_info():
    """Return current edition and available features."""
    features = {
        # Core — full-featured agentic memory system
        "vector_search": True,
        "blended_retrieval": True,
        "cross_encoder_reranking": True,
        "two_phase_extraction": True,
        "intent_adaptive_routing": True,
        "causal_triple_extraction": True,
        "entity_extraction_llm": True,
        "knowledge_graph_jsonl": True,
        "direct_answer_synthesis": True,
        "mcp_server": True,
        # Ungated features
        "typedb_stix_ontology": is_enterprise(),
        "temporal_graph_queries": True,
        "graph_traversal_multihop": True,
        "advanced_synthesis_formats": True,
        "report_ingestion": True,
        "alias_resolution_typedb": is_enterprise(),
        "opencti_integration": is_enterprise(),
        "sigma_generation": is_enterprise(),
        "context_injection": is_enterprise(),
        "multi_tenant_auth": is_enterprise(),
    }
    return {
        "edition": "enterprise" if is_enterprise() else "community",
        "edition_name": edition_name(),
        "version": __version__,
        "features": features,
    }


@app.post("/api/sync", dependencies=[Depends(require_api_guard)])
async def sync(request: Request, req: SyncRequest):
    if not is_enterprise():
        return JSONResponse(
            status_code=501,
            content={
                "error": "OpenCTI sync requires the zettelforge-enterprise package.",
            },
        )
    try:
        from zettelforge_enterprise.opencti_sync import sync_opencti

        tenant_mm = get_mm_for_request(request)
        result = sync_opencti(
            tenant_mm,
            limit=req.limit,
            entity_types=req.entity_types,
            use_extraction=False,
        )
        return result
    except Exception:
        logger.exception("OpenCTI sync failed")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


# ── HTML Frontend ────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZettelForge</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0a0e17; color: #c9d1d9; min-height: 100vh; }
        .header { background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px; display: flex; align-items: center; gap: 16px; }
        .header h1 { font-size: 20px; color: #58a6ff; font-weight: 600; }
        .header .version { color: #8b949e; font-size: 13px; }
        .header .stats { margin-left: auto; color: #8b949e; font-size: 13px; }
        .container { max-width: 960px; margin: 0 auto; padding: 24px; }
        .search-box { display: flex; gap: 8px; margin-bottom: 24px; }
        .search-box input { flex: 1; padding: 12px 16px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 15px; outline: none; }
        .search-box input:focus { border-color: #58a6ff; box-shadow: 0 0 0 3px rgba(88,166,255,0.1); }
        .search-box button { padding: 12px 24px; background: #238636; border: none; border-radius: 6px; color: #fff; font-size: 15px; cursor: pointer; font-weight: 500; }
        .search-box button:hover { background: #2ea043; }
        .tabs { display: flex; gap: 4px; margin-bottom: 16px; }
        .tabs button { padding: 8px 16px; background: transparent; border: 1px solid #30363d; border-radius: 6px; color: #8b949e; cursor: pointer; font-size: 13px; }
        .tabs button.active { background: #21262d; color: #c9d1d9; border-color: #58a6ff; }
        .meta { color: #8b949e; font-size: 13px; margin-bottom: 16px; }
        .results { display: flex; flex-direction: column; gap: 12px; }
        .result { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
        .result:hover { border-color: #58a6ff; }
        .result .title { color: #58a6ff; font-size: 13px; margin-bottom: 8px; font-family: monospace; }
        .result .content { color: #c9d1d9; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
        .result .footer { display: flex; gap: 12px; margin-top: 8px; color: #8b949e; font-size: 12px; }
        .result .tag { display: inline-block; padding: 2px 8px; background: #21262d; border-radius: 12px; font-size: 11px; color: #8b949e; }
        .result .tag.tier-a { background: #1a472a; color: #3fb950; }
        .result .tag.tier-b { background: #2a1a47; color: #a371f7; }
        .synthesis { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
        .synthesis h3 { color: #58a6ff; margin-bottom: 12px; }
        .synthesis .answer { font-size: 15px; line-height: 1.7; }
        .input-section { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 24px; }
        .input-section textarea { width: 100%; min-height: 100px; padding: 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 14px; resize: vertical; font-family: inherit; }
        .input-section .actions { display: flex; gap: 8px; margin-top: 8px; }
        .input-section button { padding: 8px 16px; background: #238636; border: none; border-radius: 6px; color: #fff; cursor: pointer; font-size: 13px; }
        .empty { text-align: center; padding: 48px; color: #484f58; }
        .empty h2 { font-size: 18px; margin-bottom: 8px; color: #8b949e; }
        .spinner { display: none; text-align: center; padding: 24px; color: #8b949e; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ZettelForge</h1>
        <span class="version" id="version"></span>
        <span class="stats" id="stats"></span>
        <span id="user-info" style="margin-left:auto;display:flex;align-items:center;gap:8px;"></span>
    </div>
    <div class="container">
        <div class="search-box">
            <input type="text" id="query" placeholder="Search threat intelligence... (e.g., What tools does APT28 use?)" autofocus>
            <button onclick="doSearch()">Search</button>
        </div>
        <div class="tabs">
            <button class="active" onclick="setMode('recall')">Recall</button>
            <button onclick="setMode('synthesize')">Synthesize</button>
            <button onclick="setMode('remember')">Remember</button>
            <button onclick="setMode('sync')">OpenCTI Sync</button>
        </div>
        <div id="remember-section" class="input-section" style="display:none;">
            <textarea id="remember-content" placeholder="Paste threat intelligence to store..."></textarea>
            <div class="actions">
                <button onclick="doRemember()">Store in Memory</button>
            </div>
        </div>
        <div id="sync-section" class="input-section" style="display:none;">
            <p style="color:#8b949e;margin-bottom:12px;">Pull latest from OpenCTI into ZettelForge memory.</p>
            <div class="actions">
                <button onclick="doSync()">Sync Now (20 per type)</button>
            </div>
        </div>
        <div class="meta" id="meta"></div>
        <div class="spinner" id="spinner">Searching...</div>
        <div id="synthesis"></div>
        <div class="results" id="results">
            <div class="empty">
                <h2>ZettelForge CTI Memory</h2>
                <p>Search across threat actors, CVEs, tools, campaigns, and reports.</p>
            </div>
        </div>
    </div>
    <script>
        let mode = 'recall';
        function apiHeaders(extra = {}) {
            const headers = {...extra};
            const key = localStorage.getItem('zettelforgeApiKey');
            if (key) headers['X-API-Key'] = key;
            return headers;
        }
        function setMode(m) {
            mode = m;
            document.querySelectorAll('.tabs button').forEach((b,i) => b.classList.toggle('active', ['recall','synthesize','remember','sync'][i] === m));
            document.getElementById('remember-section').style.display = m === 'remember' ? 'block' : 'none';
            document.getElementById('sync-section').style.display = m === 'sync' ? 'block' : 'none';
        }
        async function doSearch() {
            const q = document.getElementById('query').value.trim();
            if (!q) return;
            document.getElementById('spinner').style.display = 'block';
            document.getElementById('results').innerHTML = '';
            document.getElementById('synthesis').innerHTML = '';
            document.getElementById('meta').textContent = '';
            try {
                if (mode === 'synthesize') {
                    const res = await fetch('/api/synthesize', {method:'POST', headers:apiHeaders({'Content-Type':'application/json'}), body:JSON.stringify({query:q, format:'synthesized_brief'})});
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || data.error || 'Synthesis failed');
                    const syn = data.synthesis || {};
                    document.getElementById('synthesis').innerHTML = `<div class="synthesis"><h3>Synthesis (${escHtml(data.latency_ms)}ms)</h3><div class="answer">${escHtml(syn.summary || syn.answer || JSON.stringify(syn))}</div></div>`;
                } else {
                    const res = await fetch('/api/recall', {method:'POST', headers:apiHeaders({'Content-Type':'application/json'}), body:JSON.stringify({query:q, k:10})});
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || data.error || 'Recall failed');
                    document.getElementById('meta').textContent = `${data.count} results in ${data.latency_ms}ms`;
                    if (data.results.length === 0) {
                        document.getElementById('results').innerHTML = '<div class="empty"><h2>No results</h2></div>';
                    } else {
                        document.getElementById('results').innerHTML = data.results.map(r => `
                            <div class="result">
                                <div class="title">${escHtml(r.id)} <span class="tag tier-${cssToken(r.tier)}">${escHtml(r.tier)}</span> <span class="tag">${escHtml(r.domain)}</span></div>
                                <div class="content">${escHtml(r.content)}</div>
                                <div class="footer">
                                    <span>${escHtml(r.created_at?.slice(0,10) || '')}</span>
                                    <span>confidence: ${escHtml(r.confidence)}</span>
                                    ${r.entities.map(e => `<span class="tag">${escHtml(e)}</span>`).join('')}
                                </div>
                            </div>`).join('');
                    }
                }
            } catch(e) { document.getElementById('results').innerHTML = `<div class="empty"><h2>Error: ${escHtml(e.message)}</h2></div>`; }
            document.getElementById('spinner').style.display = 'none';
        }
        async function doRemember() {
            const content = document.getElementById('remember-content').value.trim();
            if (!content) return;
            const res = await fetch('/api/remember', {method:'POST', headers:apiHeaders({'Content-Type':'application/json'}), body:JSON.stringify({content, domain:'cti'})});
            const data = await res.json();
            if (!res.ok) {
                document.getElementById('meta').textContent = data.detail || data.error || 'Store failed';
                return;
            }
            document.getElementById('meta').textContent = `Stored: ${data.note_id} (${data.status}, ${data.latency_ms}ms, entities: ${data.entities.join(', ')})`;
            document.getElementById('remember-content').value = '';
        }
        async function doSync() {
            document.getElementById('meta').textContent = 'Syncing from OpenCTI...';
            try {
                const res = await fetch('/api/sync', {method:'POST', headers:apiHeaders({'Content-Type':'application/json'}), body:JSON.stringify({limit:20})});
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || data.error || 'Sync failed');
                document.getElementById('meta').textContent = `Synced ${data.synced || 0} objects, ${data.skipped || 0} skipped, ${data.errors || 0} errors (${data.duration_s || 0}s)`;
            } catch(e) { document.getElementById('meta').textContent = `Sync error: ${e.message}`; }
        }
        function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
        function cssToken(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9_-]/g, ''); }
        document.getElementById('query').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
        // Load stats + edition
        fetch('/api/stats', {headers: apiHeaders()}).then(r=>r.json()).then(d => {
            if (d.detail || d.error) throw new Error(d.detail || d.error);
            const edBadge = d.edition === 'enterprise' ? 'Enterprise' : 'Community';
            document.getElementById('version').textContent = `v${d.version} (${edBadge})`;
            document.getElementById('stats').textContent = `${d.total_notes} notes | ${d.retrievals} recalls`;
            // Hide enterprise-only tabs in Community
            if (d.edition !== 'enterprise') {
                document.querySelectorAll('.tabs button').forEach(b => {
                    if (b.textContent === 'OpenCTI Sync') b.style.display = 'none';
                });
            }
        }).catch(e => { document.getElementById('stats').textContent = e.message; });
        // Load auth state
        fetch('/auth/me').then(r=>r.json()).then(d => {
            const el = document.getElementById('user-info');
            if (d.authenticated) {
                el.innerHTML = `<img src="${escHtml(d.picture||'')}" style="width:24px;height:24px;border-radius:50%;" onerror="this.style.display='none'"> <span style="color:#c9d1d9;font-size:13px;">${escHtml(d.name)}</span> <a href="/auth/logout" style="color:#8b949e;font-size:12px;text-decoration:none;">logout</a>`;
            } else {
                fetch('/auth/providers').then(r=>r.json()).then(p => {
                    if (p.providers.length > 0) {
                        el.innerHTML = p.providers.map(pr => `<a href="/auth/login/${encodeURIComponent(pr)}" style="padding:4px 12px;background:#21262d;border-radius:4px;color:#58a6ff;font-size:12px;text-decoration:none;">Login with ${escHtml(pr)}</a>`).join(' ');
                    }
                });
            }
        });
    </script>
</body>
</html>"""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ZettelForge Web UI")
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.host in {"0.0.0.0", "::"} and not API_KEY:
        parser.error("Set ZETTELFORGE_WEB_API_KEY before binding the web app to all interfaces")

    import uvicorn

    print(f"ZettelForge v{__version__} — http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
