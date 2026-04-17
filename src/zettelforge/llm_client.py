"""Unified LLM interface.

Delegates to a registered :class:`~zettelforge.llm_providers.base.LLMProvider`
chosen by ``llm.provider`` config. The public ``generate()`` signature
is stable — RFC-002 Phase 1 refactored the internals without changing
the call contract, so existing call sites (``fact_extractor``,
``memory_updater``, ``synthesis_generator``, ``intent_classifier``,
``note_constructor``, ``entity_indexer``, ``memory_evolver``) do not
need to change.

Example::

    from zettelforge.llm_client import generate

    text = generate("Extract facts from: APT28 uses Cobalt Strike")
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from zettelforge.llm_providers import registry
from zettelforge.log import get_logger

_logger = get_logger("zettelforge.llm_client")


# ── Environment-variable helpers (preserved for backward compat) ──────────────

DEFAULT_LLM_PROVIDER = "local"
DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-3B-Instruct-GGUF"
DEFAULT_LLM_FILENAME = "qwen2.5-3b-instruct-q4_k_m.gguf"
DEFAULT_OLLAMA_MODEL = "qwen2.5:3b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


def get_llm_provider() -> str:
    """Return the configured provider name, honouring env var and config."""
    if value := os.environ.get("ZETTELFORGE_LLM_PROVIDER"):
        return value
    try:
        from zettelforge.config import get_config

        return get_config().llm.provider or DEFAULT_LLM_PROVIDER
    except Exception:
        return DEFAULT_LLM_PROVIDER


def get_llm_model() -> str:
    """Return the configured LLM model identifier (env > config > default)."""
    if value := os.environ.get("ZETTELFORGE_LLM_MODEL"):
        return value
    try:
        from zettelforge.config import get_config

        return get_config().llm.model or DEFAULT_LLM_MODEL
    except Exception:
        return DEFAULT_LLM_MODEL


def get_ollama_url() -> str:
    """Return the configured LLM server URL for the ollama provider."""
    if value := os.environ.get("ZETTELFORGE_LLM_URL"):
        return value
    try:
        from zettelforge.config import get_config

        return get_config().llm.url or DEFAULT_OLLAMA_URL
    except Exception:
        return DEFAULT_OLLAMA_URL


# ── Provider kwargs ──────────────────────────────────────────────────────────


def _provider_kwargs(provider_name: str) -> Dict[str, Any]:
    """Build constructor kwargs for a provider from current config + env.

    The registry caches instances keyed by name, so these kwargs are only
    consumed on first creation. A :func:`reload` is required to pick up
    config changes at runtime.
    """
    kwargs: Dict[str, Any] = {}

    try:
        from zettelforge.config import get_config

        llm_cfg = get_config().llm
    except Exception:
        llm_cfg = None

    if llm_cfg is not None:
        kwargs["model"] = llm_cfg.model
        kwargs["url"] = llm_cfg.url
        kwargs["api_key"] = getattr(llm_cfg, "api_key", "")
        kwargs["timeout"] = getattr(llm_cfg, "timeout", 60.0)
        kwargs["max_retries"] = getattr(llm_cfg, "max_retries", 2)
        kwargs.update(getattr(llm_cfg, "extra", {}) or {})

    # Env overrides preserved from pre-RFC-002 behaviour.
    if provider_name == "local":
        kwargs["model"] = os.environ.get(
            "ZETTELFORGE_LLM_MODEL", kwargs.get("model") or DEFAULT_LLM_MODEL
        )
        kwargs["filename"] = os.environ.get(
            "ZETTELFORGE_LLM_FILENAME",
            kwargs.get("filename") or DEFAULT_LLM_FILENAME,
        )
    elif provider_name == "ollama":
        # ``ZETTELFORGE_OLLAMA_MODEL`` is deprecated in favour of
        # ``ZETTELFORGE_LLM_MODEL`` but still honoured through v2.x.
        kwargs["model"] = os.environ.get(
            "ZETTELFORGE_LLM_MODEL",
            os.environ.get("ZETTELFORGE_OLLAMA_MODEL", kwargs.get("model") or DEFAULT_OLLAMA_MODEL),
        )
        kwargs["url"] = os.environ.get(
            "ZETTELFORGE_LLM_URL", kwargs.get("url") or DEFAULT_OLLAMA_URL
        )

    return {k: v for k, v in kwargs.items() if v != ""}


def _fallback_provider(primary: str) -> Optional[str]:
    """Return the fallback provider name for ``primary`` (or ``None``)."""
    try:
        from zettelforge.config import get_config

        fallback = getattr(get_config().llm, "fallback", "") or ""
    except Exception:
        fallback = ""

    if fallback:
        return fallback if fallback != primary else None

    # Historical implicit fallback: local → ollama. Preserved so existing
    # installs keep working if the GGUF model fails to load.
    if primary == "local":
        return "ollama"
    return None


# ── Public API ───────────────────────────────────────────────────────────────


def generate(
    prompt: str,
    max_tokens: int = 400,
    temperature: float = 0.1,
    system: Optional[str] = None,
    json_mode: bool = False,
) -> str:
    """Generate text from a prompt via the configured LLM provider.

    Args:
        prompt: The user prompt.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature (``0.0`` = deterministic).
        system: Optional system prompt.
        json_mode: Instruct the backend to emit JSON where supported.

    Returns:
        Generated text, or ``""`` when both primary and fallback providers
        fail recoverably. Configuration errors are propagated.
    """
    primary = get_llm_provider()

    try:
        provider = registry.get(primary, **_provider_kwargs(primary))
    except ImportError:
        # Primary SDK missing — do not silently fall back, surface it.
        raise
    except ValueError:
        _logger.error("unknown_llm_provider", provider=primary)
        raise

    try:
        return provider.generate(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            json_mode=json_mode,
        )
    except ImportError:
        # Missing SDK for the primary provider — same rule as above.
        raise
    except Exception:
        _logger.debug("primary_provider_failed", provider=primary, exc_info=True)

    fallback_name = _fallback_provider(primary)
    if fallback_name is None:
        _logger.error("all_llm_backends_failed", provider=primary)
        return ""

    try:
        fallback = registry.get(fallback_name, **_provider_kwargs(fallback_name))
        return fallback.generate(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            json_mode=json_mode,
        )
    except Exception:
        _logger.error(
            "all_llm_backends_failed", primary=primary, fallback=fallback_name, exc_info=True
        )
        return ""


# ── Backward-compat shims ────────────────────────────────────────────────────
# The old private helpers are kept so ``from zettelforge.llm_client import
# _get_local_llm`` and similar internal patches in existing tests continue
# to work. They now thread through the provider registry.


def _get_local_llm() -> Any:
    """Return the underlying llama-cpp ``Llama`` instance (test/debug only)."""
    provider = registry.get("local", **_provider_kwargs("local"))
    if hasattr(provider, "_get_llm"):
        return provider._get_llm()
    raise RuntimeError("local provider has no _get_llm() hook")


def _generate_local(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system: Optional[str],
    json_mode: bool = False,
) -> str:
    """Deprecated compat shim — prefer :func:`generate`."""
    provider = registry.get("local", **_provider_kwargs("local"))
    return provider.generate(
        prompt, max_tokens=max_tokens, temperature=temperature, system=system, json_mode=json_mode
    )


def _generate_ollama(
    prompt: str,
    max_tokens: int,
    temperature: float,
    system: Optional[str] = None,
    json_mode: bool = False,
) -> str:
    """Deprecated compat shim — prefer :func:`generate`."""
    provider = registry.get("ollama", **_provider_kwargs("ollama"))
    return provider.generate(
        prompt, max_tokens=max_tokens, temperature=temperature, system=system, json_mode=json_mode
    )
