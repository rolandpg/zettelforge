# MEMORY.md - Long-Term Memory

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


## Key Learnings (Updated Mar 30, 2026 - 5:38 AM CST)
1. **CTI Platform Fix**: Resolved HTTP 500 errors on /intel/iocs/ and actor detail pages by excluding threat actors with empty slugs in Django views. Applied to dashboard, cve_detail, company_detail, search, and actors views.
2. **Alert Queue**: One high-priority alert queued at 02:04 AM CST: Handala Hack actor activity (12 new IOCs). Draft post prepared for 12 PM engagement block.
3. **Collection Schedule**: 6:00 AM CISA KEV collector pending (due in ~22 minutes). All other collectors scheduled as normal.
4. **System Health**: All CTI web endpoints now return 200. Threat alert scanner running normally (last run 5:00 AM CST processed 0 new high-priority threats).

