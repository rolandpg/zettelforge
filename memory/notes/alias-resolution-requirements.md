# Alias Resolution Requirements — Roland Fleet Memory System
**Version:** 1.0
**Date:** 2026-03-31
**Source:** OPUS (Claude Code agent)

See PRD v1.1 for phase context. Key design decisions:
- Separate alias map files: `memory/alias_maps/actors.json`, `tools.json`, `campaigns.json`
- MITRE ATT&CK IDs as canonical keys for actors
- Reverse map built at load time: O(1) alias → canonical lookup
- `resolve()` sits between extraction and index write
- Graceful degradation: unmapped entities pass through unchanged
- Collision detection raises ValueError at load time
- 17 acceptance criteria (AR-01 through AR-17)
