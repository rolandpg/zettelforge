# Format Stability Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement this plan.

**Goal:** Eliminate JSON parse failures across all 5 structured-output call sites by fixing the dropped system prompt in Ollama, adding `format="json"` mode, centralizing parse logic, and adding targeted retry on the two highest-damage sites.

**Architecture:** A new `json_parse.py` module becomes the single parse entry point for all LLM JSON extraction. The `llm_client.generate()` function gains a `json_mode` parameter that flows through to `ollama.generate(format="json")` for the Ollama backend and `response_format` for the local backend. Two critical sites (memory_updater, entity_indexer) get a single retry with bumped temperature and forced JSON mode on first parse failure.

**Tech Stack:** Python 3.10+, ollama Python SDK, llama-cpp-python (optional), structlog, pytest

---

### Task 1: Create shared `json_parse.py` utility
**Files:**
- Create: `src/zettelforge/json_parse.py`
- Test: `tests/test_json_parse.py`

This task has zero dependencies and is the foundation for Tasks 3 and 4.

- [ ] Step 1: Create `src/zettelforge/json_parse.py` with the `extract_json` function and parse stats counter.

```python
"""
Shared JSON extraction from LLM output.

Handles markdown code fences, surrounding prose, and malformed responses.
All structured-output call sites delegate here instead of inline regex+json.loads.
"""

import json
import re
from typing import Dict, Optional, Union

from zettelforge.log import get_logger

_logger = get_logger("zettelforge.json_parse")

_parse_stats: Dict[str, int] = {"success": 0, "failure": 0}


def get_parse_stats() -> Dict[str, int]:
    """Return a snapshot of cumulative parse success/failure counts."""
    return dict(_parse_stats)


def reset_parse_stats() -> None:
    """Reset parse counters (for testing)."""
    _parse_stats["success"] = 0
    _parse_stats["failure"] = 0


def extract_json(raw: str, expect: str = "object") -> Optional[Union[dict, list]]:
    """Extract JSON from LLM output, handling code fences and surrounding text.

    Args:
        raw: Raw LLM output string.
        expect: "object" to find {...} or "array" to find [...].

    Returns:
        Parsed dict/list, or None on failure.
    """
    if not raw or not raw.strip():
        _parse_stats["failure"] += 1
        return None

    text = raw.strip()

    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    text = re.sub(r"```(?:json)?\s*\n?", "", text).strip()

    # Find the target JSON structure
    if expect == "array":
        match = re.search(r"\[.*\]", text, re.DOTALL)
    else:
        match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        _parse_stats["failure"] += 1
        return None

    try:
        parsed = json.loads(match.group(0))
        _parse_stats["success"] += 1
        return parsed
    except json.JSONDecodeError:
        _parse_stats["failure"] += 1
        return None
```

- [ ] Step 2: Create `tests/test_json_parse.py` with unit tests covering all edge cases.

```python
"""Tests for json_parse.py — shared JSON extraction utility."""

import pytest

from zettelforge.json_parse import extract_json, get_parse_stats, reset_parse_stats


class TestExtractJson:
    def setup_method(self):
        reset_parse_stats()

    # --- Happy path ---

    def test_plain_object(self):
        assert extract_json('{"key": "value"}') == {"key": "value"}

    def test_plain_array(self):
        assert extract_json('[{"a": 1}]', expect="array") == [{"a": 1}]

    def test_code_fence_json(self):
        raw = '```json\n{"key": "value"}\n```'
        assert extract_json(raw) == {"key": "value"}

    def test_code_fence_no_lang(self):
        raw = '```\n[1, 2, 3]\n```'
        assert extract_json(raw, expect="array") == [1, 2, 3]

    def test_surrounding_prose(self):
        raw = 'Here is the result:\n{"answer": "yes"}\nDone.'
        assert extract_json(raw) == {"answer": "yes"}

    def test_array_with_surrounding_text(self):
        raw = 'The facts are:\n[{"fact": "x", "importance": 5}]\nEnd.'
        assert extract_json(raw, expect="array") == [{"fact": "x", "importance": 5}]

    # --- Failure cases ---

    def test_empty_string(self):
        assert extract_json("") is None

    def test_none_input(self):
        assert extract_json(None) is None

    def test_no_json(self):
        assert extract_json("No JSON here at all.") is None

    def test_invalid_json(self):
        assert extract_json("{key: value}") is None

    def test_wrong_expect(self):
        # Looking for array but only object present
        assert extract_json('{"key": 1}', expect="array") is None

    # --- Stats tracking ---

    def test_stats_success(self):
        extract_json('{"a": 1}')
        assert get_parse_stats() == {"success": 1, "failure": 0}

    def test_stats_failure(self):
        extract_json("no json")
        assert get_parse_stats() == {"success": 0, "failure": 1}

    def test_stats_accumulate(self):
        extract_json('{"a": 1}')
        extract_json("bad")
        extract_json('[1]', expect="array")
        assert get_parse_stats() == {"success": 2, "failure": 1}
