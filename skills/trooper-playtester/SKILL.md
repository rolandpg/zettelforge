---
name: trooper-playtester
description: Hybrid AI playtester for Trooper Clash. Uses Godot MCP for fast game state access + vision model for visual verification. Implements RALPH loop for autonomous testing.
metadata:
  clawdbot:
    emoji: 🎮
    requires:
      bins:
        - godot-mcp
      skills:
        - godot-mcp
        - ralph-loop
---

# Trooper Clash Playtester

Hybrid AI playtester combining fast game state (Godot MCP) with visual verification (vision models).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Godot Game Running with MCP Plugin                         │
│  └─→ WebSocket:6505 ←→ godot-mcp CLI                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Playtest Agent                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ State Monitor  │  │ Decision Engine│  │ Vision Check │  │
│  │ (fast, cheap)  │  │ (AI strategy)  │  │ (verify UI)  │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Start Godot with Trooper Clash and MCP plugin enabled
cd /home/rolandpg/trooper-clash/godot
godot --path . &

# 2. Run playtest agent
trooper-playtester --mode exploration --duration 300

# 3. Get report
trooper-playtester report --format markdown
```

## Modes

### 1. Exploration Mode (Default)
Navigate menus, start matches, verify basic functionality.

```bash
trooper-playtester --mode exploration --duration 60
```

**Checks:**
- Main menu loads
- Can start match
- HUD displays correctly
- Match ends properly

### 2. Combat Mode
Test combat mechanics, upgrades, mercenaries.

```bash
trooper-playtester --mode combat --duration 300
```

**Checks:**
- Troopers spawn and fight
- Upgrades apply correctly
- Mercenaries counter-pick
- Resources accumulate

### 3. Stress Mode
Max units, rapid inputs, edge cases.

```bash
trooper-playtester --mode stress --duration 120
```

**Checks:**
- Performance at 200 units
- Memory stability
- Crash resistance

### 4. Regression Mode
Run predefined test scenarios.

```bash
trooper-playtester --mode regression --scenario basic_match
```

## RALPH Loop Implementation

### Recon (Every 100ms)
```bash
# Fast state poll via MCP
godot-mcp get-game-scene-tree --raw
godot-mcp get-game-node-properties --path "/root/Match/HUD"
```

### Analyze
Parse state for:
- Unit positions and HP
- Resource counts
- Match phase
- Player status
- Error states

### Link
Map observations to strategy:
```python
if my_minerals > 300 and not has_mercenary:
    action = "buy_ranger"
elif enemy_has_shieldbearer:
    action = "buy_technician"  # Counter-pick
```

### Prioritize & Execute
```bash
# Execute highest-value action
godot-mcp simulate-mouse-click --x 640 --y 700  # Open upgrade panel
godot-mcp simulate-mouse-click --x 700 --y 600  # Click upgrade
```

### Handoff (Every 5s)
```bash
# Visual verification
godot-mcp get-game-screenshot --output /tmp/frame.png
vision-model analyze /tmp/frame.png "Any visual bugs? UI readable?"
```

## State Monitoring (Fast Path)

### Game State Structure
```json
{
  "match_time": 145.5,
  "phase": "MERC_WARS",
  "players": {
    "0": {
      "minerals": 450,
      "gas": 25,
      "supply": 18,
      "cc_hp": 4800,
      "eliminated": false
    }
  },
  "units": [
    {"type": "trooper", "owner": 0, "hp": 85, "pos": [120, 0, 340]},
    {"type": "ranger", "owner": 1, "hp": 120, "pos": [-200, 0, 100]}
  ]
}
```

### Parse Script
```bash
# Extract specific values from game state
trooper-playtester state --query "players.0.minerals"
trooper-playtester state --query "units[type=trooper].count"
```

## Visual Verification (Slow Path)

### Screenshot Analysis
```bash
# Capture frame
godot-mcp get-game-screenshot

