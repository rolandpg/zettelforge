---
name: godot-mcp
description: Godot MCP Pro integration for AI-powered Godot game development. Control Godot editor via 167 tools for scene editing, node management, scripting, and runtime inspection.
metadata:
  clawdbot:
    emoji: 🎮
    requires:
      bins:
        - godot-mcp
---

# Godot MCP Skill

Control Godot editor and game runtime via the Godot MCP Pro server.

## Prerequisites

1. Godot editor running with project open
2. Godot MCP Pro plugin enabled (copy `addons/godot_mcp/` to your project)
3. MCP server connected (runs automatically via godot-mcp CLI)

## Quick Start

```bash
# Check if Godot is connected
godot-mcp get-project-info

# Get scene tree
godot-mcp get-scene-tree

# Add a node
godot-mcp add-node --type CharacterBody2D --name Player

# Run the scene
godot-mcp play-scene
```

## Project Tools

| Command | Description |
|---------|-------------|
| `godot-mcp get-project-info` | Project metadata, version, viewport, autoloads |
| `godot-mcp get-filesystem-tree` | File/directory tree with filtering |
| `godot-mcp search-files --query "*.gd"` | Fuzzy/glob file search |
| `godot-mcp get-project-settings` | Read project.godot settings |
| `godot-mcp set-project-setting --key "display/window/size/viewport_width" --value "1920"` | Set project setting |

## Scene Tools

| Command | Description |
|---------|-------------|
| `godot-mcp get-scene-tree` | Live scene tree with hierarchy |
| `godot-mcp create-scene --name "Level1" --root-type "Node2D"` | Create new scene |
| `godot-mcp open-scene --path "res://scenes/level.tscn"` | Open scene |
| `godot-mcp play-scene` | Run scene |
| `godot-mcp stop-scene` | Stop running scene |
| `godot-mcp save-scene` | Save current scene |

## Node Tools

| Command | Description |
|---------|-------------|
| `godot-mcp add-node --type "Sprite2D" --name "Hero" [--parent "Player"]` | Add node |
| `godot-mcp delete-node --path "/root/Main/Enemy"` | Delete node |
| `godot-mcp duplicate-node --path "/root/Main/Coin"` | Duplicate node |
| `godot-mcp move-node --path "/root/Main/Player" --new-parent "/root/Characters"` | Reparent |
| `godot-mcp update-property --path "/root/Player" --property "position" --value "Vector2(100, 200)"` | Set property |
| `godot-mcp get-node-properties --path "/root/Player"` | Get all properties |
| `godot-mcp rename-node --path "/root/OldName" --new-name "NewName"` | Rename |

## Script Tools

| Command | Description |
|---------|-------------|
| `godot-mcp list-scripts` | List all scripts |
| `godot-mcp read-script --path "res://player.gd"` | Read script content |
| `godot-mcp create-script --path "res://enemy.gd" --template "CharacterBody2D"` | Create script |
| `godot-mcp edit-script --path "res://player.gd" --search "func _ready" --replace "func _ready():\\n    print('Hello')"` | Edit script |
| `godot-mcp attach-script --node-path "/root/Player" --script-path "res://player.gd"` | Attach script |
| `godot-mcp validate-script --path "res://player.gd"` | Validate GDScript |

## Editor Tools

| Command | Description |
|---------|-------------|
| `godot-mcp get-editor-errors` | Get errors and stack traces |
| `godot-mcp get-editor-screenshot` | Capture editor viewport |
| `godot-mcp get-game-screenshot` | Capture running game |
| `godot-mcp clear-output` | Clear output panel |
| `godot-mcp get-output-log` | Get output panel content |
| `godot-mcp reload-project` | Rescan filesystem and reload |

## Input & Runtime Tools

| Command | Description |
|---------|-------------|
| `godot-mcp simulate-key --key "KEY_SPACE" --pressed true` | Simulate key press |
| `godot-mcp simulate-mouse-click --x 100 --y 200 --button "BUTTON_LEFT"` | Mouse click |
| `godot-mcp simulate-action --action "ui_accept" --pressed true` | Input action |
| `godot-mcp get-game-scene-tree` | Runtime scene tree |
| `godot-mcp set-game-node-property --path "/root/Player" --property "health" --value "100"` | Set runtime property |
| `godot-mcp execute-game-script --script "print('Debug message')"` | Run GDScript in game |