```

- [ ] Step 3: Run tests.

```bash
cd /home/rolandpg/zettelforge && python -m pytest tests/test_json_parse.py -v
```

**Commit:** `feat(json_parse): add shared JSON extraction utility with parse stats`

---

### Task 2: Fix Ollama system prompt bug + add `json_mode` parameter
**Files:**
- Modify: `src/zettelforge/llm_client.py`
- Test: `tests/test_llm_client.py`

This task has no code dependencies on Task 1 but must land before Task 4 (retry logic uses `json_mode`).

- [ ] Step 1: Add `json_mode: bool = False` parameter to the public `generate()` function (line 69-86). Pass it through to both backends.

Replace lines 69-100:

```python
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
        json_mode: If True, force JSON output format (Ollama: format="json").

    Returns:
        Generated text string.
    """
    provider = get_llm_provider()

    if provider == "local":
        try:
            return _generate_local(prompt, max_tokens, temperature, system, json_mode)
        except Exception:
            _logger.debug("llamacpp_unavailable_trying_ollama", exc_info=True)

    # Ollama fallback
    try:
        return _generate_ollama(prompt, max_tokens, temperature, system, json_mode)
    except Exception:
        _logger.error("all_llm_backends_failed", exc_info=True)
        return ""
```

- [ ] Step 2: Fix `_generate_local` to accept and use `json_mode` (line 103-116). Add `response_format` when json_mode is True.

Replace lines 103-116:

```python
def _generate_local(
    prompt: str, max_tokens: int, temperature: float, system: Optional[str], json_mode: bool
) -> str:
    """Generate via in-process llama-cpp-python."""
    llm = _get_local_llm()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    output = llm.create_chat_completion(**kwargs)
    return output["choices"][0]["message"]["content"].strip()
```

- [ ] Step 3: Fix `_generate_ollama` to (a) accept and pass the `system` prompt and (b) use `format="json"` when `json_mode` is True (lines 119-129). This is the **critical bug fix** -- the current function drops the system prompt entirely.

Replace lines 119-129:

```python
def _generate_ollama(
    prompt: str, max_tokens: int, temperature: float, system: Optional[str], json_mode: bool
) -> str:
    """Generate via Ollama HTTP API."""
    import ollama

    model = os.environ.get("ZETTELFORGE_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    kwargs = {
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
```

- [ ] Step 4: Create `tests/test_llm_client.py` with unit tests that mock the ollama and llama_cpp backends.

```python
"""Tests for llm_client.py — system prompt passthrough and json_mode."""

from unittest.mock import MagicMock, patch

import pytest


class TestGenerateOllama:
    """Verify _generate_ollama passes system prompt and json format."""

    @patch("zettelforge.llm_client.get_llm_provider", return_value="ollama")
    @patch("zettelforge.llm_client._generate_ollama")
    def test_system_prompt_passed_to_ollama(self, mock_ollama, mock_provider):
        from zettelforge.llm_client import generate

        mock_ollama.return_value = '{"result": "ok"}'
        generate("test prompt", system="You are a JSON bot.", json_mode=True)

        mock_ollama.assert_called_once()
        args = mock_ollama.call_args
        # system and json_mode must be forwarded
        assert args[0][3] == "You are a JSON bot."  # system param
        assert args[0][4] is True  # json_mode param

    @patch("ollama.generate")
    def test_ollama_generate_receives_system_and_format(self, mock_gen):
        from zettelforge.llm_client import _generate_ollama

        mock_gen.return_value = {"response": '{"ok": true}'}
        _generate_ollama("prompt", 400, 0.1, "system prompt here", True)

        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["system"] == "system prompt here"
        assert call_kwargs["format"] == "json"

    @patch("ollama.generate")
    def test_ollama_no_system_no_format_when_disabled(self, mock_gen):
        from zettelforge.llm_client import _generate_ollama

        mock_gen.return_value = {"response": "plain text"}
        _generate_ollama("prompt", 400, 0.1, None, False)

        call_kwargs = mock_gen.call_args[1]
        assert "system" not in call_kwargs
        assert "format" not in call_kwargs
```

- [ ] Step 5: Run tests.

```bash
cd /home/rolandpg/zettelforge && python -m pytest tests/test_llm_client.py -v
```

**Commit:** `fix(llm_client): pass system prompt to Ollama and add json_mode parameter`

---

### Task 3: Refactor 5 parse sites to use `json_parse.py`
**Files:**
- Modify: `src/zettelforge/fact_extractor.py` (lines 65-87)
- Modify: `src/zettelforge/memory_updater.py` (lines 112-135)
- Modify: `src/zettelforge/entity_indexer.py` (lines 283-327)
- Modify: `src/zettelforge/note_constructor.py` (lines 126-157)
- Modify: `src/zettelforge/synthesis_generator.py` (lines 134-148)
- Test: `tests/test_parse_sites.py`

Depends on Task 1 (`json_parse.py` must exist).

- [ ] Step 1: Refactor `fact_extractor.py` -- replace `_parse_extraction_response` inline parse (lines 65-87) with `extract_json`.

Replace lines 1-9 imports to add json_parse:

```python
"""
Fact Extractor - Phase 1 of Mem0-style two-phase pipeline.

