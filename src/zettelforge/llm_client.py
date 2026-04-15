"""
LLM Client — Unified interface for local (llama-cpp-python) and remote (Ollama) LLM.

Uses llama-cpp-python with Qwen2.5-3B-Instruct by default (in-process, no server).
Falls back to Ollama HTTP if configured via provider setting.

Usage:
    from zettelforge.llm_client import generate
    text = generate("Extract facts from: APT28 uses Cobalt Strike", max_tokens=400)
"""

import os
import threading
from typing import Optional

from zettelforge.log import get_logger

_logger = get_logger("zettelforge.llm_client")


# ── Configuration ────────────────────────────────────────────────────────────

DEFAULT_LLM_PROVIDER = "local"  # "local" (llama-cpp-python) or "ollama" (HTTP)
DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-3B-Instruct-GGUF"
DEFAULT_LLM_FILENAME = "qwen2.5-3b-instruct-q4_k_m.gguf"
DEFAULT_OLLAMA_MODEL = "qwen2.5:3b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


def get_llm_provider() -> str:
    return os.environ.get("ZETTELFORGE_LLM_PROVIDER", DEFAULT_LLM_PROVIDER)


def get_llm_model() -> str:
    return os.environ.get("ZETTELFORGE_LLM_MODEL", DEFAULT_LLM_MODEL)


def get_ollama_url() -> str:
    return os.environ.get("ZETTELFORGE_LLM_URL", DEFAULT_OLLAMA_URL)


# ── Local LLM singleton ─────────────────────────────────────────────────────

_llm = None
_llm_lock = threading.Lock()


def _get_local_llm():
    """Get or create the local Llama model (singleton)."""
    global _llm
    if _llm is None:
        with _llm_lock:
            if _llm is None:
                from llama_cpp import Llama

                _llm = Llama.from_pretrained(
                    repo_id=get_llm_model(),
                    filename=os.environ.get("ZETTELFORGE_LLM_FILENAME", DEFAULT_LLM_FILENAME),
                    n_ctx=4096,
                    n_gpu_layers=0,
                    verbose=False,
                )
    return _llm


# ── Public API ───────────────────────────────────────────────────────────────


def generate(
    prompt: str,
    max_tokens: int = 400,
    temperature: float = 0.1,
    system: Optional[str] = None,
    json_mode: bool = False,
) -> str:
    """
    Generate text from a prompt. Uses local GGUF model by default, Ollama as fallback.

    Args:
        prompt: The user prompt.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature (0.0 = deterministic).
        system: Optional system prompt.
        json_mode: If True, instruct the backend to return JSON output where supported.

    Returns:
        Generated text string.
    """
    provider = get_llm_provider()

    if provider == "local":
        try:
            return _generate_local(prompt, max_tokens, temperature, system, json_mode=json_mode)
        except Exception:
            _logger.debug("llamacpp_unavailable_trying_ollama", exc_info=True)

    # Ollama fallback
    try:
        return _generate_ollama(prompt, max_tokens, temperature, system=system, json_mode=json_mode)
    except Exception:
        _logger.error("all_llm_backends_failed", exc_info=True)
        return ""


def _generate_local(
    prompt: str, max_tokens: int, temperature: float, system: Optional[str], json_mode: bool = False
) -> str:
    """Generate via in-process llama-cpp-python."""
    llm = _get_local_llm()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    output = llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return output["choices"][0]["message"]["content"].strip()


def _generate_ollama(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system: Optional[str] = None,
    json_mode: bool = False,
) -> str:
    """Generate via Ollama HTTP API."""
    import ollama

    model = os.environ.get("ZETTELFORGE_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    kwargs: dict = {
        "model": model,
        "prompt": prompt,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    if system:
        kwargs["system"] = system
    if json_mode:
        kwargs["format"] = "json"
    response = ollama.generate(**kwargs)
    return response.get("response", "").strip()
