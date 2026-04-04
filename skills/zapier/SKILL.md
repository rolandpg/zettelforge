---
name: Zapier
slug: zapier
version: 1.0.0
homepage: https://clawic.com/skills/zapier
description: Complete Zapier automation with Zaps, Tables, Interfaces, webhooks, REST Hooks API, and 6000+ app integrations.
metadata: {"clawdbot":{"emoji":"⚡","requires":{"env":["ZAPIER_API_KEY","ZAPIER_TABLES_TOKEN"],"config":["~/zapier/"]},"primaryEnv":"ZAPIER_API_KEY","os":["linux","darwin","win32"]}}
---

# Zapier

Complete Zapier reference. See auxiliary files for detailed operations.

## Quick Start

```bash
# Test API connection
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  https://api.zapier.com/v1/profile
```

## Setup

On first use, read `setup.md`. Preferences stored in `~/zapier/memory.md`.

## When to Use

Any Zapier operation: create Zaps, manage Tables, build Interfaces, configure webhooks, integrate 6000+ apps, automate workflows.

## Architecture

```
~/zapier/
├── memory.md      # Account context, common Zaps
└── zaps/          # Documented configurations
```

## Quick Reference

| Topic | File |
|-------|------|
| Setup & memory | `setup.md`, `memory-template.md` |
| REST Hooks API | `api.md` |
| Triggers (all types) | `triggers.md` |
| Actions (all types) | `actions.md` |
| Filters, Paths, Formatters | `logic.md` |
| Webhooks (Catch Hook, send) | `webhooks.md` |
| Zapier Tables (database) | `tables.md` |
| Zapier Interfaces (forms) | `interfaces.md` |
| Popular integrations | `integrations.md` |
| Patterns & recipes | `patterns.md` |

## Core Rules

1. **Test mode first** — Use test data before enabling Zap
2. **Triggers define scope** — Zap only runs when trigger fires
3. **Field mapping explicit** — Always verify data flows correctly
4. **Filters before actions** — Reduce unnecessary task usage
5. **Idempotency via dedup** — Use Dedup filter for critical flows
6. **Webhooks for instant** — Polling triggers have 1-15 min delay

## Authentication

**Environment variables:**
- `ZAPIER_API_KEY` — API key from zapier.com/developer/platform
- `ZAPIER_TABLES_TOKEN` — Tables API token (optional, for Tables API)

```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  https://api.zapier.com/v1/zaps
```

## Zapier Product Suite

| Product | Purpose | File |
|---------|---------|------|
| **Zaps** | Automated workflows | `triggers.md`, `actions.md` |
| **Tables** | No-code database | `tables.md` |
| **Interfaces** | Forms, pages, chatbots | `interfaces.md` |
| **Chatbots** | AI-powered assistants | `interfaces.md` |
| **Canvas** | Visual workflow planning | Web UI only |

## Common Traps

- **Amount in wrong format** → Zapier passes strings, convert with Formatter
- **No idempotency** → Dedup action prevents duplicate processing
- **Webhook timeout** → Return 200 within 30 seconds
- **Task burn** → One Zap run = 1+ tasks, filters don't count
- **Polling delay** → Free: 15min, Paid: 1-2min, Webhooks: instant

## External Endpoints

| Endpoint | Purpose |
|----------|---------|
| `https://api.zapier.com/v1/*` | REST Hooks API |
| `https://hooks.zapier.com/hooks/catch/*` | Incoming webhooks |
| `https://tables.zapier.com/api/v1/*` | Tables API |
| Connected apps | 6000+ via Zapier |

## Security & Privacy

**Environment variables used:**
- `ZAPIER_API_KEY` — for REST Hooks API authentication

**Sent to Zapier:** Workflow data, field mappings, trigger/action configs
**Sent to connected apps:** Only data you explicitly map
**Stays local:** ~/zapier/ preferences, API keys (never logged)
**Never:** Expose API keys, skip webhook verification

## Trust

This skill sends data to Zapier (zapier.com) and any apps you connect through Zaps.

## Related Skills
Install with `clawhub install <slug>` if user confirms:
- `api` — REST API patterns
- `webhook` — Webhook fundamentals
- `saas` — SaaS metrics and billing

## Feedback

- If useful: `clawhub star zapier`
- Stay updated: `clawhub sync`