Extracts salient facts from raw content using LLM, with importance scoring.
Only the important facts proceed to storage, reducing redundancy and noise.
"""

import json
from dataclasses import dataclass
from typing import List

from zettelforge.json_parse import extract_json
from zettelforge.log import get_logger
```

Note: `re` import is removed since regex logic moves to `json_parse.py`.

Replace `_parse_extraction_response` method (lines 65-102):

```python
    def _parse_extraction_response(self, raw: str) -> List[ExtractedFact]:
        if not raw:
            return []

        parsed = extract_json(raw, expect="array")
        if parsed is None:
            _logger.warning("parse_failed", schema="fact_array", raw_output=raw[:200], fallback="empty_list")
            return []

        facts = []
        for item in parsed:
            if isinstance(item, dict):
                text = item.get("fact", "").strip()
                try:
                    importance = int(item.get("importance", 5))
                except (ValueError, TypeError):
                    importance = 5
                importance = max(1, min(10, importance))
                if text:
                    facts.append(ExtractedFact(text=text, importance=importance))

        facts.sort(key=lambda f: f.importance, reverse=True)
        return facts[: self.max_facts]
```

- [ ] Step 2: Refactor `memory_updater.py` -- replace `_parse_operation_response` inline parse (lines 112-135) with `extract_json`.

Replace lines 1-10 imports:

```python
"""
Memory Updater - Phase 2 of Mem0-style two-phase pipeline.

