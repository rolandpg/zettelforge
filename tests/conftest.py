"""Shared test fixtures for ZettelForge test suite."""
import os
import pytest
from zettelforge.edition import reset_edition


# Skip native libraries in CI to prevent SIGSEGV/SIGABRT on GitHub Actions runners:
# - fastembed/ONNX Runtime segfaults on runner CPU → use deterministic mock embeddings
# - llama-cpp-python aborts when model not available → use ollama (fails gracefully to "")
if os.environ.get("CI") or not os.environ.get("ZETTELFORGE_EMBEDDING_PROVIDER"):
    os.environ.setdefault("ZETTELFORGE_EMBEDDING_PROVIDER", "mock")
    os.environ.setdefault("ZETTELFORGE_LLM_PROVIDER", "ollama")


@pytest.fixture
def enable_enterprise():
    """Temporarily enable Enterprise edition for tests that need it.

    Usage:
        def test_something(enable_enterprise):
            # Enterprise features are available here
            ...
    """
    os.environ["THREATENGRAM_LICENSE_KEY"] = "TG-1234-5678-9abc-def0"
    reset_edition()
    yield
    del os.environ["THREATENGRAM_LICENSE_KEY"]
    reset_edition()