# Vision model checks
trooper-playtester vision-check --prompt "Verify mineral count shows 450"
trooper-playtester vision-check --prompt "Any UI elements overlapping or clipped?"
trooper-playtester vision-check --prompt "Are unit colors distinct for each player?"
```

### Automated Checks
| Check | Frequency | Model |
|-------|-----------|-------|
| HUD readability | Every 5s | Grok-4 Vision |
| Visual bugs | Every 10s | Grok-4 Vision |
| Match end screen | On event | Grok-4 Vision |
| Unit visibility | Every 5s | Grok-4 Vision |

## Decision Engine

### Strategy Profiles

**Aggressive Bot**
- Prioritize: Weapons upgrades, early mercs
- Action: Push constantly, deny feed

**Economic Bot**
- Prioritize: Spawn rate, passive income
- Action: Mass Troopers, overwhelm late

**Counter-Pick Bot**
- Prioritize: Scout enemy, buy counters
- Action: React to opponent composition

**Random Bot**
- Random upgrades and mercs
- Good for finding edge cases

### Command Examples
```bash
# Set strategy
trooper-playtester --strategy aggressive --duration 300

# Multi-bot match
trooper-playtester --bots "aggressive,economic,counter-pick,random"
```

## Input Simulation

### Mouse Actions
```bash
# Click at screen position (normalized 0-1 or pixels)
godot-mcp simulate-mouse-click --x 0.5 --y 0.8
godot-mcp simulate-mouse-click --x 640 --y 576

# Drag for unit selection
godot-mcp simulate-mouse-move --x 100 --y 100
godot-mcp simulate-mouse-click --button left --pressed true
godot-mcp simulate-mouse-move --x 300 --y 300
godot-mcp simulate-mouse-click --button left --pressed false
```

### Keyboard Actions
```bash
# Camera controls
godot-mcp simulate-key --key "KEY_W" --pressed true   # Pan up
godot-mcp simulate-key --key "KEY_SPACE"              # Center camera

# Game actions
godot-mcp simulate-key --key "KEY_T"                  # Toggle trooper spawn
godot-mcp simulate-key --key "KEY_1"                  # Open upgrades
```

### Game Script Execution
```bash
# Direct GDScript execution (most reliable)
godot-mcp execute-game-script --script "
var gm = get_node('/root/GameManager')
gm.players[0].minerals += 1000
"
```

## Reporting

### Real-time Metrics
```bash
# Watch live stats
trooper-playtester watch --metrics "fps,unit_count,resources"
```

### Session Report
```bash
# Generate report
trooper-playtester report --session-id abc123 --format markdown
```

**Report Includes:**
- Actions taken
- Decisions made with reasoning
- Visual bugs found
- Performance metrics
- Recommendations

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Playtest Trooper Clash
  run: |
    godot --path trooper-clash/godot --headless &
    sleep 5
    trooper-playtester --mode regression --duration 60
    trooper-playtester report --fail-on-bugs
```

## Troubleshooting

### "Connection refused" to Godot
- Ensure MCP plugin enabled in Project Settings
- Check port 6505 is available: `lsof -i :6505`
- Restart Godot with plugin enabled

### Screenshots black/empty
- Game window must be visible (not minimized)
- For headless: use `--display-driver xvfb`
- Enable "Editor > Run > Low Processor Mode" off

### State parsing errors
- Check Godot version matches (4.x)
- Verify scene paths: `godot-mcp get-scene-tree`
- Some nodes may need to be exposed via GDScript

## Implementation Phases

### Phase 1: Basic State Reader (Done)
- ✅ Godot MCP configured
- ✅ Can read game state
- ✅ Can capture screenshots

### Phase 2: Input Simulation (Next)
- ⬜ Wrapper scripts for common actions
- ⬜ Strategy profiles
- ⬜ Decision engine

### Phase 3: Visual Verification
- ⬜ Vision model integration
- ⬜ Automated bug detection
- ⬜ UI readability checks

### Phase 4: Autonomous Play
- ⬜ RALPH loop implementation
- ⬜ Multi-bot matches
- ⬜ CI/CD integration

---

**Status:** Phase 1 complete. Ready for Phase 2 implementation.
