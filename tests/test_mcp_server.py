"""Lightweight protocol tests for the MCP server.

These tests cover only the parts of the server that must work without
instantiating a MemoryManager — initialize, tools/list, and the lazy
singleton contract. Tool-call behaviour is exercised through the full
MemoryManager path in the existing integration tests.
"""

from __future__ import annotations

import io
import json
import sys

import pytest


@pytest.fixture
def reset_mcp_singleton():
    """Reset the lazy singleton between tests."""
    import zettelforge.mcp.server as server

    original = server._mm
    server._mm = None
    yield
    server._mm = original


def _exchange(payloads: list[dict]) -> list[dict]:
    """Run run_stdio() with the given messages and return parsed responses."""
    from zettelforge.mcp import run_stdio

    stdin_data = "".join(json.dumps(p) + "\n" for p in payloads)
    saved_stdin, saved_stdout = sys.stdin, sys.stdout
    try:
        sys.stdin = io.StringIO(stdin_data)
        sys.stdout = io.StringIO()
        run_stdio()
        raw = sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = saved_stdin, saved_stdout

    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def test_import_does_not_instantiate_memory_manager():
    """Importing zettelforge.mcp must not create a MemoryManager."""
    import zettelforge.mcp as pkg
    import zettelforge.mcp.server as server

    # Public API is still accessible.
    assert callable(pkg.run_stdio)
    assert isinstance(pkg.TOOLS, list) and len(pkg.TOOLS) == 7

    # Singleton is lazy — not created yet.
    assert server._mm is None, "MemoryManager should not be instantiated on import"


def test_initialize_returns_server_info(reset_mcp_singleton):
    """The `initialize` handshake must work without touching the backend."""
    import zettelforge.mcp.server as server

    [response] = _exchange([{"jsonrpc": "2.0", "id": 0, "method": "initialize"}])

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 0
    result = response["result"]
    assert result["protocolVersion"]
    assert result["serverInfo"]["name"] == "zettelforge"
    assert result["serverInfo"]["version"]
    assert "tools" in result["capabilities"]

    # Still lazy.
    assert server._mm is None


def test_tools_list_returns_expected_tools(reset_mcp_singleton):
    """`tools/list` must return exactly the seven MCP tools."""
    import zettelforge.mcp.server as server

    [response] = _exchange([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])

    tools = response["result"]["tools"]
    names = {t["name"] for t in tools}
    expected = {
        "zettelforge_remember",
        "zettelforge_recall",
        "zettelforge_synthesize",
        "zettelforge_entity",
        "zettelforge_graph",
        "zettelforge_stats",
        "zettelforge_sync",
    }
    assert names == expected

    # Every tool must have a JSON-Schema-shaped input schema.
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"
        assert "properties" in tool["inputSchema"]

    # Still lazy — tools/list must not spin up MemoryManager.
    assert server._mm is None


def test_unknown_method_returns_jsonrpc_error(reset_mcp_singleton):
    [response] = _exchange([{"jsonrpc": "2.0", "id": 9, "method": "does/not/exist"}])

    assert response["id"] == 9
    assert response["error"]["code"] == -32601
    assert "Unknown method" in response["error"]["message"]


def test_notifications_initialized_is_silent(reset_mcp_singleton):
    """Notification messages (no id) must not produce a response."""
    responses = _exchange([{"jsonrpc": "2.0", "method": "notifications/initialized"}])
    assert responses == []


def test_threatrecall_tool_name_is_rewritten(monkeypatch, reset_mcp_singleton):
    """The `threatrecall_*` compat alias is mapped to `zettelforge_*`."""
    import zettelforge.mcp.server as server

    captured: dict = {}

    class _FakeMM:
        def get_stats(self) -> dict:
            captured["called"] = True
            return {"total_notes": 0, "retrievals": 0, "entity_index": {}}

    server._mm = _FakeMM()  # type: ignore[assignment]
    try:
        result = server.handle_tool_call("threatrecall_stats", {})
    finally:
        pass  # fixture resets on teardown

    assert captured.get("called") is True
    assert "version" in result
    assert "total_notes" in result
