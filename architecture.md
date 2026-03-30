# Roland Fleet Infrastructure — Architecture Overview
*Generated 2026-03-30 | Updated with Phase 4 module integration*

---

## 1. High-Level Architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           PATRICK ROLAND (User)                              ║
║                    Telegram Direct / X.com / LinkedIn                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                      │
                                      ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                          OPENCLAW GATEWAY                                    ║
║   • boot-md hook: BOOT.md on startup                                        ║
║   • Session management (main + subagents)                                    ║
║   • Channel routing: Telegram, X, etc.                                       ║
║   • Skills framework: ~/.openclaw/workspace/skills/                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║  PATTON (Primary Agent)          │ HERMES (Subagent)    │ NOUSNET (Subagent)║
║  Strategic Operations             │ Research/Analysis    │ (legacy)          ║
║  SOUL.md: Patton persona          │ ~/hermes-agent/      │ ~/nousnet/        ║
║  Voice: Direct, no emoji          │ sessions_spawn       │                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                    │
                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    WORKSPACE LAYER (~/.openclaw/workspace/)                  ║
║                                                                              ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  ║
║  │  SOUL.md     │  │  MEMORY.md   │  │  USER.md     │  │  AGENTS.md    │  ║
║  │  Patton      │  │  Long-term   │  │  Patrick     │  │  Boot seq     │  ║
║  │  identity    │  │  12 entries  │  │  preferences │  │  + init steps │  ║
║  │              │  │  97% used    │  │              │  │                │  ║
║  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘  ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                    PYTHON MODULES (memory/)                             │ ║
║  │                                                                          │ ║
║  │  enhanced_memory.py ─── EnhancedMemoryStore ─── Bounded 2200 chars       │ ║
║  │       ├── load()       → reads MEMORY.md, USER.md at boot               │ ║
║  │       ├── get_stats()  → entry count, usage %                           │ ║
║  │       └── Injection scanned, § delimited                                │ ║
║  │                                                                          │ ║
║  │  nudge_manager.py ─── NudgeManager ─── Proactive prompts                │ ║
║  │       ├── check_turn()  → memory nudge every 10 turns                   │ ║
║  │       ├── on_task_complete() → skill nudge every 5 tasks                │ ║
║  │       └── State persisted to ~/.openclaw/workspace/memory/nudge_state.json ║
║  │                                                                          │ ║
║  │  skill_manager.py ─── SkillManager ─── Procedural memory                │ ║
║  │       ├── list_skills() → scans workspace/skills/                       │ ║
║  │       └── Current skills: cti-collection, cti-alerting, mssp-ma-tracking│ ║
║  │                                                                          │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
║  memory_init.py ─── Consolidated bootstrap helper                            ║
║       from memory_init import init_all → (store, nm, sm)                    ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                    SKILLS DIRECTORY (workspace/skills/)                 │ ║
║  │                                                                          │ ║
║  │  security/cti-collection/    ← Full CTI collection pipeline               │ ║
║  │  security/cti-alerting/     ← Alert scanner + X post drafting            │ ║
║  │  financial/mssp-ma-tracking/ ← M&A deal tracking + PE positioning       │ ║
║  │  blogwatcher/               ← RSS feed monitoring                       │ ║
║  │  find-skills/                ← Skill discovery                           │ ║
║  │  news-summary/               ← News briefings                            │ ║
║  │  x-algorithm/               ← X engagement strategy                      │ ║
║  │  x-articles/                ← X long-form articles                      │ ║
║  │  proactive-agent/            ← WAL Protocol, Working Buffer, Crons      │ ║
║  │  humanizer/                  ← AI text humanizer                         │ ║
║  │                                                                              │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                    DAILY NOTES (memory/YYYY-MM-DD.md)                   │ ║
║  │  Session logs, decisions, learnings, status reports                       │ ║
║  │  Alert queue: ~/.openclaw/workspace/memory/alert-queue.md              │ ║
║  │  Seen alerts dedup: ~/.openclaw/workspace/memory/.seen_alerts.json    │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                    │
                    │ (proactive collection / alerting)
                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    CTI STACK (~/cti-workspace/)                              ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                    DJANGO CTI PLATFORM (port 8000)                      │ ║
