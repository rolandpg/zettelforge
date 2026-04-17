"""In-process llama-cpp-python GGUF provider (``local``).

Extracted from the previous ``llm_client._generate_local`` for RFC-002
Phase 1. Lazy-loads the GGUF model on first ``generate()`` call so the
registry can instantiate the provider without paying model-load cost at
import time.
"""

from __future__ import annotations

import threading
from typing import Any, Optional

from zettelforge.log import get_logger

_logger = get_logger("zettelforge.llm_providers.local")

_DEFAULT_MODEL = "Qwen/Qwen2.5-3B-Instruct-GGUF"
_DEFAULT_FILENAME = "qwen2.5-3b-instruct-q4_k_m.gguf"
_DEFAULT_N_CTX = 4096


class LocalProvider:
    """llama-cpp-python provider.

    Args:
        model: HuggingFace repo id (e.g. ``"Qwen/Qwen2.5-3B-Instruct-GGUF"``).
        filename: Specific quantized file within the repo.
        n_ctx: Context window size in tokens.
        **_: Accept and ignore extra kwargs so the registry can pass
            fields like ``api_key`` or ``timeout`` that only apply to
            other providers without breaking instantiation.
    """

    name = "local"

    def __init__(
        self,
        model: str = "",
        filename: str = "",
        n_ctx: int = _DEFAULT_N_CTX,
        **_: Any,
    ) -> None:
        self._model_id = model or _DEFAULT_MODEL
        self._filename = filename or _DEFAULT_FILENAME
        self._n_ctx = n_ctx
        self._llm: Any = None
        self._lock = threading.Lock()

    def _get_llm(self) -> Any:
        if self._llm is None:
            with self._lock:
                if self._llm is None:
                    try:
                        from llama_cpp import Llama
                    except ImportError as exc:
                        raise ImportError(
                            "Local LLM requires llama-cpp-python. "
                            "Install with: pip install zettelforge[local]"
                        ) from exc

                    self._llm = Llama.from_pretrained(
                        repo_id=self._model_id,
                        filename=self._filename,
                        n_ctx=self._n_ctx,
                        n_gpu_layers=0,
                        verbose=False,
                    )
                    _logger.debug("local_llm_loaded", model=self._model_id)
        return self._llm

    def generate(
        self,
        prompt: str,
        max_tokens: int = 400,
        temperature: float = 0.1,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        llm = self._get_llm()

        messages: list[dict[str, str]] = []
        # llama-cpp-python has no response_format; steer via system prompt.
        if json_mode:
            json_hint = "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no commentary."
            system = (system + json_hint) if system else json_hint.strip()
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        output = llm.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return str(output["choices"][0]["message"]["content"]).strip()
