# RFC-002: Universal LLM Provider Interface

## Metadata

- **Author**: Patrick Roland
- **Status**: Draft
- **Created**: 2026-04-16
- **Last Updated**: 2026-04-16
- **Reviewers**: Adversarial review completed 2026-04-16 (3 blockers fixed, 7 warnings addressed)
- **Related Tickets**: Community request — multi-provider LLM support
- **Related RFCs**: RFC-001 (Conversational Entity Extractor — depends on `generate()` stability)

## Summary

Introduce a pluggable LLM provider interface behind the existing `generate()` function so users can point ZettelForge at any LLM backend — OpenAI, Anthropic, Azure OpenAI, AWS Bedrock, Google Vertex, vLLM, or any OpenAI-compatible endpoint — without changing any calling code. Cloud providers are opt-in extras; the default remains local llama-cpp-python for offline operation.

## Motivation

ZettelForge currently supports two LLM backends: `local` (llama-cpp-python in-process GGUF) and `ollama` (HTTP to localhost:11434). Both are local-first, which aligns with the project's offline-capable philosophy. However, users have three reasons to want cloud and remote providers:

**1. Quality ceiling.** The default Qwen2.5-3B model is adequate for fact extraction and intent classification, but synthesis and multi-hop reasoning benefit substantially from larger models (GPT-4o, Claude Opus, Qwen-72B). Users with API keys want to use them.

**2. Deployment flexibility.** Teams running ZettelForge in cloud environments (Azure Container Apps, AWS ECS) already have LLM endpoints available via their cloud provider's AI services. Forcing them through Ollama adds an unnecessary proxy hop.

**3. Community adoption.** An MIT-licensed project that only supports two local backends creates friction for the majority of developers whose default LLM interaction is through OpenAI-compatible APIs. Lowering that barrier directly serves the open-source community strategy.

The current `llm_client.py` is 151 lines with hardcoded provider logic. Adding each new provider as another `_generate_*` function will not scale — the file would grow linearly with provider count, each provider would need its own config parsing, and testing would require mocking increasingly tangled conditionals.

### Who benefits

- **Solo analysts** running ZettelForge on a laptop with an OpenAI API key
- **Teams** deploying on cloud infrastructure with Azure OpenAI or Bedrock endpoints
- **Self-hosters** running vLLM, TGI, or LiteLLM behind an OpenAI-compatible proxy
- **Contributors** who can add new providers without modifying core extraction/synthesis code

## Proposed Design

### Architecture Overview

```
generate()                          # Public API — unchanged
  |
  v
ProviderRegistry.get(name)          # Returns configured LLMProvider instance
  |
  v
LLMProvider.generate(...)           # Protocol method — each provider implements this
  |
  +--> LocalProvider                # llama-cpp-python (built-in, default)
  +--> OllamaProvider               # Ollama HTTP API (built-in)
  +--> OpenAICompatProvider          # Any /v1/chat/completions endpoint (built-in)
  +--> AnthropicProvider             # Anthropic native SDK (optional extra)
  +--> MockProvider                  # For testing (built-in)
```

The key design decision is a **provider protocol** with a **registry**. The `generate()` function remains the sole public API. Internally it resolves the configured provider name to an `LLMProvider` instance via the registry and delegates. Callers never import or reference providers directly.

### LLMProvider Protocol

```python
# src/zettelforge/llm_providers/base.py

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM providers must implement."""

    name: str  # e.g., "local", "ollama", "openai_compat", "anthropic"

    def generate(
        self,
        prompt: str,
        max_tokens: int = 400,
        temperature: float = 0.1,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """Generate text from a prompt. Returns empty string on failure."""
        ...
```

Using `Protocol` (PEP 544) rather than ABC because:
- No forced inheritance — third-party providers just need duck-type compatibility
- `runtime_checkable` enables `isinstance()` validation at registration time
- Consistent with ZettelForge's existing style (no ABC usage in the codebase)

### Provider Registry