## Animation Tools

| Command | Description |
|---------|-------------|
| `godot-mcp list-animations --player-path "/root/Player/AnimationPlayer"` | List animations |
| `godot-mcp create-animation --player-path "/root/Player/AnimationPlayer" --name "Walk"` | Create animation |
| `godot-mcp add-animation-track --player-path "/root/Player/AnimationPlayer" --animation "Walk" --track-type "value" --path ".:position"` | Add track |
| `godot-mcp set-animation-keyframe --player-path "/root/Player/AnimationPlayer" --animation "Walk" --track-index 0 --time 0.0 --value "Vector2(0, 0)"` | Set keyframe |

## TileMap Tools

| Command | Description |
|---------|-------------|
| `godot-mcp tilemap-set-cell --tilemap-path "/root/TileMap" --layer 0 --x 5 --y 3 --source-id 1` | Set cell |
| `godot-mcp tilemap-fill-rect --tilemap-path "/root/TileMap" --layer 0 --x 0 --y 0 --width 10 --height 10 --source-id 1` | Fill rectangle |
| `godot-mcp tilemap-clear --tilemap-path "/root/TileMap"` | Clear all cells |

## 3D Scene Tools

| Command | Description |
|---------|-------------|
| `godot-mcp add-mesh-instance --parent "/root" --name "Cube" --mesh-type "Box"` | Add mesh |
| `godot-mcp setup-camera-3d --path "/root/Camera3D" --fov 75 --near 0.1 --far 1000` | Configure camera |
| `godot-mcp setup-lighting --type "DirectionalLight3D" --parent "/root" --name "Sun"` | Add light |

## Physics Tools

| Command | Description |
|---------|-------------|
| `godot-mcp setup-collision --node-path "/root/Player" --shape "rectangle" --extents "Vector2(16, 32)"` | Add collision |
| `godot-mcp set-physics-layers --node-path "/root/Player" --layer 1 --mask 1` | Set layers |
| `godot-mcp add-raycast --parent "/root/Player" --name "GroundCheck" --cast-to "Vector2(0, 20)"` | Add raycast |

## Particle Tools

| Command | Description |
|---------|-------------|
| `godot-mcp create-particles --parent "/root" --name "Explosion" --type "GPUParticles2D"` | Create particles |
| `godot-mcp apply-particle-preset --particles-path "/root/Explosion" --preset "fire"` | Apply preset |

## Export Tools

| Command | Description |
|---------|-------------|
| `godot-mcp list-export-presets` | List export presets |
| `godot-mcp export-project --preset "Linux/X11"` | Get export command |

## Audio Tools

| Command | Description |
|---------|-------------|
| `godot-mcp add-audio-player --parent "/root" --name "BGM" --type "AudioStreamPlayer"` | Add audio player |
| `godot-mcp add-audio-bus --name "SFX"` | Add audio bus |
| `godot-mcp add-audio-bus-effect --bus-name "SFX" --effect-type "Reverb"` | Add effect |

## Tips

- Use `--raw` flag for JSON output suitable for scripting
- All node paths use Godot's path format: `/root/NodeName/ChildName`
- Vector2/Vector3 values: `Vector2(x, y)` or `Vector3(x, y, z)`
- Colors: `#ff0000` or `Color(1, 0, 0)`
- Undo/Redo is supported for all mutation operations

## Troubleshooting

**"Connection closed" error:**
- Godot editor not running
- MCP plugin not enabled in project
- Wrong project open

**"Node not found" error:**
- Check node path with `godot-mcp get-scene-tree`
- Scene may not be open in editor

**Screenshot black/empty:**
- Game not running (for game screenshots)
- Editor viewport minimized

## Full Tool List

Run `godot-mcp --help` to see all 167 available tools.
