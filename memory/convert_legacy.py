#!/usr/bin/env python3
"""
Convert legacy MEMORY.md/USER.md to §-delimited format
"""

import re
from pathlib import Path

def distill_memory(content: str) -> list:
    """Convert legacy MEMORY.md entries to §-delimited format."""
    entries = []
    
    # Key facts to preserve as compact entries
    key_facts = [
        "X.com pre-authenticated via xurl (OAuth1). Command: xurl post \"text\". Account: @Deuslogica. Path: ~/.npm-global/lib/node_modules/@xdevplatform/xurl/cli.js",
        "Name: Patton. Role: Strategic Operations Agent for Patrick Roland. Voice: Direct, no emoji, cite sources, lead with the take",
        "Target market: DoD tier 2-4 suppliers, CMMC-mandated orgs with limited internal security. CTI focus: DIB threats",
        "Key threat actors: MOIS (Handala Hack, MuddyWater), China-Nexus (Volt Typhoon, APT28/29), Ransomware (backup/BCP failures), Supply chain (IT service providers)",
        "CTI pipeline: 9 collectors (CISA KEV, NVD, DataBreaches, Ransomware, OTX, THN, Cybersecurity Dive, IC3 CSA, STIX/TAXII). Scripts in ~/cti-workspace/collect_*.py",
        "Collection schedule: 6AM CISA KEV, 7AM NVD+DataBreaches+Ransomware, 8AM OTX, 9AM IOC linking",
        "Storage tier: Hot SSD (/home/rolandpg/.openclaw/workspace/), Cold HDD (/media/rolandpg/USB-HDD/)",
        "X.com strategy: Threat intel threads perform best (3.4% engagement). Reply chains > broadcasts. Priority: CVE/KEV > APT profiles > MSSP ops",
        "Memory architecture: JSONL + LanceDB dual-write. Embedding: nomic-embed-text-v2-moe via Ollama. LLM: nemotron-3-nano",
        "CTI platform: Django on port 8000. DB: ~/cti-workspace/data/cti/cti.db. Dashboard: ~/cti-workspace/darkweb-observatory/output/html/index.html",
        "Systemd timers: ~/.config/systemd/user/. Daily at 06:00 CDT, weekly Friday 23:00 CDT",
        "Hermes Agent cloned to ~/hermes-agent. Nousnet cloned to ~/nousnet. Security assessment complete for both",
    ]
    
    # Key learnings (don't repeat)
    learnings = [
        "xurl auth: OAuth1 tokens pre-configured. Don't search for auth instructions",
        "Django models: Check field names with python3 manage.py shell -c \"from intel.models import Model; print([f.name for f in Model._meta.get_fields()])\"",
        "Systemd timers: Service files must be copied to ~/.config/systemd/user/ — symlinks don't work",
        "CISA KEV: 1551 entries, 906 DIB-relevant. NVD API 2.0: https://services.nvd.nist.gov/rest/json/cves/2.0",
        "Handala Hack: Iranian MOIS APT. Actor ID 49 in CTI DB. Briefing: memory/briefings/handala-hack-20260329.md",
        "Hermes learning system: Can integrate without privacy issues. Checklist: notes/hermes-learning-checklist.md",
    ]
    
    entries.extend(key_facts)
    entries.extend(learnings)
    
    return entries

def distill_user(content: str) -> list:
    """Convert legacy USER.md to §-delimited format."""
    entries = [
        "Name: Patrick Roland. Title: Director of SOC Services, Summit 7 Systems. Certs: CISSP, CCP. Background: Navy nuclear veteran",
        "Focus: MSSP consolidation, CMMC/DIB expertise, PE due diligence on MSSP acquisitions",
        "Target market: Mid-tier and SMB government contractors (DoD tier 2-4 suppliers), CMMC-mandated orgs with limited internal security staff",
        "Communication: Direct, no fluff, prefers actionable over explanatory. Wants proactive, not reactive. Likes to experiment",
        "Privacy priority: Prefers local-only solutions. Using Ollama, not external APIs",
        "X.com: @Deuslogica. LinkedIn: /in/patrickgroland. Content pillars: MSSP ops, CMMC/DIB, leadership, cybersecurity market analysis",
        "CTI priorities: MOIS-linked actors, China-Nexus, ransomware targeting backup failures in healthcare/local govt",
    ]
    return entries

def convert_file(input_path: Path, output_path: Path, distill_func, header: str):
    """Convert a legacy file to §-delimited format."""
    content = input_path.read_text()
    
    # Run distillation
    entries = distill_func(content)
    
    # Build new content
    lines = [header]
    for entry in entries:
        lines.append("\n§\n")
        lines.append(entry)
    
    new_content = "\n".join(lines) + "\n"
    
    # Write
    output_path.write_text(new_content)
    print(f"Converted {input_path.name}: {len(entries)} entries")

if __name__ == "__main__":
    workspace = Path("/home/rolandpg/.openclaw/workspace")
    
    # Convert MEMORY.md
    convert_file(
        workspace / "MEMORY.md.backup",
        workspace / "MEMORY.md",
        distill_memory,
        "# MEMORY.md - Long-Term Memory"
    )
    
    # Convert USER.md
    convert_file(
        workspace / "USER.md.backup",
        workspace / "USER.md",
        distill_user,
        "# USER.md - About Patrick Roland"
    )
    
    print("\nConversion complete. Backups saved with .backup extension.")
