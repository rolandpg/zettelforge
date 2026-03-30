#!/usr/bin/env python3
"""
Enhanced MemoryStore - Hermes-inspired memory with bounded limits and injection scanning

Features:
- Bounded character limits prevent context overflow
- § delimiter separates entries
- Frozen snapshot pattern (stable system prompt, live disk state)
- Content injection scanning for all memory entries
- File locking for concurrent access safety

Usage:
    from memory.enhanced_memory import EnhancedMemoryStore
    store = EnhancedMemoryStore()
    store.load()
    
    # Get frozen snapshot for system prompt
    snapshot = store.get_snapshot()
    
    # Add entry (scanned automatically)
    store.add("memory", "New thing I learned...")
    
    # Read entries
    entries = store.read("memory")
"""

import fcntl
import logging
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default limits (characters, not tokens)
DEFAULT_MEMORY_LIMIT = 2200
DEFAULT_USER_LIMIT = 1375

# Entry delimiter
ENTRY_DELIMITER = "\n§\n"

# Section headers for files
MEMORY_HEADER = "# MEMORY.md - Long-Term Memory"
USER_HEADER = "# USER.md - About You"

# ============================================================================
# INJECTION SCANNING
# ============================================================================

_INJECTION_PATTERNS = [
    (r'ignore previous', "prompt_injection"),
    (r'you are now', "role_hijack"),
    (r'curl.*KEY', "exfil_curl"),
    (r'wget.*KEY', "exfil_wget"),
    (r'authorized_keys', "ssh_backdoor"),
]

_INVISIBLE_CHARS = {
    '\u200b',  # Zero width space
    '\u200c',  # Zero width non-joiner
    '\u200d',  # Zero width joiner
    '\u2060',  # Word joiner
    '\ufeff',  # BOM
    '\u202a',  # Left-to-right embedding
    '\u202b',  # Right-to-left embedding
    '\u202c',  # Pop directional formatting
    '\u202d',  # Left-to-right override
    '\u202e',  # Right-to-left override
}


def scan_content(content: str) -> Optional[str]:
    """
    Scan content for injection/exfiltration patterns.
    Returns error message if blocked, None if clean.
    """
    if not content:
        return None
    
    # Check invisible unicode
    for char in _INVISIBLE_CHARS:
        if char in content:
            return f"Blocked: invisible unicode U+{ord(char):04X} detected"
    
    # Check threat patterns
    for pattern, threat_type in _INJECTION_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return f"Blocked: threat pattern '{threat_type}' detected"
    
    return None


# ============================================================================
# FILE LOCKING
# ============================================================================

