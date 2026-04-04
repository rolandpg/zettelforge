# OpenClaw Multi-Agent Architecture

## Core Concepts

An **agent** is a fully isolated brain with:
- **Workspace**: Files, AGENTS.md/SOUL.md/USER.md, persona rules (`~/.openclaw/workspace-<agentId>/`)
- **AgentDir**: Auth profiles, model registry, per-agent config (`~/.openclaw/agents/<agentId>/agent/`)
- **Sessions**: Chat history + routing state (`~/.openclaw/agents/<agentId>/sessions/`)

Auth profiles are **per-agent** — no cross-talk unless explicitly enabled.

## Agent Isolation

| Resource | Scope | Path |
|----------|-------|------|
| Workspace | Per-agent | `~/.openclaw/workspace-<agentId>/` |
| AgentDir | Per-agent | `~/.openclaw/agents/<agentId>/agent/` |
| Sessions | Per-agent | `~/.openclaw/agents/<agentId>/sessions/` |
| Auth profiles | Per-agent | `~/.openclaw/agents/<agentId>/agent/auth-profiles.json` |

## Creating Agents

```bash
openclaw agents add <agentId>
# Creates workspace, agentDir, sessions automatically
```

Verify:
```bash
openclaw agents list --bindings
```

## Routing (Bindings)

Bindings are **deterministic**, most-specific wins:

1. `peer` match (exact DM/group/channel id)
2. `parentPeer` match (thread inheritance)
3. `guildId + roles` (Discord)
4. `guildId` (Discord)
5. `teamId` (Slack)
6. `accountId` match
7. channel-level match (`accountId: "*"`)
8. fallback to default agent

### Binding Examples

**One WhatsApp number per agent:**
```json5
bindings: [
  { agentId: "home", match: { channel: "whatsapp", accountId: "personal" } },
  { agentId: "work", match: { channel: "whatsapp", accountId: "biz" } },
]
```

**Same channel, specific peer to different agent:**
```json5
bindings: [
  { agentId: "opus", match: { channel: "whatsapp", peer: { kind: "direct", id: "+15551234567" } } },
  { agentId: "chat", match: { channel: "whatsapp" } },  // fallback
]
```

**Discord bots per agent:**
```json5
bindings: [
  { agentId: "main", match: { channel: "discord", accountId: "default" } },
  { agentId: "coding", match: { channel: "discord", accountId: "coding" } },
]
```

## Agent-to-Agent Communication

Enable in config:
```json5
tools: {
  agentToAgent: {
    enabled: true,
    allow: ["main", "tamara", "vigil"]
  }
}
```

Send message:
```javascript
sessions_send({
  sessionKey: "agent:tamara:main",
  message: "CTI alert: New KEV added"
})
```

**Speed**: Direct messaging (sessions_send) > file-based sync. For critical alerts, use sessions_send. For daily summaries, file sync is fine.

## Fleet Pattern (Roland Fleet)

Each agent writes daily sync to shared location:
```
~/.openclaw/workspace/fleet/patton_daily.md
~/.openclaw/workspace-tamara/fleet/tamara_daily.md
~/.openclaw/workspace-vigil/fleet/vigil_daily.md
```

Agents read each other's syncs during heartbeat/boot.

## Per-Agent Configuration

**Different models:**
```json5
agents: {
  list: [
    { id: "chat", model: "anthropic/claude-sonnet-4-6" },
    { id: "opus", model: "anthropic/claude-opus-4-6" }
  ]
}
```

**Sandboxing:**
```json5
{
  id: "family",
  sandbox: { mode: "all", scope: "agent" },
  tools: { allow: ["read"], deny: ["exec", "write", "edit"] }
}
```

**Group chat gating:**
```json5
groupChat: {
  mentionPatterns: ["@family", "@familybot"]
}
```

## Cross-Agent Memory Search

Search another agent's QMD transcripts:
```json5
agents: {
  list: [{
    id: "main",
    memorySearch: {
      qmd: {
        extraCollections: [
          { path: "~/agents/family/sessions", name: "family-sessions" }
        ]
      }
    }
  }]
}
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `openclaw agents list` | List all agents |
| `openclaw agents list --bindings` | Show routing bindings |
| `openclaw agents add <id>` | Create new agent |
| `openclaw config set tools.agentToAgent.enabled true` | Enable A2A messaging |
| `openclaw gateway restart` | Apply config changes |

## Anti-Patterns

- ❌ Reuse agentDir across agents (causes auth/session collisions)
- ❌ Assume main agent credentials are shared
- ❌ Use file sync for urgent alerts (use sessions_send)

## Roland Fleet Current Setup

| Agent | Role | Workspace | Routing |
|-------|------|-----------|---------|
| main (Patton) | Strategic ops, default | `workspace/` | default |
| tamara | Social media content | `workspace-tamara/` | telegram DM |
| vigil | CTI analyst | `workspace-vigil/` | background only |

A2A enabled: main ↔ tamara ↔ vigil
