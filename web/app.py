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


# ── HTML Frontend (SPA) ──────────────────────────────────────────────────────
# RFC-015: ZettelForge Web Management Interface served from web/ui/


@app.get("/", response_class=HTMLResponse)
async def index():
    ui_dir = Path(__file__).parent / "ui"
    index_path = ui_dir / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return HTMLResponse(
        content="<html><body><h1>ZettelForge</h1><p>Web UI not found. Run from the project root.</p></body></html>",
        status_code=200,
    )


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
