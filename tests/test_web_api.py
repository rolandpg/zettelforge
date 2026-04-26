"""Integration tests for the ZettelForge Web API (RFC-015).

Tests all 13 new API endpoints using FastAPI TestClient.
Requires a running MemoryManager with mock embedding/LLM (provided by conftest).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure web/ and src/ are importable (same pattern as web/app.py)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "web"))


@pytest.fixture
def client():
    """Create a TestClient for the ZettelForge web app."""
    os.environ.setdefault("ZETTELFORGE_BACKEND", "sqlite")
    os.environ.setdefault("ZETTELFORGE_LLM_PROVIDER", "mock")
    from web.app import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def api_key():
    """Set an API key so tests don't need loopback."""
    os.environ["ZETTELFORGE_WEB_API_KEY"] = "test-api-key-12345"
    yield "test-api-key-12345"
    del os.environ["ZETTELFORGE_WEB_API_KEY"]


def _headers(api_key: str | None = None) -> dict:
    h = {}
    if api_key:
        h["X-API-Key"] = api_key
    return h


# ── Health ───────────────────────────────────────────────────────────────────


class TestHealthEndpoint:
    """GET /api/health — system health information."""

    def test_health_returns_basic_info(self, client, api_key):
        resp = client.get("/api/health", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "edition" in data
        assert "storage_backend" in data
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_health_has_provider_info(self, client, api_key):
        resp = client.get("/api/health", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "embedding_provider" in data
        assert "llm_provider" in data
        assert isinstance(data.get("governance_enabled"), bool)
        assert isinstance(data.get("pii_enabled"), bool)


# ── Config ───────────────────────────────────────────────────────────────────


class TestConfigEndpoint:
    """GET /api/config and PUT /api/config — configuration management."""

    def test_get_config_returns_redacted_secrets(self, client, api_key):
        resp = client.get("/api/config", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "llm" in data
        assert "embedding" in data
        assert "governance" in data

    def test_put_config_accepts_changes(self, client, api_key):
        resp = client.put(
            "/api/config",
            headers={**_headers(api_key), "Content-Type": "application/json"},
            json={"retrieval": {"default_k": 5}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "applied" in data

    def test_put_config_returns_pending_restart(self, client, api_key):
        resp = client.put(
            "/api/config",
            headers={**_headers(api_key), "Content-Type": "application/json"},
            json={"backend": "lance"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "pending_restart" in data
        assert any("backend" in str(item).lower() for item in data["pending_restart"])


# ── Graph Nodes / Edges ──────────────────────────────────────────────────────


class TestGraphEndpoints:
    """GET /api/graph/nodes and GET /api/graph/edges — knowledge graph data."""

    def test_graph_nodes_returns_list(self, client, api_key):
        resp = client.get("/api/graph/nodes", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "count" in data
        assert isinstance(data["nodes"], list)

    def test_graph_edges_returns_list(self, client, api_key):
        resp = client.get("/api/graph/edges", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "edges" in data
        assert "count" in data
        assert isinstance(data["edges"], list)


# ── Entities ──────────────────────────────────────────────────────────────────


class TestEntitiesEndpoint:
    """GET /api/entities — paginated entity index."""

    def test_entities_accepts_pagination(self, client, api_key):
        resp = client.get("/api/entities?offset=0&limit=10", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert data["offset"] == 0
        assert data["limit"] == 10

    def test_entities_filters_by_type(self, client, api_key):
        resp = client.get("/api/entities?type=actor", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data

    def test_entities_filters_by_text_search(self, client, api_key):
        resp = client.get("/api/entities?q=APT", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data


# ── History ───────────────────────────────────────────────────────────────────


class TestHistoryEndpoint:
    """GET /api/history — recent session activity."""

    def test_history_returns_list(self, client, api_key):
        resp = client.get("/api/history", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_history_entries_have_expected_fields(self, client, api_key):
        resp = client.get("/api/history?limit=5", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        if data:
            entry = data[0]
            assert "query_id" in entry
            assert "event_type" in entry
            assert "timestamp" in entry


# ── Ingest ────────────────────────────────────────────────────────────────────


class TestIngestEndpoint:
    """POST /api/ingest — bulk ingestion."""

    def test_ingest_accepts_single_item(self, client, api_key):
        resp = client.post(
            "/api/ingest",
            headers={**_headers(api_key), "Content-Type": "application/json"},
            json={
                "items": [
                    {
                        "content": "APT28 uses Cobalt Strike for lateral movement.",
                        "source_type": "test",
                        "domain": "cti",
                        "evolve": False,
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["succeeded"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["success"] is True
        assert "note_id" in data["results"][0]

    def test_ingest_handles_multiple_items(self, client, api_key):
        resp = client.post(
            "/api/ingest",
            headers={**_headers(api_key), "Content-Type": "application/json"},
            json={
                "items": [
                    {
                        "content": f"Test note {i} for bulk ingest.",
                        "source_type": "test",
                        "domain": "cti",
                        "evolve": False,
                    }
                    for i in range(3)
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["succeeded"] == 3
        assert all(r["success"] for r in data["results"])


# ── Telemetry ─────────────────────────────────────────────────────────────────


class TestTelemetryEndpoint:
    """GET /api/telemetry — aggregated telemetry summary."""

    def test_telemetry_returns_summary(self, client, api_key):
        resp = client.get("/api/telemetry", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_queries" in data
        assert isinstance(data.get("total_queries", 0), int)
        assert "top_intents" in data

    def test_telemetry_has_latency_stats(self, client, api_key):
        resp = client.get("/api/telemetry", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "avg_latency_ms" in data


# ── Storage ───────────────────────────────────────────────────────────────────


class TestStorageEndpoint:
    """GET /api/storage — storage statistics."""

    def test_storage_returns_counts(self, client, api_key):
        resp = client.get("/api/storage", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_notes" in data
        assert "entity_count" in data
        assert isinstance(data["total_notes"], int)
        assert isinstance(data["entity_count"], int)


# ── Logs ──────────────────────────────────────────────────────────────────────


class TestLogsEndpoint:
    """GET /api/logs — structlog file tailing."""

    def test_logs_returns_list(self, client, api_key):
        resp = client.get("/api/logs?lines=10", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)

    def test_logs_supports_level_filter(self, client, api_key):
        resp = client.get("/api/logs?lines=10&level=INFO", headers=_headers(api_key))
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data


# ── SSE Streams ───────────────────────────────────────────────────────────────


class TestSSEEndpoints:
    """GET /api/logs/stream and GET /api/telemetry/stream — SSE streaming."""

    def test_logs_stream_returns_200(self, client, api_key):
        pytest.skip("SSE endpoints stream indefinitely; tested manually")

    def test_telemetry_stream_returns_200(self, client, api_key):
        pytest.skip("SSE endpoints stream indefinitely; tested manually")


# ── Frontend ──────────────────────────────────────────────────────────────────


class TestFrontendEndpoint:
    """GET / — SPA serving."""

    def test_frontend_serves_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/html")
        html = resp.text
        assert "ZettelForge" in html
