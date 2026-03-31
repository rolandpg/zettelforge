---
name: cti-alerting
description: Run CTI alert pipeline and draft X posts for high-priority threats
category: security
created: 2026-03-30
updated: 2026-03-30
---

# CTI Alerting

## When to Use
Run the CTI alert pipeline to scan for high-priority threats and generate draft X posts for engagement.
This should be run after the collection cycle (every 4 hours) or manually when new threats are suspected.

## Procedure
1. cd ~/cti-workspace
2. Ensure Django settings are set: export DJANGO_SETTINGS_MODULE=ctidb.settings
3. Run the threat alert scanner: python3 threat_alert.py
4. Check the alert queue for new drafts: cat ~/.openclaw/workspace/memory/alert-queue.md
5. For any HIGH priority alerts with actionable intelligence, consider drafting an X post using the templates in HEARTBEAT.md
6. Review the draft posts in the alert queue and select those worth posting during engagement blocks (12 PM and 6 PM CST)
7. Use the xurl tool to post: xurl post "your draft text here"
8. After posting, consider archiving or marking the alert as processed to avoid duplicate posts

## Examples
- python3 threat_alert.py  # Runs the scanner and updates alert queue
- xurl post "🔴 EPSS 95.0% | Almost certainly exploitation | medium confidence\n\nCVE-2023-23752 (EPSS 95.00%)\n\nAn issue was discovered in Joomla! 4.0.0 through 4.2.7. An improper access check allows unauthorized access to webservice endpoints.\n\nHighest risk of all CVEs by exploitation likelihood\n\nSource: FIRST.org EPSS | Reliability: B\n\nLink: https://nvd.nist.gov/vuln/detail/CVE-2023-23752\n\n#EPSS #threatintel #CVE #cybersecurity"

## Gotchas
- The threat alert script includes deduplication - it will not re-alert on the same CVE/actor within the seen alerts window
- Always verify the alert queue for duplicates before posting
- The script runs every 4 hours via cron (0 */4 * * *), but can be run manually
- Ensure Tor is running if scanning dark web sources (though threat_alert.py does not currently use Tor)

## References
- Threat alert script: ~/cti-workspace/threat_alert.py
- Alert queue: ~/.openclaw/workspace/memory/alert-queue.md
- HEARTBEAT.md: Contains post templates by type (CVE/KEV, APT profile)
- X.com pre-authenticated via xurl (OAuth1): Command: xurl post "text"
- CTI platform: http://localhost:8000/intel/ for reviewing full details