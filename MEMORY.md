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
Hermes phases 1-3: EnhancedMemoryStore (bounded 2200 chars, § delimited), NudgeManager (10 turns), SkillManager (3 skills). Phase 4: MemoryManager (vector recall) wired into boot via init_all(). Similarity threshold: 0.30. Historical notes: 36 real, 11 archived. 
§
Qualys TRU: Broken Physics of Remediation (Mar 2026) - TTE -1 day, 6.5x KEV vol, 88% defender loss. Sub-1% of CVEs weaponized. Risk Mass (exposure-days) > MTTR. ROC = embedded intel + exploit confirmation + autonomous remediation. Briefing: memory/briefings/qualys-remediation-physics-20260331.md
§
OPUS research notes on memory system implementations: Entity-first (regex/named lists) > pure semantic for structured cybersecurity domains. Key gaps identified: (1) Actor alias resolution — MuddyWater/Mercury/TEMP.Zagros creates phantom duplicates. (2) Epistemic tiering — separate Tier A human facts from Tier B agent inferences from Tier C summaries. (3) Cold archive deferral risk — all systems that skipped it had to retrofit under pressure. (4) Reasoning memory — capture why links are made, not just what was linked. (5) Self-updating entity lists from notes themselves. Source: OPUS landscape analysis via Patrick.
