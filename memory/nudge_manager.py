#!/usr/bin/env python3
"""
NudgeManager - Hermes-inspired proactive prompts

Tracks agent activity and generates nudges to encourage:
1. Saving learnings to memory
2. Creating skills from successful task approaches
3. Context pressure warnings

Usage:
    from memory.nudge_manager import NudgeManager
    nm = NudgeManager()
    
    # Call each turn
    nudge = nm.check_turn()
    
    # After complex task completion
    nm.on_task_complete()
    
    # Context pressure check
    pressure = nm.check_context_pressure(token_count, limit)
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Default thresholds
DEFAULT_MEMORY_NUDGE_INTERVAL = 10  # Prompt to save memory every N turns
DEFAULT_SKILL_NUDGE_INTERVAL = 5   # Prompt to create skill after N task completions
DEFAULT_BUDGET_WARNING = 0.70       # Warn at 70% context
DEFAULT_BUDGET_CRITICAL = 0.90      # Urgent at 90% context


@dataclass
class NudgeState:
    """Persistent state for nudges."""
    turns_since_memory: int = 0
    tasks_since_skill: int = 0
    last_memory_nudge: float = 0
    last_skill_nudge: float = 0
    context_warned_70: bool = False
    context_warned_90: bool = False


class NudgeManager:
    """
    Tracks agent activity and generates proactive nudges.
    
    Nudges are suggestions, not commands. The agent decides whether to act.
    
    Design principles:
    - Nudge, don't force
    - Reset counters on relevant action (not on nudge itself)
    - Context warnings are informational (display to user, not injected)
    """
    
    def __init__(
        self,
        memory_nudge_interval: int = DEFAULT_MEMORY_NUDGE_INTERVAL,
        skill_nudge_interval: int = DEFAULT_SKILL_NUDGE_INTERVAL,
        budget_warning: float = DEFAULT_BUDGET_WARNING,
        budget_critical: float = DEFAULT_BUDGET_CRITICAL,
        state_file: Optional[Path] = None,
    ):
        self.memory_nudge_interval = memory_nudge_interval
        self.skill_nudge_interval = skill_nudge_interval
        self.budget_warning = budget_warning
        self.budget_critical = budget_critical
        
        # State file for persistence
        if state_file is None:
            workspace = Path(__file__).parent.parent
            state_file = workspace / ".nudge_state.json"
        self.state_file = Path(state_file)
        
        # Load or init state
        self.state = self._load_state()
        
        # Track if we've warned this session
        self._warned_70 = self.state.context_warned_70
        self._warned_90 = self.state.context_warned_90
    
    def _load_state(self) -> NudgeState:
        """Load persistent state from file."""
        if self.state_file.exists():
            try:
                import json
                data = json.loads(self.state_file.read_text())
                return NudgeState(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return NudgeState()
    
    def _save_state(self):
        """Persist state to file."""
        import json
        data = {
            'turns_since_memory': self.state.turns_since_memory,
            'tasks_since_skill': self.state.tasks_since_skill,
            'last_memory_nudge': self.state.last_memory_nudge,
            'last_skill_nudge': self.state.last_skill_nudge,
            'context_warned_70': self._warned_70,
            'context_warned_90': self._warned_90,
        }
        self.state_file.write_text(json.dumps(data, indent=2))
    
    def check_turn(self, memory_tool_used: bool = False) -> Optional[str]:
        """
        Call after each user turn.
        
        Args:
            memory_tool_used: True if agent used memory tool this turn
            
        Returns:
            Nudge message if threshold exceeded, None otherwise
        """
        # Reset if memory was used
        if memory_tool_used:
            self.state.turns_since_memory = 0
            self._save_state()
            return None
        
        # Increment counter
        self.state.turns_since_memory += 1
        
        # Check threshold
        if self.state.turns_since_memory >= self.memory_nudge_interval:
            # Don't fire too frequently (min 60 seconds between nudges)
            if time.time() - self.state.last_memory_nudge > 60:
                self.state.last_memory_nudge = time.time()
                self._save_state()
                return self._memory_nudge()
        
        self._save_state()
        return None
    
    def on_task_complete(self, skill_created: bool = False) -> Optional[str]:
        """
        Call after a complex task is completed.
        
        Args:
            skill_created: True if agent created a skill this time
            
        Returns:
            Nudge message if threshold exceeded, None otherwise
        """
        # Reset if skill was created
        if skill_created:
            self.state.tasks_since_skill = 0
            self._save_state()
            return None
        
        # Increment counter
        self.state.tasks_since_skill += 1
        
        # Check threshold
        if self.state.tasks_since_skill >= self.skill_nudge_interval:
            if time.time() - self.state.last_skill_nudge > 120:  # Min 2 min between skill nudges
                self.state.last_skill_nudge = time.time()
                self._save_state()
                return self._skill_nudge()
        
        self._save_state()
        return None
    
    def check_context_pressure(
        self, 
        current_tokens: int, 
        max_tokens: int,
        display_callback=None
    ) -> Optional[str]:
        """
        Check context pressure and warn user.
        
        Args:
            current_tokens: Current token count
            max_tokens: Model's context limit
            display_callback: Optional function to call with warning message
            
        Returns:
            Warning message if threshold exceeded, None otherwise
        """
        if max_tokens <= 0:
            return None
        
        ratio = current_tokens / max_tokens
        
        # 90% - critical
        if ratio >= self.budget_critical and not self._warned_90:
            self._warned_90 = True
            msg = self._context_critical()
            if display_callback:
                display_callback(msg)
            return msg
        
        # 70% - warning
        if ratio >= self.budget_warning and not self._warned_70:
            self._warned_70 = True
            msg = self._context_warning(ratio)
            if display_callback:
                display_callback(msg)
            return msg
        
        # Reset warnings if ratio drops
        if ratio < self.budget_warning:
            self._warned_70 = False
            self._warned_90 = False
        
        return None
    
    def reset_memory_counter(self):
        """Manually reset memory nudge counter."""
        self.state.turns_since_memory = 0
        self._save_state()
    
    def reset_skill_counter(self):
        """Manually reset skill nudge counter."""
        self.state.tasks_since_skill = 0
        self._save_state()
    
    def get_stats(self) -> dict:
        """Get current nudge stats."""
        return {
            "turns_since_memory": self.state.turns_since_memory,
            "tasks_since_skill": self.state.tasks_since_skill,
            "memory_nudge_threshold": self.memory_nudge_interval,
            "skill_nudge_threshold": self.skill_nudge_interval,
            "context_warning_70": self.budget_warning,
            "context_critical_90": self.budget_critical,
        }
    
    # =========================================================================
    # Nudge Templates
    # =========================================================================
    
    def _memory_nudge(self) -> str:
        """Generate memory save nudge."""
        return (
            "You just handled a complex task or made a decision worth remembering. "
            "Consider adding a § entry to MEMORY.md with the key takeaway."
        )
    
    def _skill_nudge(self) -> str:
        """Generate skill creation nudge."""
        return (
            "This approach worked well for a complex task. "
            "Consider creating a skill in workspace/skills/ to capture this procedure "
            "so it can be reused automatically in similar situations."
        )
    
    def _context_warning(self, ratio: float) -> str:
        """Generate context pressure warning."""
        pct = int(ratio * 100)
        return (
            f"Context at {pct}% capacity. Consider using /compress "
            "or explicitly saving memories to free up space."
        )
    
    def _context_critical(self) -> str:
        """Generate critical context warning."""
        return (
            "Context CRITICAL - approaching limit. Wrap up current work, "
            "save any memories, and consider /compress before continuing."
        )


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import sys
    
    nm = NudgeManager()
    
    print("=== NudgeManager Test ===\n")
    
    # Show initial state
    print("Initial stats:", nm.get_stats())
    
    # Simulate turns
    print("\n--- Simulating turns ---")
    for i in range(15):
        nudge = nm.check_turn()
        if nudge:
            print(f"Turn {i+1}: NUDGE FIRED - {nudge}")
        else:
            print(f"Turn {i+1}: No nudge")
    
    # Simulate task completions
    print("\n--- Simulating task completions ---")
    for i in range(8):
        nudge = nm.on_task_complete()
        if nudge:
            print(f"Task {i+1}: NUDGE FIRED - {nudge}")
        else:
            print(f"Task {i+1}: No nudge")
    
    # Context pressure test
    print("\n--- Context pressure test ---")
    test_cases = [
        (1000, 8000),  # 12.5% - no warning
        (5000, 8000),  # 62.5% - no warning  
        (6000, 8000),  # 75% - warning
        (7500, 8000),  # 93.75% - critical
    ]
    
    nm2 = NudgeManager()  # Fresh instance for pressure test
    for tokens, limit in test_cases:
        msg = nm2.check_context_pressure(tokens, limit)
        if msg:
            print(f"{tokens}/{limit} ({int(100*tokens/limit)}%): {msg}")
        else:
            print(f"{tokens}/{limit} ({int(100*tokens/limit)}%): OK")
