"""ZettelForge Web UI — FastAPI backend + SPA frontend (RFC-015).

A search-and-recall interface for ZettelForge's CTI memory system.

Usage:
    python web/app.py                    # Start on port 8088
    python web/app.py --port 9000        # Custom port
    uvicorn web.app:app --reload         # Dev mode

Endpoints (existing):
    GET  /                    -> Search UI (SPA HTML)
    POST /api/recall          -> Blended recall (vector + graph)
    POST /api/remember        -> Store a note
    POST /api/synthesize      -> RAG synthesis
    GET  /api/stats           -> Memory system stats
    POST /api/sync            -> Trigger OpenCTI sync

Endpoints (RFC-015, new):
    GET  /api/health          -> System health
    GET  /api/config          -> Current config (secrets redacted)
    PUT  /api/config          -> Apply config changes
    GET  /api/graph/nodes     -> KG entity nodes
    GET  /api/graph/edges     -> KG relationship edges
    GET  /api/entities        -> Paginated entity index
    GET  /api/history         -> Recent activity
    POST /api/ingest          -> Bulk ingestion
    GET  /api/telemetry       -> Aggregated telemetry summary
    GET  /api/storage         -> Storage stats
    GET  /api/logs            -> Log file tailing
    GET  /api/logs/stream     -> SSE log streaming
    GET  /api/telemetry/stream -> SSE telemetry streaming
"""

# isort: skip_file

import asyncio
import json
import logging
import os
import secrets
import sys
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Ensure zettelforge is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

os.environ.setdefault("ZETTELFORGE_BACKEND", "sqlite")

from zettelforge import MemoryManager, __version__
from zettelforge.config import get_config
from zettelforge.edition import edition_name, is_enterprise
from web.auth import get_mm_for_request, register_auth_routes

logger = logging.getLogger(__name__)

_start_time = time.monotonic()

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

# ── Helper functions ─────────────────────────────────────────────────────────


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
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
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


def _get_memory_stats() -> dict:
    """Get stats from the default MemoryManager."""
    try:
        return mm.get_stats()
    except Exception:
        return {"total_notes": 0, "notes_created": 0, "retrievals": 0, "entity_index": {}}


def _get_memory_mb() -> float | None:
    """Get current memory usage in MB. Returns None if psutil not available."""
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return None


def _get_data_dir_size_mb(data_dir: str = "~/.amem") -> float | None:
    """Get the size of the data directory in MB."""
    try:
        path = Path(os.path.expanduser(data_dir))
        if not path.exists():
            return None
        total_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return round(total_bytes / (1024 * 1024), 1)
    except Exception:
        return None


# ── Pydantic models (existing) ───────────────────────────────────────────────


class RecallRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    k: int = Field(default=10, ge=1, le=MAX_K)
    domain: str | None = Field(default=None, max_length=100)


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
    entity_types: List[str] | None = None


# ── Pydantic models (RFC-015, new) ───────────────────────────────────────────


class IngestItem(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)
    source_type: str = Field(default="manual")
    source_ref: str = Field(default="")
    domain: str = Field(default="cti")
    evolve: bool = True


class IngestRequest(BaseModel):
    items: list[IngestItem] = Field(default_factory=list, max_length=100)


class ConfigUpdateRequest(BaseModel):
    # Accept arbitrary nested dict for config updates
    pass


# ── Existing API endpoints ───────────────────────────────────────────────────


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


# ── RFC-015: New API Endpoints ───────────────────────────────────────────────


def _redact_secrets(obj: Any, depth: int = 0) -> Any:
    """Recursively redact sensitive config fields."""
    _SENSITIVE_KEYS = {"api_key", "password", "token", "secret", "license_key", "credentials"}
    if depth > 10:
        return obj
    if isinstance(obj, dict):
        return {
            k: ("***" if k.lower() in _SENSITIVE_KEYS and isinstance(v, str) and v else _redact_secrets(v, depth + 1))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_secrets(item, depth + 1) for item in obj]
    if hasattr(obj, "__dict__"):
        return _redact_secrets(obj.__dict__, depth)
    return obj


