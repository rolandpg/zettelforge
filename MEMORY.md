# MEMORY.md - Long-Term Memory

§
Patton. Strategic Operations Agent for Patrick Roland. CISSP, CCP. Navy nuclear vet. Voice: direct, no emoji, cite sources.
§
X.com pre-authenticated via xurl (OAuth1). Command: xurl post "text". Account: @Deuslogica. Path: ~/.npm-global/lib/node_modules/@xdevplatform/xurl/cli.js
§
Target market: DoD tier 2-4 suppliers, CMMC-mandated orgs with limited internal security. CTI focus: DIB threats.
§
Key threat actors: MOIS (Handala Hack ID 49, MuddyWater), China-Nexus (Volt Typhoon, APT28/29), Ransomware (backup/BCP), Supply chain (IT service providers). Briefing: memory/briefings/handala-hack-20260329.md
§
CTI pipeline: 9 collectors (CISA KEV, NVD, DataBreaches, Ransomware, OTX, THN, Cybersecurity Dive, IC3 CSA, STIX/TAXII). Schedule: 6AM CISA KEV, 7AM NVD+Ransomware, 8AM OTX, 9AM IOC linking. Scripts: ~/cti-workspace/collect_*.py
§
Storage: Hot SSD (/home/rolandpg/.openclaw/workspace/), Cold HDD (/media/rolandpg/USB-HDD/).
§
X.com strategy: Threat intel threads perform best (3.4% engagement). Reply chains > broadcasts. Priority: CVE/KEV > APT > MSSP ops.
§
CTI platform: Django on port 8000. DB: ~/cti-workspace/data/cti/cti.db. Dashboard: ~/cti-workspace/darkweb-observatory/output/html/index.html
§
Systemd timers: ~/.config/systemd/user/. Daily 06:00 CDT, weekly Friday 23:00 CDT. Service files must be COPIED (not symlinked).
§
Hermes Agent: ~/hermes-agent. Nousnet: ~/nousnet. Security assessments complete. Checklist: notes/hermes-learning-checklist.md
§
Key learnings: xurl auth = OAuth1 pre-configured. Django models: check field names first. Systemd: copy service files. CISA KEV: 1551 entries.
§
Hermes learning phases 1-3: EnhancedMemoryStore (bounded 2200 chars, § delimited, injection scanned), NudgeManager, SkillManager (skills/ dir).
