# MEMORY.md - Long-Term Memory

§
Key threat actors: MOIS (Handala Hack ID 49, MuddyWater), China-Nexus (Volt Typhoon, APT28/29), Ransomware (backup/BCP), Supply chain (IT service providers). Briefing: memory/briefings/handala-hack-20260329.md
§
CTI pipeline: 15 collectors (CISA KEV, NVD, DataBreaches, Ransomware, OTX, THN, Cybersecurity Dive, IC3 CSA, STIX/TAXII, RSS x5, DoD x3, GovInfo FR bulk). Schedule: 6AM CISA KEV, 7AM CFR rules + GovInfo FR bulk, 8AM NVD+Ransomware+THN+RSS. Scripts: ~/cti-workspace/collect_*.py. DoD feeds: war.gov (Contracts, News Stories, News Releases). RSS: DarkReading, SecurityWeek, Threatpost, SANS ISC, KrebsOnSecurity.
§
Storage: Hot SSD (/home/rolandpg/.openclaw/workspace/), Cold HDD (/media/rolandpg/USB-HDD/).
§
X.com strategy: Threat intel threads perform best (3.4% engagement). Reply chains > broadcasts. Priority: CVE/KEV > APT > MSSP ops. Posted AIVSS+BRICKSTORM thread (ID 2039895053120729147) 2026-04-02. Posted KEV Lag thread (ID 2040032547933962475) 2026-04-03.
§
CTI platform: Django on port 8000. DB: ~/cti-workspace/data/cti/cti.db. Dashboard: ~/cti-workspace/darkweb-observatory/output/html/index.html
§
Systemd timers: ~/.config/systemd/user/. Daily 06:00 CDT memory, 07:00 CDT fleet sync (Patton+Tamara), 07:02 CDT CFR, weekly Fri 23:00 CDT. Service files must be COPIED (not symlinked).
§
Hermes Agent: ~/hermes-agent. Nousnet: ~/nousnet. Security assessments complete. Checklist: notes/hermes-learning-checklist.md
§
Key learnings: xurl auth = OAuth1 pre-configured. Django models: check field names first. Systemd: copy service files. Fleet sync: 07:00 CDT daily — scripts/fleet_sync.sh + openclaw-fleet-sync.timer. OAuth2 for X analytics not configured — requires manual export from analytics.x.com.
§
Qualys TRU: Broken Physics of Remediation (Mar 2026) — TTE -1 day, 6.5x KEV vol, 88% defender loss. Sub-1% of CVEs weaponized. Risk Mass (exposure-days) > MTTR. Full briefing: memory/briefings/qualys-remediation-physics-20260331.md
§
HashiCorp Vault: ACTIVE (2026-04-04). Docker container `vault-dev` on host network, auto-restart. KV v2 at secret/, AppRole auth. Per-agent policies: patton, tamara, vigil, nexus (least privilege). Credentials: ~/.openclaw/vault-credentials/{agent}.json. Skills: vault-read, vault-write, vault-setup. Helper: scripts/vault_helper.py. Setup script: scripts/vault-setup.sh. Onboarding: fleet/vault_agent_onboarding.md. All agents notified and confirmed. Next: MCP server (vault-mcp-server) for direct tool integration.
§
OpenClaw Multi-Agent: Each agent has isolated workspace + agentDir + sessions. Routing via bindings (most-specific wins). Agent-to-agent messaging requires `tools.agentToAgent.enabled=true` + allowlist. Fleet pattern: shared file sync for daily summaries, `sessions_send` for urgent alerts. Current fleet: main (Patton, default), tamara (social), vigil (CTI, background), nexus (AI research). A2A enabled 2026-04-03. Full reference: notes/openclaw-multi-agent.md

Memory Architecture: Our specialized **ZettelForge** (formerly A-MEM, now in skills/zettelforge) is the primary system for CTI synthesis and entity tracking. Honcho has been deprecated due to crashes and availability issues. See: research/amem_vs_honcho_architecture_20260406.md, research/skills-ontology-20260406-updated.md
§
Hardware — DGX Spark / ASUS Ascent GX10: NVIDIA Blackwell GB10 GPU, ARM v9.2-A CPU, 128GB LPDDR5x unified memory, 7TB NVMe SSD (4TB PCIe 5.0 + 1TB + 2TB PCIe 4.0), Wi-Fi 7, 10G Ethernet, NVIDIA ConnectX-7 SmartNIC. Runs Ubuntu Linux. Capable of full fine-tuning 13B models or QLoRA up to 70B. Full specs: notes/dgx-spark-specs.md
