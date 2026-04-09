"""
Prospective Indexer — Kumiho-style Future-Query Indexing

At remember() time, generates 1-3 future-scenario implications per note.
These are stored in MemoryNote.semantic.prospective_index and enable
queries like "what will APT28 do next?" to match notes about current
APT28 activity even when the note doesn't directly mention future actions.

Architecture:
  - generate_prospective_index(text, domain) -> List[str]
  - Called from NoteConstructor.construct() for cti-domain notes
  - Matches at recall() time via cosine similarity against a separate
    in-memory index of prospective entries (no extra DB needed)

Reference: Kumiho (arXiv:2603.17244) — "Graph-Native Cognitive Memory for AI Agents"
            Park, Young Bin (Mar 2026)
"""
import json
import re
from typing import List

import ollama


def generate_prospective_index(
    text: str,
    domain: str,
    model: str = "qwen2.5:3b",
    max_entries: int = 3,
) -> List[str]:
    """
    Generate future-scenario implications for a note.

    Given a CTI note, the LLM generates statements about what the information
    implies for future situations, even when the original text is historical.

    Examples:
      Input: "APT28 has shifted to edge devices as initial access"
      Output: [
        "APT28 future campaigns will prioritize edge device exploitation",
        "Organizations should audit edge device security posture",
        "APT28 TTPs will shift away from traditional server access"
      ]

    Args:
        text: Raw note content.
        domain: MemoryNote metadata domain (prospecting only runs for cti).
        model: Ollama model for generation.
        max_entries: Maximum implications to generate (default 3).

    Returns:
        List of prospective implication strings.
    """
    if domain != "cti":
        return []

    prompt = _build_prospective_prompt(text, max_entries)

    try:
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={"temperature": 0.3, "num_predict": 400},
        )
        raw = response.get("response", "").strip()
        entries = _parse_prospective_response(raw, max_entries)
        return entries
    except Exception as e:
        print(f"[ProspectiveIndexer] Generation failed: {e}")
        return []


def _build_prospective_prompt(text: str, max_entries: int) -> str:
    return f"""You are a threat intelligence analyst generating forward-looking implications from intelligence data.

Given a piece of intelligence, generate {max_entries} implications about what this means for FUTURE threats, campaigns, or defensive priorities. These are NOT quotes from the text — they are what the information predicts or implies.

Rules:
- Each implication should be a concise statement (under 25 words)
- Focus on: future actor behavior, likely next moves, emerging threat trends
- If the text is historical (e.g., "APT28 used Mimikatz in 2021"), generate implications about what historical patterns suggest for future behavior
- Do NOT repeat the input text. Generate NEW forward-looking statements.
- If the text is not CTI-related (e.g., casual conversation), return an empty array.

Intelligence:
{text[:1500]}

Output as JSON array of strings:
["implication 1", "implication 2", ...]
JSON:"""


def _parse_prospective_response(raw: str, max_entries: int) -> List[str]:
    """Parse LLM JSON output into a list of strings."""
    if not raw:
        return []

    # Strip markdown code fences first
    if raw.startswith("```"):
        parts = raw.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("["):
                raw = stripped
                break

    # Use raw_decode to parse JSON even with trailing text (e.g., "].")
    try:
        parsed, end = json.JSONDecoder().raw_decode(raw)
    except (json.JSONDecodeError, ValueError):
        return []

    if not isinstance(parsed, list):
        return []

    entries = []
    for item in parsed[:max_entries]:
        if isinstance(item, str) and item.strip():
            entries.append(item.strip()[:200])
    return entries


# === Prospective Retrieval ===

class ProspectiveRetriever:
    """
    In-memory prospective index for fast future-query matching.

    At recall() time, we embed the user's query and search it against
    the prospective_index entries stored in recent notes. Notes whose
    prospective entries match the query are surfaced, even if the
    original note content doesn't match the query.

    This is a read-only index rebuilt from MemoryStore on init.
    """

    def __init__(self, memory_store):
        self.store = memory_store
        self._entries: List[dict] = []  # [{note_id, entry, vector}]
        self._built = False

    def build_index(self, embedding_model: str = "nomic-embed-text-v2-moe") -> int:
        """Build in-memory index from all notes in store. Returns entry count."""
        self._entries = []

        try:
            import ollama
        except ImportError:
            return 0

        try:
            for note in self.store.iterate_notes():
                for entry in note.semantic.prospective_index:
                    if not entry.strip():
                        continue
                    try:
                        emb_response = ollama.embeddings(
                            model=embedding_model,
                            prompt=entry,
                        )
                        vector = emb_response.get("embedding", [])
                        if vector:
                            self._entries.append({
                                "note_id": note.id,
                                "entry": entry,
                                "vector": vector,
                            })
                    except Exception:
                        # Skip embedding failures gracefully
                        pass

        except Exception as e:
            print(f"[ProspectiveRetriever] build_index failed: {e}")

        self._built = True
        return len(self._entries)

    def retrieve(
        self,
        query: str,
        note_lookup,
        top_k: int = 5,
        score_threshold: float = 0.65,
    ) -> List[tuple]:
        """
        Retrieve notes whose prospective entries match the query.

        Args:
            query: User's question (e.g., "what will APT28 do next")
            note_lookup: callable(note_id) -> MemoryNote
            top_k: Maximum notes to return
            score_threshold: Minimum cosine similarity to return

        Returns:
            List of (note, score) tuples sorted by descending similarity.
        """
        if not self._built:
            self.build_index()

        if not self._entries:
            return []

        try:
            import ollama
            import numpy as np
        except ImportError:
            return []

        try:
            q_emb = ollama.embeddings(
                model="nomic-embed-text-v2-moe",
                prompt=query,
            ).get("embedding", [])
        except Exception:
            return []

        if not q_emb:
            return []

        q_vec = np.array(q_emb)
        results = []

        for entry in self._entries:
            v = np.array(entry["vector"])
            norm = np.linalg.norm(q_vec) * np.linalg.norm(v)
            if norm == 0:
                continue
            score = float(np.dot(q_vec, v) / norm)

            if score >= score_threshold:
                note = note_lookup(entry["note_id"])
                if note:
                    results.append((note, score))

        # Sort by score descending, deduplicate by note_id (keep highest)
        seen = set()
        deduped = []
        for note, score in sorted(results, key=lambda x: -x[1]):
            if note.id not in seen:
                seen.add(note.id)
                deduped.append((note, score))

        return deduped[:top_k]
