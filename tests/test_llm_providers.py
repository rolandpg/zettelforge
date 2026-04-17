"""Unit tests for the RFC-002 Phase 1 provider infrastructure.

Covers the registry contract, the built-in providers' behaviour, and
the refactored ``generate()`` delegation path.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from zettelforge.llm_providers import (
    LocalProvider,
    MockProvider,
    OllamaProvider,
    available,
    registry,
)
from zettelforge.llm_providers.base import LLMProvider


@pytest.fixture(autouse=True)
def reset_registry_instances():
    """Clear cached provider instances between tests.

    Registrations created when ``zettelforge.llm_providers`` is imported
    are preserved; only cached singleton instances are reset.
    """
    registry.reset()
    yield
    registry.reset()


# ── Protocol contract ────────────────────────────────────────────────────────


class TestLLMProviderProtocol:
    def test_local_satisfies_protocol(self):
        assert isinstance(LocalProvider(model="x"), LLMProvider)

    def test_ollama_satisfies_protocol(self):
        assert isinstance(OllamaProvider(model="x"), LLMProvider)

    def test_mock_satisfies_protocol(self):
        assert isinstance(MockProvider(), LLMProvider)

    def test_builtins_registered(self):
        names = available()
        assert "local" in names
        assert "ollama" in names
        assert "mock" in names


# ── Registry ─────────────────────────────────────────────────────────────────


class TestRegistry:
    def test_get_returns_singleton(self):
        a = registry.get("mock")
        b = registry.get("mock")
        assert a is b

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            registry.get("definitely-not-a-provider")

    def test_register_duplicate_raises(self):
        with pytest.raises(ValueError, match="already registered"):
            registry.register("local", LocalProvider)

    def test_reset_clears_instances_not_registrations(self):
        registry.get("mock")
        registry.reset()
        # A fresh instance is created after reset.
        fresh = registry.get("mock")
        assert isinstance(fresh, MockProvider)
        assert "mock" in available()


# ── MockProvider ─────────────────────────────────────────────────────────────


class TestMockProvider:
    def test_returns_canned_response(self):
        mock = MockProvider(responses=["hello"])
        assert mock.generate("anything") == "hello"

    def test_cycles_through_responses(self):
        mock = MockProvider(responses=["a", "b"])
        assert mock.generate("q1") == "a"
        assert mock.generate("q2") == "b"
        assert mock.generate("q3") == "a"  # cycles

    def test_records_every_call(self):
        mock = MockProvider()
        mock.generate("ask", max_tokens=10, temperature=0.5, system="sys", json_mode=True)
        assert len(mock.calls) == 1
        call = mock.calls[0]
        assert call == {
            "prompt": "ask",
            "max_tokens": 10,
            "temperature": 0.5,
            "system": "sys",
            "json_mode": True,
        }

    def test_default_response_list(self):
        mock = MockProvider()
        assert mock.generate("") == "mock response"


# ── OllamaProvider ───────────────────────────────────────────────────────────

# The ollama SDK is not a core dependency — skip this class when it is
# unavailable (e.g. the minimal CI environment without zettelforge[local]).
pytest.importorskip("ollama", reason="ollama SDK not installed")


class TestOllamaProvider:
    """Verify OllamaProvider wraps the ollama SDK Client correctly.

    The provider instantiates ``ollama.Client(host=<url>)`` so that
    configuring ``llm.url`` actually directs requests to the intended
    server. Tests patch the ``Client`` class and inspect the call made
    on the returned instance.
    """

    def test_generate_calls_ollama_with_expected_args(self):
        provider = OllamaProvider(model="qwen2.5:3b", url="http://host:11434")
        with patch("ollama.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.generate.return_value = {"response": "ok"}

            result = provider.generate(
                "hello", max_tokens=50, temperature=0.2, system="sys", json_mode=True
            )

            assert result == "ok"
            mock_client_cls.assert_called_once_with(host="http://host:11434")
            args, kwargs = mock_client.generate.call_args
            assert kwargs["model"] == "qwen2.5:3b"
            assert kwargs["prompt"] == "hello"
            assert kwargs["system"] == "sys"
            assert kwargs["format"] == "json"
            assert kwargs["options"] == {"temperature": 0.2, "num_predict": 50}

    def test_generate_omits_system_when_absent(self):
        provider = OllamaProvider(model="qwen2.5:3b")
        with patch("ollama.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.generate.return_value = {"response": "ok"}
            provider.generate("hello")
            _, kwargs = mock_client.generate.call_args
            assert "system" not in kwargs
            assert "format" not in kwargs

    def test_generate_empty_response_returns_empty_string(self):
        provider = OllamaProvider(model="qwen2.5:3b")
        with patch("ollama.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.generate.return_value = {}
            assert provider.generate("prompt") == ""

    def test_generate_routes_through_configured_host(self):
        """``llm.url`` is honoured via ``ollama.Client(host=...)``."""
        provider = OllamaProvider(model="qwen2.5:3b", url="http://gpu-box:11434")
        with patch("ollama.Client") as mock_client_cls:
            mock_client_cls.return_value.generate.return_value = {"response": "ok"}
            provider.generate("hello")
            mock_client_cls.assert_called_once_with(host="http://gpu-box:11434")

    def test_unknown_kwargs_ignored_at_construction(self):
        # The registry forwards kwargs meant for other providers; they
        # must be accepted silently.
        provider = OllamaProvider(
            model="qwen2.5:3b",
            api_key="ignored",
            timeout=120.0,
            max_retries=5,
        )
        assert provider.name == "ollama"


# ── LocalProvider ────────────────────────────────────────────────────────────


class TestLocalProvider:
    def test_unknown_kwargs_ignored_at_construction(self):
        provider = LocalProvider(
            model="Qwen/Qwen2.5-3B-Instruct-GGUF",
            filename="qwen2.5-3b-instruct-q4_k_m.gguf",
            api_key="ignored",
            timeout=120.0,
        )
        assert provider.name == "local"

    def test_json_mode_appends_instruction_when_no_system(self):
        provider = LocalProvider()
        fake_llm = _FakeLlamaCpp()
        provider._llm = fake_llm
        provider.generate("prompt", json_mode=True)
        messages = fake_llm.last_messages
        assert messages[0]["role"] == "system"
        assert "JSON" in messages[0]["content"]

    def test_json_mode_extends_existing_system(self):
        provider = LocalProvider()
        fake_llm = _FakeLlamaCpp()
        provider._llm = fake_llm
        provider.generate("prompt", system="Base prompt.", json_mode=True)
        system = fake_llm.last_messages[0]["content"]
        assert system.startswith("Base prompt.")
        assert "JSON" in system


class _FakeLlamaCpp:
    """Minimal stand-in for llama_cpp.Llama used by LocalProvider tests."""

    def __init__(self) -> None:
        self.last_messages: list[dict[str, str]] = []

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> dict:
        self.last_messages = messages
        return {"choices": [{"message": {"content": "  out  "}}]}


# ── generate() delegation (llm_client) ───────────────────────────────────────


class TestGenerateDelegatesToProvider:
    def test_generate_uses_configured_provider(self):
        from zettelforge.llm_client import generate

        canned = MockProvider(responses=["from mock"])
        with patch.dict(os.environ, {"ZETTELFORGE_LLM_PROVIDER": "mock"}):
            with patch("zettelforge.llm_providers.registry.get", return_value=canned):
                result = generate("hi")
        assert result == "from mock"
        assert canned.calls[0]["prompt"] == "hi"

    def test_generate_returns_empty_on_recoverable_failure(self):
        from zettelforge.llm_client import generate

        class _Flaky:
            name = "flaky"

            def generate(self, *a, **kw):  # noqa: D401 — test stub
                raise RuntimeError("transient")

        with patch.dict(
            os.environ,
            {"ZETTELFORGE_LLM_PROVIDER": "flaky", "ZETTELFORGE_LLM_FALLBACK": ""},
        ):
            with patch(
                "zettelforge.llm_providers.registry.get",
                side_effect=[_Flaky(), _Flaky()],
            ):
                # No fallback configured + primary="flaky" is not "local",
                # so the implicit fallback also does not kick in.
                result = generate("hi")
        assert result == ""

    def test_generate_propagates_import_error(self):
        from zettelforge.llm_client import generate

        with patch.dict(os.environ, {"ZETTELFORGE_LLM_PROVIDER": "local"}):
            with patch(
                "zettelforge.llm_providers.registry.get",
                side_effect=ImportError("missing sdk"),
            ):
                with pytest.raises(ImportError):
                    generate("hi")


# ── Config (RFC-002 extensions) ──────────────────────────────────────────────


class TestLLMConfigRepr:
    def test_api_key_is_redacted(self):
        from zettelforge.config import LLMConfig

        cfg = LLMConfig(api_key="sk-supersecret")
        text = repr(cfg)
        assert "sk-supersecret" not in text
        assert "***" in text

    def test_empty_api_key_shows_empty_string(self):
        from zettelforge.config import LLMConfig

        cfg = LLMConfig()
        assert "api_key=''" in repr(cfg)


class TestEnvRefResolution:
    def test_resolves_env_var(self, monkeypatch):
        from zettelforge.config import _resolve_env_refs

        monkeypatch.setenv("MY_TEST_KEY", "sk-abc")
        assert _resolve_env_refs("${MY_TEST_KEY}") == "sk-abc"

    def test_missing_env_var_becomes_empty(self, monkeypatch):
        from zettelforge.config import _resolve_env_refs

        monkeypatch.delenv("DEFINITELY_NOT_SET_9X", raising=False)
        assert _resolve_env_refs("${DEFINITELY_NOT_SET_9X}") == ""

    def test_literal_strings_unchanged(self):
        from zettelforge.config import _resolve_env_refs

        assert _resolve_env_refs("plain") == "plain"
        assert _resolve_env_refs("") == ""
