"""LLMProvider protocol — the contract every LLM backend implements.

Phase 1 of RFC-002. See docs/rfcs/RFC-002-universal-llm-provider.md.

Using ``typing.Protocol`` (PEP 544) rather than an abstract base class so
third-party providers only need duck-type compatibility — no forced
inheritance. ``runtime_checkable`` enables ``isinstance`` validation at
registration time.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """All LLM providers must implement this protocol.

    Attributes:
        name: Short provider identifier (e.g., ``"local"``, ``"ollama"``,
            ``"openai_compat"``, ``"anthropic"``, ``"mock"``). Used as the
            registry key.
    """

    name: str

    def generate(
        self,
        prompt: str,
        max_tokens: int = 400,
        temperature: float = 0.1,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """Generate text from a prompt.

        Providers MUST return an empty string on recoverable failure so
        callers can short-circuit cleanly. Configuration errors (missing
        SDK, missing API key, etc.) SHOULD raise so they surface during
        startup rather than failing silently per call.
        """
        ...
