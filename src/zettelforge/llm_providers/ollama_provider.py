"""Ollama HTTP provider.

Extracted from the previous ``llm_client._generate_ollama`` for RFC-002
Phase 1. Reads the model tag and URL from constructor args so the
registry can build instances from :class:`~zettelforge.config.LLMConfig`.
"""

from __future__ import annotations

from typing import Any, Optional

from zettelforge.llm_providers.base import LLMEmptyResponseError

_DEFAULT_MODEL = "qwen2.5:3b"
_DEFAULT_URL = "http://localhost:11434"


class OllamaProvider:
    """Ollama HTTP API provider.

    Args:
        model: Ollama model tag (e.g. ``"qwen2.5:3b"``).
        url: Base URL of the Ollama server.
        **_: Ignored — registry may pass other providers' kwargs.
    """

    name = "ollama"

    def __init__(
        self,
        model: str = "",
        url: str = "",
        timeout: float = 60.0,
        max_retries: int = 2,
        **_: Any,
    ) -> None:
        self._model = model or _DEFAULT_MODEL
        self._url = url or _DEFAULT_URL
        self._timeout = timeout
        self._max_retries = max_retries

    def generate(
        self,
        prompt: str,
        max_tokens: int = 400,
        temperature: float = 0.1,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        import ollama

        kwargs: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            kwargs["system"] = system
        if json_mode:
            kwargs["format"] = "json"

        # Route through a per-instance Client so ``self._url`` actually affects
        # where the call goes. The module-level ``ollama.generate`` always
        # targets the default localhost:11434, ignoring this provider's config.
        client = ollama.Client(host=self._url, timeout=self._timeout)
        response = client.generate(**kwargs)
        text = str(response.get("response", "")).strip()
        if not text:
            raise LLMEmptyResponseError(model=self._model, prompt_len=len(prompt))
        return text