║  │  Models: IOC, CVE, ThreatActor, ATTACKTechnique, ThreatAlert, Sector    │ ║
║  │  DB: ~/cti-workspace/data/cti/cti.db (SQLite)                           │ ║
║  │  Web UI pages:                                                          │ ║
║  │    /intel/              → Dashboard        [200]                       │ ║
║  │    /intel/cves/         → CVE list         [200]                       │ ║
║  │    /intel/actors/       → Threat actors    [200]                       │ ║
║  │    /intel/iocs/         → IOC list         [200] (was 500, fixed)      │ ║
║  │    /intel/alerts/       → Threat alerts    [200]                       │ ║
║  │    /intel/techniques/   → ATT&CK matrix    [200]                       │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                    COLLECTORS (~/cti-workspace/collect_*.py)           │ ║
║  │                                                                          │ ║
║  │  cron: 0 6 * * *  → CISA KEV          (gov confirmed exploitation)    │ ║
║  │  cron: 0 7 * * *  → NVD CVE           (vulnerability database)         │ ║
║  │  cron: 0 7 * * *  → Ransomware        (group + victim IOCs)            │ ║
║  │  cron: 0 7 * * *  → CybersecurityDive (industry news)                  │ ║
║  │  cron: 0 7 * * *  → THN               (The Hacker News)                │ ║
║  │  cron: 0 7 * * *  → CSHub             (Cybersecurity Hub)              │ ║
║  │  cron: 0 7 * * *  → DataBreaches      (breach tracking)                │ ║
║  │  cron: 0 7 * * *  → IC3 CSA           (FBI cybercrime alerts)          │ ║
║  │  cron: 0 8 * * *  → AlienVault OTX    (25 pulses/day)                  │ ║
║  │  cron: 0 9 * * *  → IOC linker       (actor ←→ IOC association)        │ ║
║  │  cron: 0 */4 * * * → threat_alert.py  (generates alert drafts)         │ ║
║  │  cron: 0 23 * * 5  → EPSS CSV import  (exploitation probability)       │ ║
║  │                                                                              │ ║
║  │  Manual / on-demand:                                                     │ ║
║  │    sti_workflow.py        → Full collection + STI workflow              │ ║
║  │    update_attck_mappings.py → CVE → ATT&CK technique linking            │ ║
║  │    backfill_nvd.py        → Historical CVE enrichment                   │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                    THREAT ALERT PIPELINE (threat_alert.py)              │ ║
║  │                                                                          │ ║
║  │  Triggers:                                                               │ ║
║  │    • CVSS >= 9.0 (4hr window)                                           │ ║
║  │    • CISA KEV additions (4hr window)                                    │ ║
║  │    • Threat actor activity (3+ new IOCs, 4hr window)                   │ ║
║  │    • DIB-relevant IOCs (notes contains [DIB])                           │ ║
║  │    • High EPSS >= 0.85 (90-day publication window, no fallback)         │ ║
║  │                                                                              │ ║
║  │  Output: ~/.openclaw/workspace/memory/alert-queue.md                    │ ║
║  │  Deduplication: ~/.openclaw/workspace/memory/.seen_alerts.json         │ ║
║  │  Post templates: FIRST CTI-SIG confidence + source reliability ratings  │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │                    DARK WEB OBSERVATORY                                  │ ║
║  │  ~/cti-workspace/darkweb-observatory/                                  │ ║
║  │                                                                              │ ║
║  │  advanced_scanner.py → Scans 361 onion targets via Tor (9050)          │ ║
║  │    cron: 0 8,20 * * * → Twice daily at 8 AM / 8 PM CDT                 │ ║
║  │    Last run: 2026-03-30 13:13 UTC | 87 UP / 257 DOWN / 17 other       │ ║
║  │                                                                              │ ║
║  │  Targets: ransomware leak sites, markets, forums, government, news       │ ║
║  │  Dashboard: ~/cti-workspace/darkweb-observatory/output/html/index.html  │ ║
║  │  Data: uptime_history.json, change_history.json, deep_scan_results.json │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
╚═══════════════════════════════════════════════════════════════════════════════╝
                    │
                    ▼
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    EXTERNAL SERVICES                                          ║
║                                                                              ║
║  X.com (@Deuslogica) ───── xurl post "text" (OAuth1 pre-auth)               ║
║  Tor Network (9050) ──────── Dark web scanning                                ║
║  CISA KEV API ────────────── Government exploitation database                 ║
║  NVD/NIST ────────────────── National Vulnerability Database                  ║
║  FIRST.org EPSS ───────────── Exploitation probability scores                 ║
║  AlienVault OTX ───────────── Threat intelligence pulses                      ║
║  SEC EDGAR ────────────────── Financial filings (M&A tracking)                ║
╚═══════════════════════════════════════════════════════════════════════════════╝

---

## 2. Storage Topology

