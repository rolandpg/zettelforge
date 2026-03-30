# Merged Memory Architecture
**Combining OpenClaw structure with Hermes Agent patterns**

## Design Philosophy
- **Keep:** Daily logs, topic notes, CTI database (valuable historical/contextual data)
- **Enhance:** MEMORY.md and USER.md with Hermes patterns (bounded limits, injection scanning, frozen snapshot)
- **Add:** Skill creation from Hermes (procedural memory system)

---

## Target Architecture

```
workspace/
├── SOUL.md                    # Agent persona (unchanged)
├── IDENTITY.md                # Agent identity (unchanged)
├── AGENTS.md                  # Boot sequence (enhanced)
├── USER.md                    # Bounded user preferences (~1375 chars)
├── MEMORY.md                  # Bounded curated memory (~2200 chars)
│
├── memory/                    # Historical context (READ-ONLY for agent)
│   ├── YYYY-MM-DD.md          # Daily logs (raw events, timestamps)
│   └── briefings/             # CTI briefings (distilled intel)
│
├── notes/                     # Topic research (PARA structure)
│   ├── cti-improvements.md
│   ├── open-loops.md
│   └── *.md
│
├── skills/                    # Procedural memories (NEW)
│   ├── SKILL.md               # Skill system template
│   ├── cti-collection/        # Example: CTI collection skill
│   │   └── SKILL.md
│   └── social-media/          # Example: X posting skill
│       └── SKILL.md
│
├── cti-workspace/             # CTI database (unchanged)
│   ├── data/cti/              # SQLite database
│   └── darkweb-observatory/   # Dark web monitoring
│
└── .openclaw/                 # OpenClaw internal (unchanged)
```

---

## Entry Format: § Delimiter

### MEMORY.md (Bounded, ~2200 char limit)
```markdown
# MEMORY.md - Long-Term Memory

§ Identity: Patton, Strategic Operations Agent for Patrick Roland
§ CTI focus: DIB/CMMC threats, CISA KEV, NVD CVEs
§ Key actors: Handala Hack, Volt Typhoon, APT28/29
§ X account: @Deuslogica, threat intel threads perform best

§ X.com is pre-authenticated via xurl (OAuth1)
§ CTI pipeline: 9 collectors, CISA KEV + NVD + OTX + THN + more
§ Storage: Hot (SSD) / Cold (HDD) tier

§ Standing tasks:
- Monitor CTI pipeline daily
- Draft X content from CTI findings
- Update memory after each session
```

### USER.md (Bounded, ~1375 char limit)
```markdown
# USER.md - About Patrick Roland

§ Name: Patrick Roland | CISSP, CCP | Navy nuclear veteran
§ Company: Summit 7 Systems (Director of SOC Services)
§ Focus: MSSP consolidation, CMMC/DIB expertise
§ Target market: DoD tier 2-4 suppliers

§ Preferences:
- Direct communication, no fluff
- Wants proactive, not reactive
- Local-only solutions (privacy priority)
- Likes to experiment and iterate

§ CTI priorities:
- MOIS-linked actors (Handala, MuddyWater)
- China-Nexus (Volt Typhoon, APT28/29)
- Ransomware (backup/BCP failures)
```

---

## Frozen Snapshot Pattern

### Session Start
1. Load MEMORY.md, USER.md, daily logs, briefings
2. Capture "frozen snapshot" for system prompt injection
3. This snapshot does NOT change during the session
4. Mid-session memory writes persist to disk immediately

### Why Frozen?
- Prefix cache stability (no mid-session re-tokenizing)
- Consistent agent behavior within session
- Prevents oscillation from memory edits

---

## Content Injection Scanning

All memory content scanned before injection:
```python
_THREAT_PATTERNS = [
    r'ignore\s+previous\s+instructions',
    r'you\s+are\s+now\s+',
    r'do\s+not\s+tell\s+the\s+user',
    r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET',
    r'authorized_keys',
]
_INVISIBLE_CHARS = {'\u200b', '\u200c', '\u200d', '\ufeff', ...}
```

Blocked content → rejected with error, logged

---

## Skill System (Procedural Memory)

Skills capture HOW, not WHAT:
```
skills/
├── SKILL.md           # Template
├── cti-collection/
│   ├── SKILL.md       # How to run CTI collectors
│   └── references/
├── x-posting/
│   ├── SKILL.md       # How to craft threat intel posts
│   └── templates/
└── cve-analysis/
    ├── SKILL.md
    └── scripts/
```

### SKILL.md Format
```markdown
---
name: cti-collection
description: Run the CTI collection pipeline
---
# CTI Collection Skill

## When to Use
After each collection cycle or when explicitly requested.

## How to Run
1. cd ~/cti-workspace
2. python3 collect_cisa_kev.py
3. python3 collect_nvd.py
4. python3 threat_alert.py

## Notes
- 6 AM: CISA KEV
- 7 AM: NVD + DataBreaches + Ransomware
- 8 AM: OTX
- 9 AM: IOC linking
```

---

## Boot Sequence (Enhanced)

```
1. Read SOUL.md         → Establish persona
2. Read USER.md         → Load user preferences (frozen snapshot)
3. Read MEMORY.md       → Load curated memories (frozen snapshot)
4. Read memory/YYYY-MM-DD.md  → Today's events
5. Read memory/briefings/*.md → Recent CTI intel
6. Load skills/         → Load procedural memories
7. Initialize nudge tracker → Track turns since memory/skill use
8. Ready for user input
```

---

## Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| MEMORY.md | Unbounded, unstructured | Bounded (~2200), § delimited |
| USER.md | Unbounded | Bounded (~1375) |
| Injection scanning | None | All content scanned |
| Frozen snapshot | None | System prompt stable |
| Skills | Manual, limited | Autonomous creation, reusable |
| Daily logs | Raw timestamps | Historical context (read-only) |

---

## What Stays the Same
- Daily logs (`memory/YYYY-MM-DD.md`)
- Topic notes (`notes/*.md`)
- CTI database + LanceDB
- SOUL.md, IDENTITY.md
- File locations (CTI workspace, etc.)

---

## Migration Path
1. Backup current MEMORY.md, USER.md
2. Restructure into § delimited format
3. Add character limits
4. Implement injection scanning
5. Add skill system
6. Update boot sequence

No data loss - we consolidate the valuable parts and enhance with Hermes patterns.