```python
# src/zettelforge/llm_providers/registry.py

import threading
from typing import Callable, Dict, Optional, Type

from zettelforge.llm_providers.base import LLMProvider
from zettelforge.log import get_logger

_logger = get_logger("zettelforge.llm_providers.registry")

_registry: Dict[str, Type[LLMProvider]] = {}
_instances: Dict[str, LLMProvider] = {}
_lock = threading.Lock()


def register(name: str, provider_class: Type[LLMProvider]) -> None:
    """Register a provider class by name. Raises ValueError on duplicate."""
    if name in _registry:
        raise ValueError(f"LLM provider '{name}' is already registered")
    _registry[name] = provider_class
    _logger.debug("provider_registered", provider=name)


def get(name: str, **kwargs) -> LLMProvider:
    """
    Get or create a provider instance by name.

    Instances are singletons per provider name (thread-safe).
    kwargs are passed to the provider constructor on first creation.
    """
    if name not in _instances:
        with _lock:
            if name not in _instances:
                if name not in _registry:
                    raise ValueError(
                        f"Unknown LLM provider '{name}'. "
                        f"Available: {', '.join(sorted(_registry.keys()))}"
                    )
                _instances[name] = _registry[name](**kwargs)
                _logger.info("provider_initialized", provider=name)
    return _instances[name]


def available() -> list[str]:
    """Return sorted list of registered provider names."""
    return sorted(_registry.keys())


def reset() -> None:
    """Clear all instances (for testing). Does NOT clear registrations."""
    with _lock:
        _instances.clear()
```

The registry is populated at import time by `__init__.py` for built-in providers. Third-party providers register via entry points (see Extension Points below).

### Built-in Providers

#### LocalProvider (llama-cpp-python)

```python
# src/zettelforge/llm_providers/local_provider.py

class LocalProvider:
    """In-process GGUF model via llama-cpp-python."""

    name = "local"

    def __init__(self, model: str = "", filename: str = "", n_ctx: int = 4096, **kwargs):
        self._model_id = model or "Qwen/Qwen2.5-3B-Instruct-GGUF"
        self._filename = filename or "qwen2.5-3b-instruct-q4_k_m.gguf"
        self._n_ctx = n_ctx
        self._llm = None
        self._lock = threading.Lock()

    def _get_llm(self):
        """Lazy singleton — same thread-safe pattern as current code."""
        if self._llm is None:
            with self._lock:
                if self._llm is None:
                    try:
                        from llama_cpp import Llama
                    except ImportError:
                        raise ImportError(
                            "Local LLM requires llama-cpp-python. "
                            "Install with: pip install zettelforge[local]"
                        ) from None
                    self._llm = Llama.from_pretrained(
                        repo_id=self._model_id,
                        filename=self._filename,
                        n_ctx=self._n_ctx,
                        n_gpu_layers=0,
                        verbose=False,
                    )
        return self._llm

    def generate(self, prompt, max_tokens=400, temperature=0.1,
                 system=None, json_mode=False):
        llm = self._get_llm()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        output = llm.create_chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=temperature,
        )
        return output["choices"][0]["message"]["content"].strip()
```

#### OllamaProvider

```python
# src/zettelforge/llm_providers/ollama_provider.py

class OllamaProvider:
    """Ollama HTTP API provider."""

    name = "ollama"

    def __init__(self, model: str = "", url: str = "", **kwargs):
        self._model = model or "qwen2.5:3b"
        self._url = url or "http://localhost:11434"

    def generate(self, prompt, max_tokens=400, temperature=0.1,
                 system=None, json_mode=False):
        import ollama
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs = {
            "model": self._model,
            "messages": messages,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            kwargs["format"] = "json"
        response = ollama.chat(**kwargs)
        return response["message"]["content"].strip()
```

#### OpenAICompatProvider

This is the highest-value addition. It covers OpenAI, Azure OpenAI, vLLM, LiteLLM, TGI, and any server exposing `/v1/chat/completions`.