```
HOT TIER (SSD)
~/.openclaw/workspace/          Primary agent workspace
  SOUL.md, MEMORY.md, USER.md    Identity + long-term memory
  AGENTS.md, HEARTBEAT.md        Operational directives
  BOOT.md                        Gateway startup hook
  memory_init.py                  Module bootstrap helper
  memory/                        Daily notes, alert queue, Python modules
    enhanced_memory.py
    nudge_manager.py
    skill_manager.py
    alert-queue.md
    .seen_alerts.json
    YYYY-MM-DD.md                Session logs
  skills/                        Agent skills (procedural knowledge)
  drafts/                        Content drafts (pre-approval)
  notes/                         Project notes, trackers
~/cti-workspace/                 CTI platform
  intel/                         Django app (models, views)
  templates/intel/               Web UI templates
  data/cti/cti.db               SQLite CTI database
  data/cti/*.log                Collection + alert logs
  collect_*.py                   Data collectors
  threat_alert.py                Alert pipeline
  darkweb-observatory/           Dark web scanner

COLD TIER (HDD /media/rolandpg/USB-HDD/)
  Archive of large files, backups
```

---

## 3. Cron Schedule (Local Time — America/Chicago)

```
06:00 ┬─ CISA KEV collector
      ├─ sti_workflow.py (full collection + STI)
      ├─ IC3 CSA collector
      └─ openclaw-memory-daily.timer (systemd)

07:00 ┬─ NVD CVE collector
      ├─ Ransomware collector
      ├─ Cybersecurity Dive collector
      ├─ THN collector
      ├─ CSHub collector
      ├─ DataBreaches collector
      └─ OTX collector (AlienVault, 25 pulses)

08:00 ├─ IOC linker (90-day keyword association)
      ├─ Dark web observatory scan ← NEW

09:00 └─ (IOC linking continued)

12:00 └─ Engagement block: X.com check + replies

18:00 └─ Engagement block: X.com review + next-day prep

20:00 └─ Dark web observatory scan ← NEW

23:00 ┬─ EPSS CSV import
      └─ openclaw-memory-weekly.timer (systemd, Friday only)

*/4h  └─ threat_alert.py (alert queue + dedup check)
```

---

## 4. Module Boot Sequence

```
Gateway Start
    │
    ▼
boot-md hook → BOOT.md
    │
    ├─ EnhancedMemoryStore → health check
    ├─ NudgeManager → stats
    ├─ SkillManager → list skills
    ├─ CTI DB → count records
    ├─ Web endpoints → HTTP status
    ├─ Systemd timers → status
    └─ Disk space + git status

Agent Session Start (per AGENTS.md)
    │
    ├─ Read SOUL.md
    ├─ from memory_init import init_all
    │     └─ (store, nm, sm) = init_all()
    ├─ Read MEMORY.md + USER.md (main session only)
    ├─ Read memory/YYYY-MM-DD.md (today + yesterday)
    └─ Check for pending nudges
```

---

## 5. Alert Flow

```
CTI Feed (CISA KEV / NVD / OTX / Ransomware / etc.)
    │
    ▼
Collector Scripts (cron 6-9 AM)
    │
    ▼
Django CTI Database (cti.db)
    │
    ▼
threat_alert.py (every 4 hours via cron)
    │
    ├─ check_high_cvss_cves()    → CVSS >= 9.0, 4hr window
    ├─ check_kev_additions()     → KEV recently updated
    ├─ check_actor_activity()    → 3+ new IOCs, 4hr window
    ├─ check_dib_breaches()      → [DIB] tag in notes
    └─ check_high_epss()         → EPSS >= 0.85, 90-day window
              │
              ▼
         save_draft() → deduplication check
              │
              ├─ (new) → append to alert-queue.md
              │              │
              │              ▼
              │         Telegram trigger (pending-alert.json)
              │
              └─ (seen) → skip
```

---

## 6. Key Files Reference

| File | Purpose |
|------|---------|
| `~/.openclaw/workspace/SOUL.md` | Patton identity and operating directives |
| `~/.openclaw/workspace/MEMORY.md` | Long-term memory (12 entries, bounded) |
| `~/.openclaw/workspace/USER.md` | Patrick Roland profile |
| `~/.openclaw/workspace/AGENTS.md` | Agent boot sequence and workspace conventions |
| `~/.openclaw/workspace/HEARTBEAT.md` | Periodic self-improvement checklist |
| `~/.openclaw/workspace/BOOT.md` | Gateway startup hook (runs on boot-md) |
| `~/.openclaw/workspace/memory_init.py` | Consolidated module bootstrap |
| `~/cti-workspace/threat_alert.py` | Alert pipeline with deduplication |
| `~/cti-workspace/darkweb-observatory/advanced_scanner.py` | Dark web onion scanner |
| `~/.openclaw/workspace/memory/alert-queue.md` | Pending X post drafts |
| `~/.openclaw/workspace/memory/.seen_alerts.json` | Deduplication tracking |

---

*Last updated: 2026-03-30*
*Owner: Patton (patton@roland.fleet)*
