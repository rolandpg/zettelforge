---
name: ralph-loop
description: Run the RALPH loop — Recon → Analyze → Link → Prioritize & Execute → Handoff. Use when working on multi-phase projects where you need to iterate autonomously without prompting for every decision.
category: workflow
created: 2026-03-31
updated: 2026-03-31
---

# RALPH Loop — Parallel Agent Operating Cycle

## When to Use

This skill is the core operating cycle for co-engineering agents working in parallel with Patton on multi-phase projects (like the Memory System Improvement Plan). It can also be used directly by Patton when working alone on a complex, multi-iteration task.

**Use when:**
- Working on a project with distinct phases that need iterative implementation
- Building something that has a test suite you can run after each change
- The task is well-scoped but has many decisions along the way
- You need to make progress autonomously without constant input

**Co-engineer mode:** Spawn a sub-agent with the coengineer prompt (`.claude/memory-coengineer-prompt.md`) and let it run RALPH cycles. You only get messaged on blocks, completions, and escalation.

## The Loop

```
RALPH — run every iteration, stateless except where noted
```

### R → Recon
Gather current state. No assumptions.
- Run the test suite — what passed? What failed?
- Check git log `--oneline -5` for recent commits
- Read any iteration logs or directives files
- Identify: which phase is active, what's failing, what's the next action

### A → Analyze
Determine what the current state reveals.
- Parse test failures — which requirements are not met?
- Root cause: missing feature, bug, test gap, or PRD ambiguity?
- If all tests pass: is the next phase already done or just not tested?
- PRD ambiguous? Propose a fix and flag it.

### L → Link
Connect analysis to action.
- Map failures to specific code changes
- Identify which files to touch
- If PRD is ambiguous: write a proposed clarification, flag for review
- If a phase is complete: document what was built, validate manually
- Never implement phase N+1 until phase N is 100% passing

### P → Prioritize & Execute
Do the highest-value work. Ship code.
- One focused change at a time
- Run tests after each change, not at the end
- Commit small and descriptive: `phase N: implement X` or `phase N: fix Y`
- Blocked? Note it clearly and handoff

### H → Handoff
Communicate what you did, what you found, what needs attention.
- Write iteration notes to the plan log
- Need input? Send structured message via `sessions_send`:
  ```
  ## Status: [phase] — [pass/fail/blocked]
  ## Did: [what you did]
  ## Found: [what tests/results revealed]
  ## Need: [what you need — be specific]
  ## Doing: [what you're doing while waiting]
  ```
- Phase complete? Send summary with test results.
- Blocked >2 iterations on same issue? Escalate explicitly.

## Running the Memory Co-Engineer

```bash
# Spawn as Claude Code sub-agent
cd ~/.openclaw/workspace
claude --prompt .claude/memory-coengineer-prompt.md

# Or via sessions_spawn in OpenClaw
/sessions_spawn with runtime="subagent", task from memory-coengineer-prompt.md
```

## Directives File

When you need to send instructions to a running coengineer without interrupting it:
- Write to `memory/coengineer_directives.md`
- The coengineer reads this on every Recon pass
- Keep it short — one priority per line
- Use `PAUSE`, `PRIORITY: <task>`, or `NOTE: <message>` prefixes

## Handoff Protocol (Co-Engineer → Patton)

**Message Patton when:**
- A phase is complete (send test results)
- Blocked for >2 iterations (escalate with diagnostic)
- PRD ambiguity found (propose resolution)
- External action needed (API keys, system changes, user approval)

**Don't message for:**
- Routine test passes
- Intermediate progress on a known task
- Small commits that are part of a larger phase

## References
- Memory PRD: `memory/MEMORY_PRD.md`
- Test suite: `memory/test_memory_system.py`
- Phase 2.5 tests: `memory/test_phase_2_5.py`
- Co-engineer prompt: `.claude/memory-coengineer-prompt.md`
- Plan iterations: `memory/plan_iterations.jsonl`