```python
# src/zettelforge/llm_providers/openai_compat_provider.py

class OpenAICompatProvider:
    """
    OpenAI-compatible /v1/chat/completions provider.

    Works with: OpenAI, Azure OpenAI, vLLM, LiteLLM, Ollama (OpenAI mode),
    Together AI, Groq, Fireworks, any server with /v1/chat/completions.
    """

    name = "openai_compat"

    def __init__(self, model: str = "", url: str = "", api_key: str = "",
                 timeout: float = 60.0, max_retries: int = 2, **kwargs):
        self._model = model or "gpt-4o-mini"
        self._base_url = url.rstrip("/") if url else "https://api.openai.com/v1"
        self._api_key = api_key  # Resolved from env var reference before reaching here
        self._timeout = timeout
        self._max_retries = max_retries

    def generate(self, prompt, max_tokens=400, temperature=0.1,
                 system=None, json_mode=False):
        import httpx

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = httpx.post(
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers=headers,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self._max_retries:
                    import time
                    time.sleep(2 ** attempt)
            except httpx.HTTPStatusError as e:
                last_error = e
                # Only retry on 429 (rate limit) and 5xx (server error)
                if e.response.status_code == 429 or e.response.status_code >= 500:
                    if attempt < self._max_retries:
                        import time
                        retry_after = e.response.headers.get("Retry-After")
                        delay = int(retry_after) if retry_after else 2 ** attempt
                        time.sleep(delay)
                    continue
                # 4xx (except 429) — fail immediately, not retryable
                raise

        _logger.error("openai_compat_failed", error=str(last_error),
                      attempts=self._max_retries + 1)
        raise last_error
```

Design notes on `openai_compat`:
- Uses `httpx` (already a core dependency) instead of the `openai` SDK. This means zero new dependencies for OpenAI support.
- `json_mode` maps to `response_format: {"type": "json_object"}`, which is supported by OpenAI, Azure OpenAI, vLLM, and most compatible servers.
- Retry with exponential backoff handles transient 429/500 errors.
- **Azure OpenAI is out of scope for Phase 2.** Azure requires `api-version` as a query parameter and uses `api-key` header (not `Authorization: Bearer`). A dedicated `azure_openai` provider or an Azure-aware subclass of `OpenAICompatProvider` will be added in a follow-up. The `openai_compat` provider works with standard OpenAI, vLLM, LiteLLM, Together AI, Groq, and any server using Bearer auth + standard `/v1/chat/completions`.

#### AnthropicProvider (Optional Extra)

```python
# src/zettelforge/llm_providers/anthropic_provider.py

class AnthropicProvider:
    """Anthropic Messages API provider (requires pip install zettelforge[anthropic])."""

    name = "anthropic"

    def __init__(self, model: str = "", api_key: str = "",
                 timeout: float = 60.0, max_retries: int = 2, **kwargs):
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "Anthropic provider requires the anthropic SDK. "
                "Install with: pip install zettelforge[anthropic]"
            ) from None
        self._model = model or "claude-sonnet-4-20250514"
        self._client = anthropic.Anthropic(
            api_key=api_key or None,  # Falls back to ANTHROPIC_API_KEY env var
            timeout=timeout,
            max_retries=max_retries,
        )

    def generate(self, prompt, max_tokens=400, temperature=0.1,
                 system=None, json_mode=False):
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        # Anthropic does not have a native json_mode. Instruct via system prompt.
        if json_mode and system:
            kwargs["system"] = system + "\n\nIMPORTANT: Respond with valid JSON only."
        elif json_mode:
            kwargs["system"] = "Respond with valid JSON only."

        response = self._client.messages.create(**kwargs)
        return response.content[0].text.strip()
```

Design notes on `anthropic`:
- Uses the native SDK rather than the Messages API via raw HTTP, because Anthropic's API differs enough from OpenAI-compat (different auth header, different request/response schema, no `response_format`) that raw HTTP would be fragile.
- `json_mode` is handled via system prompt instruction since Anthropic has no `response_format` parameter. This is the standard approach used by LangChain, LiteLLM, and others.
- The SDK is an optional dependency — `pip install zettelforge[anthropic]`.

#### MockProvider (Testing)