_RESTART_REQUIRED_FIELDS = {
    "backend", "storage.data_dir", "embedding.provider",
    "llm.provider", "logging.log_file", "logging.level",
}

# ── 1. Health ────────────────────────────────────────────────────────────────


@app.get("/api/health", dependencies=[Depends(require_api_guard)])
async def health(request: Request):
    """System health information."""
    try:
        cfg = get_config()
        s = _get_memory_stats()

        enrichment_depth = 0
        try:
            enrichment_depth = mm._enrichment_queue.qsize()
        except Exception:
            pass

        return {
            "version": __version__,
            "edition": "enterprise" if is_enterprise() else "community",
            "storage_backend": os.environ.get("ZETTELFORGE_BACKEND", "sqlite"),
            "embedding_provider": cfg.embedding.provider,
            "embedding_model": cfg.embedding.model,
            "embedding_dimensions": cfg.embedding.dimensions,
            "llm_provider": cfg.llm.provider,
            "llm_model": cfg.llm.model,
            "llm_local_backend": cfg.llm.local_backend,
            "enrichment_queue_depth": enrichment_depth,
            "governance_enabled": cfg.governance.enabled,
            "pii_enabled": cfg.governance.pii.enabled,
            "uptime_seconds": round(time.monotonic() - _start_time, 1),
            "data_dir": cfg.storage.data_dir,
            "memory_usage_mb": _get_memory_mb(),
            "data_size_mb": _get_data_dir_size_mb(cfg.storage.data_dir),
            "total_notes": s.get("total_notes", 0),
            "retrievals": s.get("retrievals", 0),
        }
    except Exception as e:
        logger.exception("Health endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 2. Config GET ────────────────────────────────────────────────────────────


@app.get("/api/config", dependencies=[Depends(require_api_guard)])
async def get_config_endpoint():
    """Return the current configuration with secrets redacted."""
    try:
        cfg = get_config()
        config_dict = {}
        for key in dir(cfg):
            if key.startswith("_"):
                continue
            val = getattr(cfg, key)
            if hasattr(val, "__dataclass_fields__"):
                config_dict[key] = _redact_secrets(
                    {f: getattr(val, f) for f in dir(val) if not f.startswith("_")}
                )
            else:
                config_dict[key] = val
        return config_dict
    except Exception as e:
        logger.exception("Config endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 3. Config PUT ────────────────────────────────────────────────────────────


@app.put("/api/config", dependencies=[Depends(require_api_guard)])
async def put_config_endpoint(data: dict):
    """Apply configuration changes in-memory."""
    try:

        cfg = get_config()
        applied = []
        pending_restart = []

        def _find_changes(prefix: str, updates: dict, target: Any):
            for k, v in updates.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict) and hasattr(target, k):
                    sub = getattr(target, k)
                    if hasattr(sub, "__dataclass_fields__"):
                        _find_changes(full_key, v, sub)
                        continue
                if hasattr(target, k):
                    setattr(target, k, v)
                    applied.append(full_key)
                    if full_key in _RESTART_REQUIRED_FIELDS or k in _RESTART_REQUIRED_FIELDS:
                        pending_restart.append(full_key)

        _find_changes("", data, cfg)

        return {
            "applied": applied,
            "pending_restart": pending_restart,
            "message": "Configuration updated. Some changes require a restart."
            if pending_restart
            else "Configuration updated.",
        }
    except Exception as e:
        logger.exception("Config put endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 4. Graph Nodes ───────────────────────────────────────────────────────────


@app.get("/api/graph/nodes", dependencies=[Depends(require_api_guard)])
async def graph_nodes(request: Request):
    """Return all knowledge graph entity nodes."""
    try:
        tenant_mm = get_mm_for_request(request)
        kg = getattr(tenant_mm, "_knowledge_graph", None)
        nodes = []
        if kg is not None:
            raw_nodes = getattr(kg, "_nodes", {}) or {}
            for nid, node in raw_nodes.items():
                nodes.append({
                    "id": nid,
                    "label": node.get("name", nid),
                    "type": node.get("entity_type", "unknown"),
                    "tier": node.get("tier", "C"),
                    "aliases": node.get("aliases", []),
                    "confidence": node.get("confidence", 0.5),
                    "created_at": node.get("created_at"),
                })
        return {"nodes": nodes, "count": len(nodes)}
    except Exception as e:
        logger.exception("Graph nodes endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 5. Graph Edges ───────────────────────────────────────────────────────────


@app.get("/api/graph/edges", dependencies=[Depends(require_api_guard)])
async def graph_edges(request: Request):
    """Return all knowledge graph relationship edges."""
    try:
        tenant_mm = get_mm_for_request(request)
        kg = getattr(tenant_mm, "_knowledge_graph", None)
        edges = []
        if kg is not None:
            raw_edges = getattr(kg, "_edges", {}) or {}
            for eid, edge in raw_edges.items():
                edges.append({
                    "id": eid,
                    "source": edge.get("source_id"),
                    "target": edge.get("target_id"),
                    "relationship": edge.get("relationship"),
                    "created_at": edge.get("created_at"),
                })
        return {"edges": edges, "count": len(edges)}
    except Exception as e:
        logger.exception("Graph edges endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 6. Entities ──────────────────────────────────────────────────────────────


@app.get("/api/entities", dependencies=[Depends(require_api_guard)])
async def entities(
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    entity_type: str | None = Query(default=None, alias="type"),
    tier: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    """Paginated entity index with filters."""
    try:
        tenant_mm = get_mm_for_request(request)
        kg = getattr(tenant_mm, "_knowledge_graph", None)

        all_entities = []
        if kg is not None:
            raw_nodes = getattr(kg, "_nodes", {}) or {}
            for nid, node in raw_nodes.items():
                all_entities.append({
                    "id": nid,
                    "name": node.get("name", nid),
                    "type": node.get("entity_type", "unknown"),
                    "tier": node.get("tier", "C"),
                    "confidence": node.get("confidence", 0.5),
                    "aliases": node.get("aliases", []),
                    "first_seen": node.get("created_at"),
                    "last_seen": node.get("updated_at"),
                    "connected_count": len(
                        getattr(kg, "_edges_from", {}).get(nid, [])
                    ),
                })

        # Apply filters
        if entity_type:
            all_entities = [e for e in all_entities if e["type"] == entity_type]
        if tier:
            all_entities = [e for e in all_entities if e["tier"] == tier]
        if q:
            q_lower = q.lower()
            all_entities = [
                e
                for e in all_entities
                if q_lower in e["name"].lower()
                or any(q_lower in a.lower() for a in e["aliases"])
            ]

        total = len(all_entities)
        page = all_entities[offset : offset + limit]

        return {"entities": page, "total": total, "offset": offset, "limit": limit}
    except Exception as e:
        logger.exception("Entities endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 7. History ───────────────────────────────────────────────────────────────


@app.get("/api/history", dependencies=[Depends(require_api_guard)])
async def history(
    limit: int = Query(default=100, ge=1, le=500),
    days: int = Query(default=5, ge=1, le=30),
):
    """Recent activity from telemetry JSONL files."""
    try:
        cfg = get_config()
        data_dir = Path(os.path.expanduser(cfg.storage.data_dir))
        telemetry_dir = data_dir / "telemetry"
        if not telemetry_dir.exists():
            return []

        entries = []
        cutoff = datetime.now() - timedelta(days=days)

        for telemetry_file in sorted(telemetry_dir.glob("telemetry_*.jsonl"), reverse=True):
            if len(entries) >= limit:
                break
            # Parse date from filename
            try:
                file_date_str = telemetry_file.stem.split("_")[1]
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    continue
            except (IndexError, ValueError):
                continue

            with open(telemetry_file) as f:
                for line in f:
                    if len(entries) >= limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue

        return entries
    except Exception as e:
        logger.exception("History endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 8. Ingest ────────────────────────────────────────────────────────────────


@app.post("/api/ingest", dependencies=[Depends(require_api_guard)])
async def ingest(request: Request, req: IngestRequest):
    """Bulk ingestion endpoint."""
    tenant_mm = get_mm_for_request(request)
    results = []

    for item in req.items:
        if not _write_slots.acquire(blocking=False):
            results.append({
                "status": "error",
                "error": "Write capacity exhausted; retry shortly",
                "success": False,
            })
            continue
        try:
            note, status_text = tenant_mm.remember(
                content=item.content,
                source_type=item.source_type,
                source_ref=item.source_ref,
                domain=item.domain,
                evolve=item.evolve,
            )
            results.append({
                "note_id": note.id,
                "status": status_text,
                "entities": note.semantic.entities[:10],
                "success": True,
            })
        except Exception as e:
            results.append({
                "status": "error",
                "error": str(e),
                "success": False,
            })
        finally:
            _write_slots.release()

    return {
        "total": len(results),
        "succeeded": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results,
    }


# ── 9. Telemetry ─────────────────────────────────────────────────────────────


@app.get("/api/telemetry", dependencies=[Depends(require_api_guard)])
async def telemetry():
    """Aggregated telemetry summary from today's data."""
    try:
        cfg = get_config()
        data_dir = Path(os.path.expanduser(cfg.storage.data_dir))
        telemetry_dir = data_dir / "telemetry"
        today_str = datetime.now().strftime("%Y-%m-%d")
        telemetry_file = telemetry_dir / f"telemetry_{today_str}.jsonl"

        if not telemetry_file.exists():
            return {
                "total_queries": 0,
                "recall_count": 0,
                "synthesis_count": 0,
                "avg_latency_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "top_intents": {},
            }

        latencies = []
        intents: dict[str, int] = {}
        recall_count = 0
        synthesis_count = 0

        with open(telemetry_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    event_type = event.get("event_type", "")
                    if event_type == "recall":
                        recall_count += 1
                    elif event_type == "synthesis":
                        synthesis_count += 1

                    duration = event.get("duration_ms")
                    if duration is not None:
                        latencies.append(duration)

                    intent = event.get("intent")
                    if intent:
                        intents[intent] = intents.get(intent, 0) + 1
                except (json.JSONDecodeError, KeyError):
                    continue

        total = len(latencies)
        avg_latency = round(sum(latencies) / total, 1) if total > 0 else None
        sorted_lat = sorted(latencies)
        p50 = sorted_lat[len(sorted_lat) // 2] if total > 0 else None
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if total > 0 else None

        # Sort intents by count descending
        sorted_intents = dict(sorted(intents.items(), key=lambda x: -x[1]))

        return {
            "total_queries": recall_count + synthesis_count,
            "recall_count": recall_count,
            "synthesis_count": synthesis_count,
            "avg_latency_ms": avg_latency,
            "p50_ms": p50,
            "p95_ms": p95,
            "top_intents": sorted_intents,
        }
    except Exception as e:
        logger.exception("Telemetry endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 10. Storage ─────────────────────────────────────────────────────────────


@app.get("/api/storage", dependencies=[Depends(require_api_guard)])
async def storage(request: Request):
    """Storage statistics."""
    try:
        tenant_mm = get_mm_for_request(request)
        s = tenant_mm.get_stats()
        kg = getattr(tenant_mm, "_knowledge_graph", None)

        graph_node_count = len(getattr(kg, "_nodes", {})) if kg else 0
        graph_edge_count = len(getattr(kg, "_edges", {})) if kg else 0

        return {
            "total_notes": s.get("total_notes", 0),
            "entity_count": len(s.get("entity_index", {})),
            "graph_node_count": graph_node_count,
            "graph_edge_count": graph_edge_count,
        }
    except Exception as e:
        logger.exception("Storage endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 11. Logs ─────────────────────────────────────────────────────────────────


def _parse_log_line(line: str, level_filter: str | None = None) -> dict | None:
    """Parse a structlog JSON line into a dict."""
    try:
        entry = json.loads(line)
        if level_filter and entry.get("level", "").upper() != level_filter.upper():
            return None
        return entry
    except (json.JSONDecodeError, KeyError):
        return None


@app.get("/api/logs", dependencies=[Depends(require_api_guard)])
async def logs(
    lines: int = Query(default=100, ge=1, le=1000),
    level: str | None = Query(default=None),
):
    """Tail the structlog file with optional level filter."""
    try:
        cfg = get_config()
        log_file = cfg.logging.log_file
        if not log_file:
            # Default log path
            data_dir = Path(os.path.expanduser(cfg.storage.data_dir))
            log_file = str(data_dir / "zettelforge.log")

        log_path = Path(os.path.expanduser(log_file))
        if not log_path.exists():
            return {"logs": [], "truncated": False}

        # Read last N lines
        with open(log_path) as f:
            all_lines = f.readlines()

        # Parse and filter
        parsed: list[dict] = []
        for line in reversed(all_lines):
            entry = _parse_log_line(line.strip(), level)
            if entry is not None:
                parsed.append(entry)
                if len(parsed) >= lines:
                    break

        parsed.reverse()
        return {"logs": parsed, "truncated": len(parsed) < len(all_lines)}
    except Exception as e:
        logger.exception("Logs endpoint failed")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── 12. Logs SSE Stream ─────────────────────────────────────────────────────


@app.get("/api/logs/stream", dependencies=[Depends(require_api_guard)])
async def log_stream():
    """SSE endpoint for live log streaming."""
    cfg = get_config()
    log_file = cfg.logging.log_file
    if not log_file:
        data_dir = Path(os.path.expanduser(cfg.storage.data_dir))
        log_file = str(data_dir / "zettelforge.log")
    log_path = Path(os.path.expanduser(log_file))

    async def event_generator():
        if not log_path.exists():
            yield f"data: {json.dumps({'event': 'log stream started', 'level': 'INFO'})}\n\n"
            return

        try:
            with open(log_path) as f:
                # Seek to end
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        line = line.strip()
                        if line:
                            try:
                                event = json.loads(line)
                                yield f"data: {json.dumps(event)}\n\n"
                            except json.JSONDecodeError:
                                yield f"data: {json.dumps({'message': line, 'level': 'RAW'})}\n\n"
                    else:
                        await asyncio.sleep(0.1)
        except Exception:
            yield f"data: {json.dumps({'event': 'Log stream ended', 'level': 'WARNING'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── 13. Telemetry SSE Stream ────────────────────────────────────────────────


@app.get("/api/telemetry/stream", dependencies=[Depends(require_api_guard)])
async def telemetry_stream():
    """SSE endpoint for live telemetry streaming."""
    cfg = get_config()
    data_dir = Path(os.path.expanduser(cfg.storage.data_dir))
    telemetry_dir = data_dir / "telemetry"
    today_str = datetime.now().strftime("%Y-%m-%d")
    telemetry_path = telemetry_dir / f"telemetry_{today_str}.jsonl"

    async def event_generator():
        if not telemetry_path.exists():
            yield f"data: {json.dumps({'event': 'telemetry stream started', 'level': 'INFO'})}\n\n"
            return

        try:
            with open(telemetry_path) as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        line = line.strip()
                        if line:
                            try:
                                event = json.loads(line)
                                yield f"data: {json.dumps(event)}\n\n"
                            except json.JSONDecodeError:
                                pass
                    else:
                        await asyncio.sleep(0.1)
        except Exception:
            yield f"data: {json.dumps({'event': 'Telemetry stream ended', 'level': 'WARNING'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
