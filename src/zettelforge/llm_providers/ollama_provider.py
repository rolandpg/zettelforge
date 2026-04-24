"""Ollama HTTP provider.

Extracted from the previous ``llm_client._generate_ollama`` for RFC-002
Phase 1. Reads the model tag and URL from constructor args so the
registry can build instances from :class:`~zettelforge.config.LLMConfig`.
"""

from __future__ import annotations

from typing import Any, Optional

_DEFAULT_MODEL = "qwen2.5:3b"
_DEFAULT_URL = "http://localhost:11434"


class OllamaProvider:
    """Ollama HTTP API provider.

    Args:
        model: Ollama model tag (e.g. ``"qwen2.5:3b"``).
        url: Base URL of the Ollama server.
        timeout: HTTP timeout in seconds (applied to ``ollama.Client``). Before
            RFC-010 this kwarg was silently dropped — requests inherited the
            ollama-python client's effectively-unbounded default. Production
            audit 2026-04-24 attributed `remember()` p95 of ~66s to hung
            Ollama calls; fixing this caps the hang class.
        **_: Ignored — registry may pass other providers' kwargs.
    """

    name = "ollama"

    def __init__(
        self,
        model: str = "",
        url: str = "",
        timeout: float = 60.0,
        **_: Any,
    ) -> None:
        self._model = model or _DEFAULT_MODEL
        self._url = url or _DEFAULT_URL
        self._timeout = timeout

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
        # ``timeout`` is now threaded through per RFC-010.
        client = ollama.Client(host=self._url, timeout=self._timeout)
        response = client.generate(**kwargs)
        return str(response.get("response", "")).strip()