```python
# src/zettelforge/llm_providers/mock_provider.py

class MockProvider:
    """Mock provider for testing. Returns canned responses."""

    name = "mock"

    def __init__(self, responses: list[str] | None = None, **kwargs):
        self._responses = list(responses) if responses else ["mock response"]
        self._call_count = 0
        self.calls: list[dict] = []  # Records all calls for assertion

    def generate(self, prompt, max_tokens=400, temperature=0.1,
                 system=None, json_mode=False):
        self.calls.append({
            "prompt": prompt, "max_tokens": max_tokens,
            "temperature": temperature, "system": system,
            "json_mode": json_mode,
        })
        response = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return response
```

### Config Schema

The `llm:` section in `config.yaml` expands to support the new providers:

```yaml
# config.default.yaml — LLM section (new schema)

llm:
  # Provider name: "local", "ollama", "openai_compat", "anthropic", "mock"
  provider: local

  # Model identifier (meaning depends on provider)
  #   local:         HuggingFace repo ID (e.g., "Qwen/Qwen2.5-3B-Instruct-GGUF")
  #   ollama:        Ollama model tag (e.g., "qwen2.5:3b")
  #   openai_compat: Model name (e.g., "gpt-4o-mini", "gpt-4o")
  #   anthropic:     Model ID (e.g., "claude-sonnet-4-20250514")
  model: Qwen/Qwen2.5-3B-Instruct-GGUF

  # Base URL (provider-specific)
  #   local:         ignored
  #   ollama:        Ollama server URL (default: http://localhost:11434)
  #   openai_compat: API base URL (default: https://api.openai.com/v1)
  #   anthropic:     ignored (uses SDK default)
  url: ""

  # API key — supports env var references: ${OPENAI_API_KEY}
  # NEVER put raw API keys in config files checked into git.
  # Use env var references or set via environment directly.
  api_key: ""

  # Default generation temperature
  temperature: 0.1

  # Request timeout in seconds
  timeout: 60.0

  # Number of retries on transient failures (429, 500, timeout)
  max_retries: 2

  # Fallback provider name. If primary fails, try this provider.
  # Set to "" to disable fallback.
  # Default: "ollama" when primary is "local", "" otherwise.
  fallback: ""

  # Provider-specific extra parameters (passed as **kwargs to provider constructor)
  # Example for Azure OpenAI:
  #   extra:
  #     api_version: "2024-02-15-preview"
  # Example for local provider:
  #   extra:
  #     filename: "qwen2.5-3b-instruct-q4_k_m.gguf"
  #     n_ctx: 4096
  extra: {}
```

Example user configs:

```yaml
# OpenAI
llm:
  provider: openai_compat
  model: gpt-4o-mini
  api_key: ${OPENAI_API_KEY}

# Anthropic
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
  api_key: ${ANTHROPIC_API_KEY}

# Azure OpenAI
llm:
  provider: openai_compat
  model: gpt-4o  # deployment name
  url: https://myresource.openai.azure.com/openai/deployments/gpt-4o
  api_key: ${AZURE_OPENAI_KEY}
  extra:
    api_version: "2024-02-15-preview"

# vLLM / LiteLLM / any OpenAI-compatible server
llm:
  provider: openai_compat
  model: Qwen/Qwen2.5-72B-Instruct
  url: http://gpu-box:8000/v1

# Ollama (explicit, same as before)
llm:
  provider: ollama
  model: qwen3.5:9b
  url: http://localhost:11434

# Local GGUF (default, unchanged)
llm:
  provider: local
  model: Qwen/Qwen2.5-3B-Instruct-GGUF
  extra:
    filename: qwen2.5-3b-instruct-q4_k_m.gguf
    n_ctx: 4096
```

### Config Dataclass Changes