Compares new facts against existing notes and decides:
ADD (new), UPDATE (refine), DELETE (contradict), or NOOP (duplicate).
"""

import json
from enum import Enum
from typing import List, Optional, Tuple

from zettelforge.json_parse import extract_json
from zettelforge.log import get_logger
from zettelforge.note_schema import MemoryNote
```

Note: `re` import removed.

Replace `_parse_operation_response` method (lines 112-135):

```python
    def _parse_operation_response(self, raw: str) -> UpdateOperation:
        if not raw:
            return UpdateOperation.ADD

        parsed = extract_json(raw, expect="object")
        if parsed is None:
            _logger.warning(
                "parse_failed", schema="update_operation", raw_output=raw[:200], fallback="ADD"
            )
            return UpdateOperation.ADD

        try:
            op_str = parsed.get("operation", "ADD").upper()
            return UpdateOperation(op_str)
        except (ValueError, AttributeError):
            return UpdateOperation.ADD
```

- [ ] Step 3: Refactor `entity_indexer.py` -- replace `_parse_ner_output` inline parse (lines 283-327) with `extract_json`.

Add import at line 18 (after existing imports, before `_logger`):

```python
from zettelforge.json_parse import extract_json
```

Replace `_parse_ner_output` method (lines 283-327):

```python
    def _parse_ner_output(self, output: str, expected_types: List[str]) -> Dict[str, List[str]]:
        """Parse LLM NER output into normalized entity dict."""
        empty = {t: [] for t in expected_types}

        if not output or not output.strip():
            return empty

        parsed = extract_json(output, expect="object")
        if parsed is None:
            _logger.warning(
                "parse_failed", schema="ner_entities", raw_output=output[:200], fallback="empty_dict"
            )
            return empty

        if not isinstance(parsed, dict):
            return empty

        # Normalize values
        results: Dict[str, List[str]] = {}
        for etype in expected_types:
            values = parsed.get(etype, [])
            if isinstance(values, list):
                results[etype] = list(
                    set(
                        str(v).lower().strip()
                        for v in values
                        if v and isinstance(v, str) and len(v.strip()) > 1
                    )
                )
            else:
                results[etype] = []

        return results
```

- [ ] Step 4: Refactor `note_constructor.py` -- replace inline parse in `extract_causal_triples` (lines 126-157) with `extract_json`.

Add import at line 14 (after existing imports):

```python
from zettelforge.json_parse import extract_json
```

Replace the parse block inside `extract_causal_triples` (lines 126-142):

```python
            output = generate(prompt, max_tokens=300, temperature=0.1)

            parsed = extract_json(output, expect="array")
            if parsed is None:
                _logger.warning(
                    "parse_failed",
                    schema="causal_triples",
                    raw_output=output[:200],
                    fallback="empty_list",
                )
                return []
```

The rest of the method (lines 144-157, normalizing triples and adding note_id) stays the same. Remove the inline `import re` at line 136.

- [ ] Step 5: Refactor `synthesis_generator.py` -- replace bare `json.loads(raw)` at line 144 with `extract_json`. This is the **UNSAFE site** that currently has zero markdown stripping.

Add import at line 7 (after existing imports):

```python
from zettelforge.json_parse import extract_json
```

Replace lines 140-148 inside `_generate_synthesis`:

```python
        try:
            from zettelforge.llm_client import generate

            raw = generate(full_prompt, max_tokens=800, temperature=0.1, system=system_prompt)
            parsed = extract_json(raw, expect="object")
            if parsed is not None:
                return parsed
            _logger.warning(
                "parse_failed",
                schema="synthesis_response",
                raw_output=raw[:200],
                fallback="fallback_synthesis",
            )
            return self._fallback_synthesis(query, format)
        except Exception:
            return self._fallback_synthesis(query, format)
```

Remove the now-unreachable second `return self._fallback_synthesis(query, format)` that was at line 148.

- [ ] Step 6: Create `tests/test_parse_sites.py` to verify each refactored parser handles code-fenced input correctly.

```python
"""Tests for refactored parse sites -- verify they delegate to extract_json."""

from unittest.mock import patch

import pytest


class TestFactExtractorParsing:
    def test_code_fenced_array(self):
        from zettelforge.fact_extractor import FactExtractor

        fe = FactExtractor()
        raw = '```json\n[{"fact": "APT28 uses Cobalt Strike", "importance": 8}]\n```'
        facts = fe._parse_extraction_response(raw)
        assert len(facts) == 1
        assert facts[0].text == "APT28 uses Cobalt Strike"
        assert facts[0].importance == 8

    def test_empty_returns_empty(self):
        from zettelforge.fact_extractor import FactExtractor

        fe = FactExtractor()
        assert fe._parse_extraction_response("") == []


class TestMemoryUpdaterParsing:
    def test_code_fenced_object(self):
        from zettelforge.memory_updater import MemoryUpdater, UpdateOperation

        mu = MemoryUpdater.__new__(MemoryUpdater)
        raw = '```json\n{"operation": "UPDATE", "reason": "refines existing"}\n```'
        assert mu._parse_operation_response(raw) == UpdateOperation.UPDATE

    def test_garbage_defaults_to_add(self):
        from zettelforge.memory_updater import MemoryUpdater, UpdateOperation

        mu = MemoryUpdater.__new__(MemoryUpdater)
        assert mu._parse_operation_response("I don't know") == UpdateOperation.ADD


class TestEntityIndexerParsing:
    def test_code_fenced_ner(self):
        from zettelforge.entity_indexer import EntityExtractor

        ex = EntityExtractor()
        raw = '```json\n{"person": ["Alice"], "location": ["Paris"], "organization": [], "event": [], "activity": [], "temporal": []}\n```'
        types = ["person", "location", "organization", "event", "activity", "temporal"]
        result = ex._parse_ner_output(raw, types)
        assert "alice" in result["person"]
        assert "paris" in result["location"]


class TestSynthesisGeneratorParsing:
    @patch("zettelforge.llm_client.generate")
    def test_code_fenced_synthesis(self, mock_gen):
        from zettelforge.synthesis_generator import SynthesisGenerator

        mock_gen.return_value = '```json\n{"answer": "test", "confidence": 0.9, "sources": []}\n```'
        sg = SynthesisGenerator()
        result = sg._generate_synthesis("query", "context", "direct_answer")
        assert result["answer"] == "test"
```

- [ ] Step 7: Run tests.

```bash
cd /home/rolandpg/zettelforge && python -m pytest tests/test_parse_sites.py -v
```

**Commit:** `refactor(parsers): centralize JSON extraction through json_parse.py across 5 call sites`

---

### Task 4: Add single retry on 2 highest-damage sites
**Files:**
- Modify: `src/zettelforge/memory_updater.py` (method `decide`, lines 37-50)
- Modify: `src/zettelforge/entity_indexer.py` (method `extract_llm`, lines 247-281)
- Test: `tests/test_retry_logic.py`

Depends on Task 2 (`json_mode` parameter) and Task 3 (refactored parse methods).

- [ ] Step 1: Add retry logic to `memory_updater.py` in the `decide` method (lines 37-50).

Replace `decide` method:

```python
    def decide(self, fact_text: str, similar_notes: List[MemoryNote]) -> UpdateOperation:
        if not similar_notes:
            return UpdateOperation.ADD

        prompt = self._build_decision_prompt(fact_text, similar_notes)

        try:
            from zettelforge.llm_client import generate

            raw = generate(prompt, max_tokens=150, temperature=0.1)
            result = self._parse_operation_response(raw)

            # If parse failed (defaulted to ADD), retry once with stricter settings
            if result == UpdateOperation.ADD and raw and raw.strip():
                # Only retry if we got output but couldn't parse it
                from zettelforge.json_parse import extract_json

                if extract_json(raw, expect="object") is None:
                    _logger.info("retry_decide", reason="parse_failed_first_attempt")
                    retry_prompt = prompt + "\nRespond with valid JSON only."
                    raw = generate(
                        retry_prompt, max_tokens=150, temperature=0.3, json_mode=True
                    )
                    result = self._parse_operation_response(raw)

            return result
        except Exception:
            _logger.warning("llm_update_decision_failed_defaulting_add", exc_info=True)
            return UpdateOperation.ADD
```

- [ ] Step 2: Add retry logic to `entity_indexer.py` in the `extract_llm` method (lines 247-281).

Replace `extract_llm` method:

```python
    def extract_llm(self, text: str) -> Dict[str, List[str]]:
        """Extract conversational entities using LLM NER.

        Returns dict with person, location, organization, event, activity, temporal keys.
        Falls back to empty dicts on failure. Retries once on parse failure.
        """
        conversational_types = [
            "person",
            "location",
            "organization",
            "event",
            "activity",
            "temporal",
        ]
        empty = {t: [] for t in conversational_types}

        if len(text.strip()) < 10:
            return empty

        try:
            from zettelforge.llm_client import generate

            prompt = f"Extract named entities from this text:\n\n{text[:2000]}\n\nJSON:"
            output = generate(
                prompt,
                max_tokens=300,
                temperature=0.0,
                system=self.NER_SYSTEM_PROMPT,
            )

            result = self._parse_ner_output(output, conversational_types)

            # If parse returned all-empty and we got output, retry once
            if all(len(v) == 0 for v in result.values()) and output and output.strip():
                from zettelforge.json_parse import extract_json

                if extract_json(output, expect="object") is None:
                    _logger.info("retry_extract_llm", reason="parse_failed_first_attempt")
                    retry_prompt = prompt + "\nRespond with valid JSON only."
                    output = generate(
                        retry_prompt,
                        max_tokens=300,
                        temperature=0.3,
                        system=self.NER_SYSTEM_PROMPT,
                        json_mode=True,
                    )
                    result = self._parse_ner_output(output, conversational_types)

            return result

        except Exception:
            _logger.warning("llm_entity_extraction_failed", exc_info=True)
            return empty
```

- [ ] Step 3: Create `tests/test_retry_logic.py`.

```python
"""Tests for retry logic on memory_updater and entity_indexer."""

from unittest.mock import MagicMock, call, patch

import pytest


class TestMemoryUpdaterRetry:
    @patch("zettelforge.llm_client.generate")
    def test_retry_on_parse_failure(self, mock_gen):
        from zettelforge.memory_updater import MemoryUpdater, UpdateOperation
        from zettelforge.note_schema import Content, Embedding, MemoryNote, Metadata, Semantic

        # First call returns garbage, second returns valid JSON
        mock_gen.side_effect = [
            "I think the answer is UPDATE",
            '{"operation": "UPDATE", "reason": "refines existing"}',
        ]

        mu = MemoryUpdater.__new__(MemoryUpdater)
        mu.model = "test"
        mu.top_s = 3
        note = MemoryNote(
            id="n1",
            created_at="2026-01-01",
            updated_at="2026-01-01",
            content=Content(raw="existing fact"),
            semantic=Semantic(context="", keywords=[], tags=[], entities=[]),
            embedding=Embedding(vector=[], model="test"),
            metadata=Metadata(domain="cti", tier="A"),
        )

        result = mu.decide("new fact", [note])
        assert result == UpdateOperation.UPDATE
        assert mock_gen.call_count == 2
        # Second call should have json_mode=True
        assert mock_gen.call_args_list[1][1].get("json_mode") is True


class TestEntityExtractorRetry:
    @patch("zettelforge.llm_client.generate")
    def test_retry_on_parse_failure(self, mock_gen):
        from zettelforge.entity_indexer import EntityExtractor

        # First call returns garbage, second returns valid NER
        mock_gen.side_effect = [
            "The entities are Alice and Paris",
            '{"person": ["Alice"], "location": ["Paris"], "organization": [], "event": [], "activity": [], "temporal": []}',
        ]

        ex = EntityExtractor()
        result = ex.extract_llm("Alice went to Paris last Tuesday for a meeting")
        assert "alice" in result["person"]
        assert mock_gen.call_count == 2
        assert mock_gen.call_args_list[1][1].get("json_mode") is True
```

- [ ] Step 4: Run tests.

```bash
cd /home/rolandpg/zettelforge && python -m pytest tests/test_retry_logic.py -v
```

**Commit:** `feat(retry): add single retry with json_mode on memory_updater and entity_indexer parse failures`

---

### Task 5: Move `llama-cpp-python` to optional dependency
**Files:**
- Modify: `pyproject.toml` (line 36)
- Modify: `src/zettelforge/llm_client.py` (lines 48-63, the `_get_local_llm` function)
- Test: `tests/test_llm_client.py` (extend)

Independent of Tasks 1-4. Can be done in parallel.

- [ ] Step 1: In `pyproject.toml`, move `llama-cpp-python>=0.3.0` from `dependencies` (line 36) to a new optional dependency group.

Remove from line 36 in dependencies:
```toml
    "llama-cpp-python>=0.3.0",
```

Add new optional group after the existing `extensions` group (after line 47):

```toml
# Local LLM (llama-cpp-python for in-process GGUF inference)
local = ["llama-cpp-python>=0.3.0"]
```

- [ ] Step 2: In `llm_client.py`, make the `_get_local_llm` function (lines 48-63) handle `ImportError` gracefully so that when `llama-cpp-python` is not installed, the function raises a clear error that triggers the Ollama fallback.

Replace lines 48-63:

```python
def _get_local_llm():
    """Get or create the local Llama model (singleton).

    Raises ImportError if llama-cpp-python is not installed.
    """
    global _llm
    if _llm is None:
        with _llm_lock:
            if _llm is None:
                try:
                    from llama_cpp import Llama
                except ImportError:
                    raise ImportError(
                        "llama-cpp-python is not installed. "
                        "Install it with: pip install zettelforge[local]"
                    )

                _llm = Llama.from_pretrained(
                    repo_id=get_llm_model(),
                    filename=os.environ.get("ZETTELFORGE_LLM_FILENAME", DEFAULT_LLM_FILENAME),
                    n_ctx=4096,
                    n_gpu_layers=0,
                    verbose=False,
                )
    return _llm
```

- [ ] Step 3: Run existing tests to verify no regressions.

```bash
cd /home/rolandpg/zettelforge && python -m pytest tests/ -v
```

**Commit:** `build(deps): move llama-cpp-python to optional [local] dependency group`

---

### Task 6: Add causal relation validation in `note_constructor.py`
**Files:**
- Modify: `src/zettelforge/note_constructor.py` (inside `extract_causal_triples`, after parse, around line 146)
- Test: `tests/test_note_constructor.py`

Independent of all other tasks.

- [ ] Step 1: Add validation that the extracted `relation` field is in `CAUSAL_RELATIONS`. Invalid relations get dropped with a warning. Insert validation inside the triple normalization loop (after line 150 in the current code, which will shift after Task 3 edits).

After the triple normalization loop that builds the `triples` list, add a filter:

```python
            # Validate relations against allowed list
            valid_triples = []
            for t in triples:
                relation = t.get("relation", "").strip().lower()
                if relation in self.CAUSAL_RELATIONS:
                    t["relation"] = relation  # normalize to lowercase
                    valid_triples.append(t)
                else:
                    _logger.warning(
                        "invalid_causal_relation",
                        relation=relation,
                        subject=t.get("subject", ""),
                        object=t.get("object", ""),
                        allowed=self.CAUSAL_RELATIONS,
                    )
            triples = valid_triples
```

This goes right before the `# Add note_id to each triple` block.

- [ ] Step 2: Create `tests/test_note_constructor.py`.

```python
"""Tests for note_constructor.py -- causal relation validation."""

import json
from unittest.mock import patch

import pytest


class TestCausalRelationValidation:
    @patch("zettelforge.llm_client.generate")
    def test_valid_relations_pass(self, mock_gen):
        from zettelforge.note_constructor import NoteConstructor

        mock_gen.return_value = json.dumps([
            {"subject": "APT28", "relation": "uses", "object": "Cobalt Strike"},
            {"subject": "APT28", "relation": "targets", "object": "NATO"},
        ])
        nc = NoteConstructor()
        triples = nc.extract_causal_triples("APT28 uses Cobalt Strike to target NATO", "n1")
        assert len(triples) == 2
        assert all(t["relation"] in nc.CAUSAL_RELATIONS for t in triples)

    @patch("zettelforge.llm_client.generate")
    def test_invalid_relation_filtered(self, mock_gen):
        from zettelforge.note_constructor import NoteConstructor

        mock_gen.return_value = json.dumps([
            {"subject": "APT28", "relation": "uses", "object": "Cobalt Strike"},
            {"subject": "APT28", "relation": "hacks", "object": "Pentagon"},
        ])
        nc = NoteConstructor()
        triples = nc.extract_causal_triples("APT28 uses Cobalt Strike and hacks Pentagon", "n1")
        assert len(triples) == 1
        assert triples[0]["relation"] == "uses"

    @patch("zettelforge.llm_client.generate")
    def test_relation_normalized_to_lowercase(self, mock_gen):
        from zettelforge.note_constructor import NoteConstructor

        mock_gen.return_value = json.dumps([
            {"subject": "APT28", "relation": "Uses", "object": "Cobalt Strike"},
        ])
        nc = NoteConstructor()
        triples = nc.extract_causal_triples("APT28 uses Cobalt Strike", "n1")
        assert len(triples) == 1
        assert triples[0]["relation"] == "uses"

    @patch("zettelforge.llm_client.generate")
    def test_all_invalid_returns_empty(self, mock_gen):
        from zettelforge.note_constructor import NoteConstructor

        mock_gen.return_value = json.dumps([
            {"subject": "X", "relation": "destroys", "object": "Y"},
        ])
        nc = NoteConstructor()
        triples = nc.extract_causal_triples("X destroys Y", "n1")
        assert len(triples) == 0
```

- [ ] Step 3: Run tests.

```bash
cd /home/rolandpg/zettelforge && python -m pytest tests/test_note_constructor.py -v
```

**Commit:** `fix(constructor): validate causal relations against CAUSAL_RELATIONS allowlist`

---

### Task 7: Full test suite and integration verification
**Files:**
- Test: all `tests/test_*.py` files from Tasks 1-6
- No new code

Depends on all previous tasks being complete.

- [ ] Step 1: Run the full test suite.

```bash
cd /home/rolandpg/zettelforge && python -m pytest tests/ -v --tb=short
```

- [ ] Step 2: Run ruff linting to ensure no style violations.

```bash
cd /home/rolandpg/zettelforge && python -m ruff check src/zettelforge/json_parse.py src/zettelforge/llm_client.py src/zettelforge/fact_extractor.py src/zettelforge/memory_updater.py src/zettelforge/entity_indexer.py src/zettelforge/note_constructor.py src/zettelforge/synthesis_generator.py
```

- [ ] Step 3: Run mypy type checking.

```bash
cd /home/rolandpg/zettelforge && python -m mypy src/zettelforge/json_parse.py src/zettelforge/llm_client.py --ignore-missing-imports
```

- [ ] Step 4: Verify parse stats are accessible from the CLI/API (manual check).

```bash
cd /home/rolandpg/zettelforge && python -c "from zettelforge.json_parse import get_parse_stats; print(get_parse_stats())"
```

**Commit:** No commit for this task -- it is a verification gate.

---

## Dependency Graph

```
Task 1 (json_parse.py) ─────────┐
                                 ├──> Task 3 (refactor 5 sites) ──┐
Task 2 (llm_client fixes) ──────┤                                 ├──> Task 7 (full test)
                                 └──> Task 4 (retry logic) ───────┤
Task 5 (optional dep) ────────────────────────────────────────────┤
Task 6 (causal validation) ───────────────────────────────────────┘
```

Tasks 1, 2, 5, 6 can all run in parallel.
Task 3 depends on Task 1.
Task 4 depends on Tasks 2 and 3.
Task 7 depends on all prior tasks.

## Files Changed Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `src/zettelforge/json_parse.py` | Create | ~55 lines |
| `src/zettelforge/llm_client.py` | Modify | Lines 48-63, 69-100, 103-116, 119-129 |
| `src/zettelforge/fact_extractor.py` | Modify | Lines 1-9 (imports), 65-102 (parser) |
| `src/zettelforge/memory_updater.py` | Modify | Lines 1-10 (imports), 37-50 (decide), 112-135 (parser) |
| `src/zettelforge/entity_indexer.py` | Modify | Line 18 (import), 247-281 (extract_llm), 283-327 (parser) |
| `src/zettelforge/note_constructor.py` | Modify | Line 14 (import), 126-157 (parse block), ~150 (validation) |
| `src/zettelforge/synthesis_generator.py` | Modify | Line 7 (import), 140-148 (parser) |
| `pyproject.toml` | Modify | Line 36 (remove dep), line ~48 (add optional group) |
| `tests/test_json_parse.py` | Create | ~65 lines |
| `tests/test_llm_client.py` | Create | ~55 lines |
| `tests/test_parse_sites.py` | Create | ~65 lines |
| `tests/test_retry_logic.py` | Create | ~75 lines |
| `tests/test_note_constructor.py` | Create | ~60 lines |

**Estimated total:** ~150 lines of production code, ~320 lines of tests.
