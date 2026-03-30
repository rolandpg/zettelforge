# Implementation Checklist: Hermes Learning for OpenClaw
**Target:** Integrate self-learning features from Hermes Agent
**Priority:** High - transforms reactive agent into proactive partner
**Effort:** Phase 1 = 2-3 hours, Phase 2 = 2-3 hours, Phase 3 = 3-4 hours

---

## Phase 1: Memory Tool Enhancement
**Goal:** Better memory with bounded limits, injection scanning, frozen snapshot

### 1.1 Create Enhanced MemoryStore Class
- [x] Create `workspace/memory/enhanced_memory.py`
- [x] Implement bounded character limits (memory_char_limit, user_char_limit)
- [x] Implement frozen snapshot pattern (stable system prompt, live disk state)
- [x] Implement entry delimiter system (§ section separator)
- [x] Add content injection scanning (_scan_memory_content)
- [x] Add invisible unicode character detection
- [x] Add file locking for concurrent access

### 1.2 Integrate into Agent Boot
- [ ] Modify AGENTS.md boot sequence to use EnhancedMemoryStore
- [ ] Load memory at startup, capture frozen snapshot
- [ ] Expose memory tool with add/replace/remove/read actions
- [ ] Write mid-session changes immediately (durable but don't change snapshot)

### 1.3 Update Memory Files
- [x] Review current MEMORY.md structure
- [x] Convert to delimiter-separated entries
- [x] Enforce character limits
- [x] Test injection scanning on existing entries

### 1.4 Test
- [x] Verify memory persists across sessions
- [x] Verify frozen snapshot doesn't change mid-session
- [x] Verify injection scanning blocks malicious content
- [x] Verify file locking works with concurrent access

**Files to modify:**
- `workspace/memory/enhanced_memory.py` (new)
- `workspace/AGENTS.md` (boot sequence)
- `workspace/MEMORY.md` (structure update)

---

## Phase 2: Nudge System
**Goal:** Agent prompts itself to save memories and create skills

### 2.1 Create NudgeManager
- [ ] Create `workspace/memory/nudge_manager.py`
- [ ] Track turns since last memory flush (`_turns_since_memory`)
- [ ] Track iterations since skill creation check (`_iters_since_skill`)
- [ ] Configurable intervals (memory_nudge_interval, skill_nudge_interval)
- [ ] Trigger nudge when threshold exceeded

### 2.2 Memory Nudge Logic
- [ ] After N user turns without saving to memory → prompt agent to consider saving
- [ ] Nudge text: "You just handled a complex task. Consider saving key learnings to MEMORY.md."
- [ ] Only nudge, don't force (agent decides)
- [ ] Reset counter when memory tool is used

### 2.3 Skill Creation Nudge Logic
- [ ] After N complex task completions → prompt to create skill
- [ ] Nudge text: "This approach worked well. Create a skill so you can reuse it."
- [ ] Only nudge for task types worth saving
- [ ] Reset counter when skill is created

### 2.4 Context Pressure Warnings
- [ ] Track context window usage
- [ ] Warning at 70%: "Approaching context limit. Consider /compress or /memory."
- [ ] Warning at 90%: "Critical - wrap up or compress context now."
- [ ] Integrate with existing HEARTBEAT.md logic

### 2.5 Integration Points
- [ ] Add nudge checking to main agent loop
- [ ] Add nudge to HEARTBEAT.md periodic checks
- [ ] Test nudges fire at correct intervals

**Files to modify:**
- `workspace/memory/nudge_manager.py` (new)
- `workspace/AGENTS.md` (boot sequence update)
- `workspace/HEARTBEAT.md` (add nudge checks)
- `workspace/SOUL.md` (add nudge personality)

---

## Phase 3: Autonomous Skill Creation
**Goal:** Agent creates skills from successful task approaches

### 3.1 Skill Creation Trigger
- [ ] Detect complex task completion (multi-step success)
- [ ] After nudge accepted → invoke skill_manager tool
- [ ] Generate skill name and description automatically
- [ ] Create SKILL.md with frontmatter + instructions
- [ ] Create directory structure (references/, templates/, scripts/)

### 3.2 Skill Manager Tool
- [ ] Create `workspace/skills/` directory structure
- [ ] Implement create/edit/patch/delete actions
- [ ] Add YAML frontmatter validation (name, description required)
- [ ] Security scan on skill creation (same as memory injection scanning)
- [ ] Skill improvement tracking (update on subsequent successful use)

### 3.3 Skill Templates
- [ ] Create skill template in `workspace/skills/SKILL.md.template`
- [ ] Define standard sections: Description, Usage, Examples, Gotchas
- [ ] Document skill creation workflow

### 3.4 Existing Skill Migration
- [ ] Review current workspace skills (CTI-related)
- [ ] Convert to SKILL.md format with frontmatter
- [ ] Add to skills/ directory
- [ ] Test skill loading and execution

### 3.5 Skills Hub Compatibility
- [ ] Ensure OpenClaw skills work with agentskills.io standard
- [ ] Add index-cache skill if needed
- [ ] Test skill discovery and installation

**Files to modify:**
- `workspace/skills/` (new directory)
- `workspace/skills/skill_manager.py` (new)
- `workspace/skills/*.md` (migrate existing)
- `workspace/SOUL.md` (skill creation guidance)

---

## Phase 4: Session Search (Optional)
**Goal:** Fast lookup of past conversations

### 4.1 Honcho Self-Host Setup (Optional)
- [ ] Evaluate Honcho server requirements
- [ ] Deploy Honcho on local homelab (or skip if not needed)
- [ ] Configure base_url for self-hosted
- [ ] Test user modeling functionality

### 4.2 FTS5 Integration (Alternative)
- [ ] Evaluate SQLite FTS5 for local session search
- [ ] Index conversation history
- [ ] Create search tool for agent access

### 4.3 LLM Summarization
- [ ] Generate summaries of completed sessions
- [ ] Store summaries for fast retrieval
- [ ] Use summaries for context injection

**Decision point:** Only pursue if Phase 1-3 prove insufficient

---

## Phase 5: User Modeling (Optional)
**Goal:** Better understanding of Patrick's preferences

### 5.1 Honcho Dialectic (If Self-Hosted)
- [ ] Enable self-critique mode
- [ ] Track preference patterns
- [ ] Update USER.md with learned preferences

### 5.2 Manual Preference Updates
- [ ] Periodic review of USER.md accuracy
- [ ] Patrick confirms/corrects learned preferences
- [ ] Document communication style preferences

---

## Testing Checklist

### Memory System
- [ ] Memory persists across agent restarts
- [ ] Character limits enforced
- [ ] Injection scanning blocks malicious content
- [ ] Frozen snapshot stable during session
- [ ] Mid-session writes persist immediately

### Nudge System
- [ ] Memory nudge fires at correct interval
- [ ] Skill nudge fires after complex tasks
- [ ] Context warnings fire at 70%/90%
- [ ] Nudges don't fire too frequently
- [ ] Agent can dismiss nudges appropriately

### Skill System
- [ ] Skills can be created from nudge
- [ ] Skills persist across sessions
- [ ] Skills improve with use
- [ ] Security scanning works
- [ ] Skills compatible with agentskills.io

### Integration
- [ ] Boot sequence completes without errors
- [ ] All tools accessible to agent
- [ ] No performance degradation
- [ ] Logs show correct operation

---

## Rollback Plan
- [ ] Backup current workspace before changes
- [ ] Test each phase independently
- [ ] Keep old memory system until new one verified
- [ ] Document all file locations before modifying

---

## Priority Order
1. Phase 1 (Memory) - Foundation, do first
2. Phase 2 (Nudges) - Uses Phase 1, logical next
3. Phase 3 (Skills) - Most powerful, but complex
4. Phase 4-5 - Optional, evaluate after 1-3

---

## Effort Estimate
- Phase 1: 2-3 hours (straightforward)
- Phase 2: 2-3 hours (straightforward)
- Phase 3: 3-4 hours (more complex)
- Phase 4-5: 4+ hours (optional, evaluate need)

**Total for core phases: 7-10 hours**