```python
# src/zettelforge/config.py — updated LLMConfig

@dataclass
class LLMConfig:
    provider: str = "local"          # Default for new installs (offline-first)
    model: str = "Qwen/Qwen2.5-3B-Instruct-GGUF"  # Default for local provider
    url: str = ""
    api_key: str = ""                # Supports ${ENV_VAR} references
    temperature: float = 0.1
    timeout: float = 60.0
    max_retries: int = 2
    fallback: str = "ollama"         # local -> ollama fallback preserved
    extra: dict = field(default_factory=dict)

# NOTE: Existing deployments may have config.yaml with provider: ollama
# and model: qwen3.5:9b. These are preserved — config.yaml overrides
# config.default.yaml. The defaults above are for NEW installs only.
# Existing env var ZETTELFORGE_LLM_PROVIDER=ollama continues to work.
```

### Env Var Reference Resolution

API keys in config must support `${ENV_VAR}` syntax so users never put raw keys in YAML:

```python
# src/zettelforge/config.py — new helper

import re

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_env_refs(value: str) -> str:
    """Replace ${VAR_NAME} references with environment variable values."""
    def replacer(match):
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            get_logger("zettelforge.config").warning(
                "env_var_not_found", var=var_name,
                hint=f"Set {var_name} in your environment"
            )
            return ""
        return env_value
    return _ENV_VAR_PATTERN.sub(replacer, value)
```

This is called during `_apply_yaml()` for the `llm.api_key` field specifically, and for any string value under `llm.extra`.

### Security: API Key Handling

1. **Never log API keys.** The `_resolve_env_refs()` function runs at config load time. The resolved key is stored in the `LLMConfig` dataclass but is excluded from any `__repr__` or structured log output. Add a `__repr__` override to `LLMConfig`:

```python
def __repr__(self):
    key_display = "'***'" if self.api_key else "''"
    return (
        f"LLMConfig(provider={self.provider!r}, model={self.model!r}, "
        f"url={self.url!r}, api_key={key_display}, "
        f"temperature={self.temperature}, timeout={self.timeout}, "
        f"max_retries={self.max_retries}, fallback={self.fallback!r})"
    )
```

2. **Env var overrides still work.** `ZETTELFORGE_LLM_API_KEY` environment variable is added to `_apply_env()` as the highest-priority source for `api_key`.

3. **Config validation at startup.** If `provider` is `anthropic` and `api_key` is empty after resolution, raise `ValueError` with a clear message: "API key required for provider 'anthropic'. Set ANTHROPIC_API_KEY or configure llm.api_key: ${ANTHROPIC_API_KEY}". For `openai_compat`, fail fast only when `url` points to `api.openai.com` (which always requires auth); skip validation for self-hosted endpoints like vLLM that may not require keys.

### Fallback Behavior

The current code silently falls back from `local` to `ollama` on failure. This RFC makes fallback explicit and configurable:

```python
# In the updated generate() function

def generate(prompt, max_tokens=400, temperature=0.1, system=None, json_mode=False):
    cfg = get_config().llm
    provider_name = cfg.provider

    try:
        provider = registry.get(provider_name, **_provider_kwargs(cfg))
        return provider.generate(prompt, max_tokens, temperature, system, json_mode)
    except (ImportError, ValueError, TypeError):
        # Configuration errors — not retryable, do not fall back
        raise
    except Exception:
        # Transient errors (network, timeout, rate limit) — try fallback
        _logger.debug("primary_provider_failed", provider=provider_name, exc_info=True)

    # Fallback
    fallback_name = cfg.fallback
    if not fallback_name:
        # Preserve backward compat: local -> ollama implicit fallback
        if provider_name == "local":
            fallback_name = "ollama"

    if fallback_name and fallback_name != provider_name:
        try:
            fallback = registry.get(fallback_name, **_fallback_kwargs(cfg))
            return fallback.generate(prompt, max_tokens, temperature, system, json_mode)
        except Exception:
            _logger.error("fallback_provider_failed", provider=fallback_name, exc_info=True)

    _logger.error("all_llm_providers_failed")
    return ""
```

Key decisions:
- Implicit `local -> ollama` fallback is preserved for backward compatibility.
- All other providers have no implicit fallback (explicit `fallback:` config required).
- `generate()` still returns `""` on total failure — callers already handle this.

