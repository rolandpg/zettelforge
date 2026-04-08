#!/bin/bash
# RALPH Loop Initiator for Fleet
# Triggers RALPH (Recon-Analyze-Link-Prioritize-Execute-Handoff) on all agents
# based on tasks in notes/open-loops.md
# Runs via systemd timer

set -e

echo "[$(date)] RALPH initiator starting for all agents"

WORKSPACE="/home/rolandpg/.openclaw/workspace"
OPEN_LOOPS="$WORKSPACE/notes/open-loops.md"

# Agents and their primary domains (from SOUL and fleet setup)
AGENTS=("patton" "tamara" "vigil" "nexus")
DOMAINS=(
  "strategy,briefings,financial,CTI-orchestration"  # Patton
  "social-media,content,X,LinkedIn"                 # Tamara
  "CTI-collection,pipeline,dashboard"               # Vigil
  "AI-research,memory,packaging,improvements"       # Nexus
)

for i in "${!AGENTS[@]}"; do
  agent="${AGENTS[$i]}"
  domain="${DOMAINS[$i]}"
  
  echo "[$(date)] Initiating RALPH loop for $agent ($domain tasks)"
  
  # Send directive to agent's workspace or session
  # For now, append to agent's daily sync and trigger via fleet sync pattern
  AGENT_DIR="$HOME/.openclaw/workspace-$agent"
  mkdir -p "$AGENT_DIR/fleet"
  
  cat >> "$AGENT_DIR/fleet/ralph_directive.md" << EOF
# RALPH Directive - $(date +%Y-%m-%d\ %H:%M)
Run full RALPH loop (Recon → Analyze → Link → Prioritize & Execute → Handoff) on your assigned tasks from $OPEN_LOOPS.

Assigned domain: $domain
Global open loops: Threat Engram Startup (your role noted in file).

Follow ralph-loop/SKILL.md exactly. Document in your daily note. Handoff blocks or completions to Patton.

EOF

  echo "[$(date)] RALPH directive written for $agent"
done

echo "[$(date)] RALPH initiator complete. Fleet sync will propagate."
