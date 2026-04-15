"""Tests for LLM client (local llama-cpp-python + ollama fallback)."""
import os
import pytest
from unittest.mock import patch
from zettelforge.llm_client import generate, _get_local_llm

_SKIP_INTEGRATION = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="LLM integration tests require local model or Ollama",
)


@_SKIP_INTEGRATION
class TestLocalLLM:
    def test_generate_returns_string(self):
        result = generate("Say hello in one word.", max_tokens=10)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_follows_instruction(self):
        result = generate(
            "Classify this as factual, temporal, or relational: What CVE was used?",
            max_tokens=20,
            temperature=0.1,
        )
        assert any(word in result.lower() for word in ["factual", "temporal", "relational", "exploratory", "causal"])

    def test_generate_json_extraction(self):
        import json
        result = generate(
            'Extract facts as JSON array: [{"fact": "text", "importance": 1-10}]\n'
            'Text: APT28 uses Cobalt Strike.',
            max_tokens=200,
            temperature=0.1,
        )
        # Should contain JSON-like content
        assert "{" in result

    def test_model_singleton(self):
        m1 = _get_local_llm()
        m2 = _get_local_llm()
        assert m1 is m2

    def test_system_prompt(self):
        result = generate(
            "What tools does APT28 use?",
            max_tokens=50,
            system="Reply in exactly one sentence.",
        )
        assert isinstance(result, str)
        assert len(result) > 0


class TestGenerateJsonMode:
    """Test json_mode parameter (mocked, runs in CI)."""

    @patch("zettelforge.llm_client._generate_ollama")
    @patch("zettelforge.llm_client.get_llm_provider", return_value="ollama")
    def test_json_mode_passed_to_ollama(self, mock_provider, mock_ollama):
        mock_ollama.return_value = '{"test": true}'
        generate("test prompt", json_mode=True)
        _, kwargs = mock_ollama.call_args
        assert kwargs.get("json_mode") is True

    @patch("zettelforge.llm_client._generate_ollama")
    @patch("zettelforge.llm_client.get_llm_provider", return_value="ollama")
    def test_system_prompt_passed_to_ollama(self, mock_provider, mock_ollama):
        mock_ollama.return_value = "response"
        generate("test", system="Be a JSON robot")
        _, kwargs = mock_ollama.call_args
        assert kwargs.get("system") == "Be a JSON robot"