### json_mode Mapping Per Provider

| Provider | json_mode Implementation |
|---|---|
| `local` | Not supported by llama-cpp-python `create_chat_completion`. Use system prompt instruction. |
| `ollama` | `format: "json"` parameter (existing behavior). |
| `openai_compat` | `response_format: {"type": "json_object"}`. Widely supported. |
| `anthropic` | System prompt suffix: "Respond with valid JSON only." |
| `mock` | Returns response as-is (test controls output). |

For `local`, update to use system prompt instruction when `json_mode=True`:

```python
if json_mode:
    json_instruction = "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanation."
    if system:
        system = system + json_instruction
    else:
        system = json_instruction
```

### File Layout

```
src/zettelforge/
  llm_client.py                          # MODIFIED — delegates to provider registry
  config.py                              # MODIFIED — expanded LLMConfig, env ref resolution
  llm_providers/                         # NEW directory
    __init__.py                          # Registers built-in providers
    base.py                              # LLMProvider protocol
    registry.py                          # Provider registry (singleton instances)
    local_provider.py                    # llama-cpp-python (from current _generate_local)
    ollama_provider.py                   # Ollama HTTP (from current _generate_ollama)
    openai_compat_provider.py            # OpenAI-compatible /v1/chat/completions
    anthropic_provider.py                # Anthropic native SDK
    mock_provider.py                     # Test mock
config.default.yaml                      # MODIFIED — expanded llm: section
pyproject.toml                           # MODIFIED — new optional extras
tests/
  test_llm_providers.py                  # NEW — unit tests for each provider
  test_llm_client.py                     # NEW — integration tests for generate() with mock
```

### Package Extras

```toml
# pyproject.toml additions

[project.optional-dependencies]
# Existing
local = ["llama-cpp-python>=0.3.0"]

# New cloud provider extras
anthropic = ["anthropic>=0.40.0"]
```

Note: `openai_compat` provider uses `httpx` (already a core dependency) and does NOT require the `openai` SDK. No `openai` extra is provided — ZettelForge does not import the OpenAI SDK.

### Extension Points: Third-Party Providers

Third-party packages can register providers via Python entry points:

```toml
# In a third-party package's pyproject.toml
[project.entry-points."zettelforge.llm_providers"]
my_provider = "my_package.provider:MyProvider"
```

The registry discovers and loads these at import time:

```python
# src/zettelforge/llm_providers/__init__.py

from zettelforge.llm_providers.registry import register
from zettelforge.llm_providers.local_provider import LocalProvider
from zettelforge.llm_providers.ollama_provider import OllamaProvider
from zettelforge.llm_providers.openai_compat_provider import OpenAICompatProvider
from zettelforge.llm_providers.mock_provider import MockProvider

# Register built-in providers
register("local", LocalProvider)
register("ollama", OllamaProvider)
register("openai_compat", OpenAICompatProvider)
register("mock", MockProvider)

# Register optional built-in providers (skip if SDK not installed)
try:
    from zettelforge.llm_providers.anthropic_provider import AnthropicProvider
    register("anthropic", AnthropicProvider)
except ImportError:
    pass

# Discover third-party providers via entry points
try:
    from importlib.metadata import entry_points
    for ep in entry_points(group="zettelforge.llm_providers"):
        try:
            provider_class = ep.load()
            register(ep.name, provider_class)
        except Exception:
            _logger.debug("third_party_provider_load_failed", entry_point=ep.name, exc_info=True)
except Exception:
    _logger.debug("entry_point_discovery_failed", exc_info=True)
```

## Implementation Plan

### Phase 1: Provider Infrastructure (non-breaking)

Create the provider protocol, registry, and refactor existing backends into provider classes. The public `generate()` function delegates to the registry but behavior is identical.

**Files created:**
- `src/zettelforge/llm_providers/__init__.py`
- `src/zettelforge/llm_providers/base.py`
- `src/zettelforge/llm_providers/registry.py`
- `src/zettelforge/llm_providers/local_provider.py`
- `src/zettelforge/llm_providers/ollama_provider.py`
- `src/zettelforge/llm_providers/mock_provider.py`
- `tests/test_llm_providers.py`