@contextmanager
def file_lock(path: Path):
    """Exclusive file lock for read-modify-write safety."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()


# ============================================================================
# ENHANCED MEMORY STORE
# ============================================================================

class EnhancedMemoryStore:
    """
    Bounded curated memory with file persistence.
    
    Maintains two parallel states:
      - _snapshot: frozen at load time, used for system prompt injection
      - memory_entries / user_entries: live state, mutated by operations
    
    The snapshot NEVER changes during a session. This ensures:
      - Stable prefix cache (no re-tokenizing mid-session)
      - Consistent agent behavior within session
      - No oscillation from memory edits
    """
    
    def __init__(
        self,
        memory_dir: Optional[Path] = None,
        memory_char_limit: int = DEFAULT_MEMORY_LIMIT,
        user_char_limit: int = DEFAULT_USER_LIMIT,
    ):
        """
        Initialize EnhancedMemoryStore.
        
        Args:
            memory_dir: Directory for memory files (default: workspace/memory/)
            memory_char_limit: Max chars for MEMORY.md entries
            user_char_limit: Max chars for USER.md entries
        """
        if memory_dir is None:
            # Default to workspace/memory/
            workspace = Path(__file__).parent.parent
            memory_dir = workspace / "memory"
        
        self.memory_dir = Path(memory_dir)
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit
        
        # Live entry state
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
        
        # Frozen snapshot (captured at load, never changes)
        self._snapshot: Dict[str, str] = {"memory": "", "user": ""}
        
        # Track if loaded
        self._loaded = False
    
    @property
    def memory_path(self) -> Path:
        return self.memory_dir / "MEMORY.md"
    
    @property
    def user_path(self) -> Path:
        return self.memory_dir / "USER.md"
    
    def load(self) -> None:
        """Load entries from disk and capture frozen snapshot."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Load entries
        self.memory_entries = self._read_file(self.memory_path)
        self.user_entries = self._read_file(self.user_path)
        
        # Deduplicate (preserve order, keep first)
        self.memory_entries = list(dict.fromkeys(self.memory_entries))
        self.user_entries = list(dict.fromkeys(self.user_entries))
        
        # Capture frozen snapshot
        self._snapshot = {
            "memory": self._render_block("memory", self.memory_entries),
            "user": self._render_block("user", self.user_entries),
        }
        
        self._loaded = True
        logger.info(
            "EnhancedMemoryStore loaded: %d memory entries, %d user entries",
            len(self.memory_entries),
            len(self.user_entries)
        )
    
    def get_snapshot(self) -> Dict[str, str]:
        """Get frozen snapshot for system prompt injection."""
        if not self._loaded:
            self.load()
        return self._snapshot.copy()
    
    # =========================================================================
    # File Operations
    # =========================================================================
    
    def _read_file(self, path: Path) -> List[str]:
        """Read entries from a §-delimited file."""
        if not path.exists():
            return []
        
        content = path.read_text()
        
        # Strip header if present
        for header in (MEMORY_HEADER, USER_HEADER):
            if content.startswith(header):
                # Find end of first line (header line)
                first_newline = content.find('\n')
                if first_newline > 0:
                    content = content[first_newline + 1:]
        
        # Split by delimiter, filter empty
        entries = [e.strip() for e in content.split(ENTRY_DELIMITER) if e.strip()]
        return entries
    
    def _write_file(self, path: Path, entries: List[str], header: str) -> None:
        """Write entries to a §-delimited file with header."""
        with file_lock(path):
            # Build content
            lines = [header]
            for entry in entries:
                lines.append(ENTRY_DELIMITER)
                lines.append(entry)
            
            content = "\n".join(lines) + "\n"
            
            # Atomic write
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(content)
            tmp.rename(path)  # Atomic on POSIX
    
    # =========================================================================
    # Memory Operations
    # =========================================================================
    
    def add(self, target: str, content: str) -> Dict[str, any]:
        """
        Add entry to memory or user store.
        
        Args:
            target: "memory" or "user"
            content: Entry content (will be scanned)
        
        Returns:
            {"success": bool, "error": str or None, "char_count": int}
        """
        if not self._loaded:
            self.load()
        
        # Scan for injection
        scan_result = scan_content(content)
        if scan_result:
            logger.warning("Blocked injection in %s: %s", target, scan_result)
            return {"success": False, "error": scan_result, "char_count": 0}
        
        # Check target
        if target not in ("memory", "user"):
            return {"success": False, "error": f"Invalid target: {target}", "char_count": 0}
        
        # Check char limit
        limit = self.memory_char_limit if target == "memory" else self.user_char_limit
        if len(content) > limit:
            return {
                "success": False,
                "error": f"Content exceeds {limit} char limit (got {len(content)})",
                "char_count": len(content)
            }
        
        # Add to entries
        if target == "memory":
            # Check for duplicate
            if content in self.memory_entries:
                return {"success": True, "error": "Duplicate entry", "char_count": len(content), "duplicate": True}
            self.memory_entries.append(content)
            self._write_file(self.memory_path, self.memory_entries, MEMORY_HEADER)
        else:
            if content in self.user_entries:
                return {"success": True, "error": "Duplicate entry", "char_count": len(content), "duplicate": True}
            self.user_entries.append(content)
            self._write_file(self.user_path, self.user_entries, USER_HEADER)
        
        # Note: snapshot NOT updated (frozen)
        return {"success": True, "error": None, "char_count": len(content)}
    
    def replace(self, target: str, old_content: str, new_content: str) -> Dict[str, any]:
        """
        Replace entry matching old_content with new_content.
        
        Args:
            target: "memory" or "user"
            old_content: Substring to match (must be unique)
            new_content: Replacement content
        
        Returns:
            {"success": bool, "error": str or None}
        """
        if not self._loaded:
            self.load()
        
        # Scan new content
        scan_result = scan_content(new_content)
        if scan_result:
            return {"success": False, "error": scan_result}
        
        # Check char limit
        limit = self.memory_char_limit if target == "memory" else self.user_char_limit
        if len(new_content) > limit:
            return {"success": False, "error": f"Content exceeds {limit} char limit"}
        
        # Find entry
        entries = self.memory_entries if target == "memory" else self.user_entries
        matches = [i for i, e in enumerate(entries) if old_content in e]
        
        if not matches:
            return {"success": False, "error": f"No entry found containing: {old_content[:50]}..."}
        
        if len(matches) > 1:
            return {"success": False, "error": f"Multiple matches ({len(matches)}). Use more specific substring."}
        
        # Replace
        idx = matches[0]
        entries[idx] = new_content
        
        # Write
        if target == "memory":
            self._write_file(self.memory_path, self.memory_entries, MEMORY_HEADER)
        else:
            self._write_file(self.user_path, self.user_entries, USER_HEADER)
        
        return {"success": True, "error": None}
    
    def remove(self, target: str, content_substring: str) -> Dict[str, any]:
        """
        Remove entry containing substring.
        
        Args:
            target: "memory" or "user"
            content_substring: Substring to match
        
        Returns:
            {"success": bool, "error": str or None, "removed": bool}
        """
        if not self._loaded:
            self.load()
        
        entries = self.memory_entries if target == "memory" else self.user_entries
        matches = [i for i, e in enumerate(entries) if content_substring in e]
        
        if not matches:
            return {"success": False, "error": "No matching entry found", "removed": False}
        
        if len(matches) > 1:
            return {"success": False, "error": f"Multiple matches ({len(matches)}). Use more specific substring.", "removed": False}
        
        # Remove
        idx = matches[0]
        removed = entries.pop(idx)
        
        # Write
        if target == "memory":
            self._write_file(self.memory_path, self.memory_entries, MEMORY_HEADER)
        else:
            self._write_file(self.user_path, self.user_entries, USER_HEADER)
        
        logger.info("Removed entry from %s: %s...", target, removed[:50])
        return {"success": True, "error": None, "removed": True}
    
    def read(self, target: str = "memory") -> List[str]:
        """Read all entries for target."""
        if not self._loaded:
            self.load()
        return self.memory_entries if target == "memory" else self.user_entries.copy()
    
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """Get storage statistics."""
        if not self._loaded:
            self.load()
        
        def calc_stats(entries: List[str], limit: int) -> Dict[str, int]:
            total = sum(len(e) for e in entries)
            return {
                "entries": len(entries),
                "total_chars": total,
                "limit": limit,
                "used_pct": int(100 * total / limit) if limit > 0 else 0
            }
        
        return {
            "memory": calc_stats(self.memory_entries, self.memory_char_limit),
            "user": calc_stats(self.user_entries, self.user_char_limit)
        }
    
    # =========================================================================
    # Rendering
    # =========================================================================
    
    def _render_block(self, target: str, entries: List[str]) -> str:
        """Render entries as a formatted block for system prompt."""
        if not entries:
            return f"## {target.upper()} (empty)\n"
        
        lines = [f"## {target.upper()}"]
        for i, entry in enumerate(entries, 1):
            lines.append(f"\n§ [{i}] {entry}")
        
        return "\n".join(lines)


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Simple test CLI
    store = EnhancedMemoryStore()
    store.load()
    
    print("=== Memory Stats ===")
    stats = store.get_stats()
    for key, vals in stats.items():
        print(f"\n{key}:")
        for k, v in vals.items():
            print(f"  {k}: {v}")
    
    print("\n=== Snapshot Preview ===")
    snapshot = store.get_snapshot()
    for key, val in snapshot.items():
        print(f"\n{key}:")
        print(val[:500] + "..." if len(val) > 500 else val)