**Files modified:**
- `src/zettelforge/llm_client.py` — Rewrite internals to use registry; keep `generate()` signature identical
- `src/zettelforge/config.py` — Expand `LLMConfig` with new fields, add `_resolve_env_refs()`, add `__repr__` override

**Validation:** All existing tests pass. `generate()` with `provider: local` and `provider: ollama` produces identical results.

### Phase 2: OpenAI-Compatible Provider

Add the `openai_compat` provider. This single provider covers OpenAI, Azure OpenAI, vLLM, LiteLLM, Together AI, Groq, and any `/v1/chat/completions` endpoint.

**Files created:**
- `src/zettelforge/llm_providers/openai_compat_provider.py`

**Files modified:**
- `src/zettelforge/llm_providers/__init__.py` — Register `openai_compat`
- `config.default.yaml` — Expanded `llm:` section with examples
- `pyproject.toml` — Add `openai` optional extra

**Validation:** Unit tests with `MockProvider` verifying request construction. Integration test against a local vLLM or Ollama in OpenAI-compat mode.

### Phase 3: Anthropic Provider

Add the native Anthropic SDK provider.

**Files created:**
- `src/zettelforge/llm_providers/anthropic_provider.py`

**Files modified:**
- `src/zettelforge/llm_providers/__init__.py` — Conditional registration
- `pyproject.toml` — Add `anthropic` and `cloud` optional extras

**Validation:** Unit tests with mocked SDK client. Integration test with real API key (CI secret).

### Phase 4: Config, Docs, Entry Points

- Add env var reference resolution (`${VAR}` syntax) to config loader
- Add `ZETTELFORGE_LLM_API_KEY` env var override in `_apply_env()`
- Add entry point discovery for third-party providers
- Update `config.default.yaml` with full documentation of new `llm:` schema
- Add env var override for `ZETTELFORGE_LLM_TIMEOUT`, `ZETTELFORGE_LLM_MAX_RETRIES`, `ZETTELFORGE_LLM_FALLBACK`

**Files modified:**
- `src/zettelforge/config.py` — `_resolve_env_refs()`, expanded `_apply_env()`
- `config.default.yaml` — Full documentation update

## Migration

### Existing users with default config (local provider)

**No changes required.** The default `provider: local` with the same model defaults produces identical behavior. The implicit `local -> ollama` fallback is preserved.

### Existing users with `provider: ollama` in config.yaml

**No changes required.** The `ollama` provider is a built-in with identical behavior.

### Existing users with env var overrides

All existing env vars continue to work:
- `ZETTELFORGE_LLM_PROVIDER` — maps to `llm.provider`
- `ZETTELFORGE_LLM_MODEL` — maps to `llm.model`
- `ZETTELFORGE_LLM_URL` — maps to `llm.url`
- `ZETTELFORGE_OLLAMA_MODEL` — deprecated but still honored (falls back to `ZETTELFORGE_LLM_MODEL`)

New env vars added:
- `ZETTELFORGE_LLM_API_KEY` — maps to `llm.api_key`
- `ZETTELFORGE_LLM_TIMEOUT` — maps to `llm.timeout`
- `ZETTELFORGE_LLM_MAX_RETRIES` — maps to `llm.max_retries`
- `ZETTELFORGE_LLM_FALLBACK` — maps to `llm.fallback`

### Callers of generate()

**Zero changes.** The 7 call sites (`fact_extractor.py`, `memory_updater.py`, `synthesis_generator.py`, `intent_classifier.py`, `note_constructor.py`, `entity_indexer.py`, `memory_evolver.py`) all import and call `generate()` with the same signature. They are not modified.

## Alternatives Considered

**Alternative 1: LiteLLM as a dependency.** LiteLLM provides a unified interface to 100+ LLM providers. Rejected because: (a) it pulls in ~20 transitive dependencies including `openai`, `tiktoken`, and `pydantic` v1 compat shims; (b) it is 50K+ lines of code for a feature we need ~200 lines for; (c) it conflicts with the minimal-dependency constraint; (d) it would make ZettelForge's LLM behavior dependent on a fast-moving third-party library's release cycle.

**Alternative 2: OpenAI SDK as the universal client.** The `openai` Python SDK can point at any OpenAI-compatible endpoint via `base_url`. Rejected because: (a) it adds a required dependency for what should be an optional feature; (b) it does not cover Anthropic's API; (c) `httpx` (already in core deps) can make the same HTTP calls without the SDK overhead.

**Alternative 3: Abstract base class instead of Protocol.** Using `abc.ABC` with `@abstractmethod`. Rejected because: (a) forces inheritance, which is unnecessary for a single-method interface; (b) inconsistent with the rest of the codebase which uses no ABCs; (c) `Protocol` with `runtime_checkable` provides the same validation benefits without coupling.

**Alternative 4: Provider config as separate YAML sections.** e.g., `openai:`, `anthropic:`, `ollama:` as top-level sections alongside `llm:`. Rejected because: (a) proliferates top-level config sections; (b) makes it unclear which provider is active; (c) a single `llm:` section with `provider:` discriminator is simpler and mirrors the existing `embedding:` pattern.

**Alternative 5: No fallback — fail fast.** Remove the implicit `local -> ollama` fallback entirely. Rejected because: (a) breaks backward compatibility for users who rely on the current silent fallback; (b) the fallback costs nothing when the primary succeeds; (c) explicit `fallback: ""` opt-out is available for users who want fail-fast.

## Open Questions

1. **Should Azure OpenAI be a separate provider or handled via `openai_compat` with `extra` params?** Current proposal uses `openai_compat` with `extra.api_version`. This works but Azure's auth can also use Entra ID tokens (not just API keys). A dedicated `azure_openai` provider might be cleaner long-term. Decision deferred to Phase 2 implementation.

2. **Should `generate()` accept a `provider` override parameter?** e.g., `generate(prompt, provider="anthropic")` to use a different provider per-call without changing global config. This would be useful for synthesis (use a powerful model) vs. classification (use a fast model). Intentionally excluded from this RFC to keep the API surface unchanged — can be proposed as a follow-up RFC if needed.

3. **Should we add streaming support?** The current `generate()` returns a complete string. Streaming would require a different return type (`Iterator[str]`), breaking the API contract. Excluded from this RFC. If needed, it should be a separate `generate_stream()` function.

4. **How should we handle provider-specific rate limiting?** OpenAI returns `Retry-After` headers on 429s. The current retry logic uses fixed exponential backoff. Should we respect `Retry-After`? Proposed: yes, in Phase 2, as an enhancement to `openai_compat_provider.py`.

5. **Should `ZETTELFORGE_OLLAMA_MODEL` be formally deprecated?** It currently sets the Ollama model independently of `ZETTELFORGE_LLM_MODEL`. With the unified config, `ZETTELFORGE_LLM_MODEL` should be the canonical env var for all providers. Proposed: honor `ZETTELFORGE_OLLAMA_MODEL` with a deprecation warning in logs, remove in v3.0.

## Rollout Strategy

1. **Phase 1** ships as a patch release (2.3.0) — pure refactor, no new providers, all tests pass identically.
2. **Phase 2** ships as 2.4.0 — adds `openai_compat` provider.
3. **Phase 3** ships as 2.5.0 — adds `anthropic` provider.
4. **Phase 4** ships alongside Phase 3 — config enhancements and documentation.
5. Azure OpenAI support follows as a separate RFC or Phase 5.

Each phase is independently shippable. If Phase 2 stalls, Phase 1 still delivers value (cleaner architecture, mock provider for testing, entry point extensibility).

## Decision

- **Status**: Draft
- **Date**: 2026-04-16
- **Decision Maker**: Patrick Roland
- **Rationale**: Pending approval. Adversarial review completed with 3 blockers (all fixed), 7 warnings (6 addressed, Azure deferred to follow-up), 5 nits (3 fixed).
