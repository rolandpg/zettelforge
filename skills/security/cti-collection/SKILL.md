---
name: cti-collection
description: Run the full CTI collection pipeline
category: security
created: 2026-03-29T20:24:00
updated: 2026-03-29T20:24:00
---

# CTI Collection

## When to Use
Run the full CTI collection pipeline

## Procedure
1. cd ~/cti-workspace
2. Run collectors in order:
   - 6 AM: CISA KEV (collect_cisa_kev.py)
   - 7 AM: NVD + DataBreaches + Ransomware + THN
   - 8 AM: OTX pulses
   - 9 AM: IOC linking + threat_alert.py
3. Check CTI platform at http://localhost:8000/intel/
4. Review alert queue for HIGH/CRITICAL alerts
5. Draft X posts for high-priority threats

## Examples
- python3 collect_cisa_kev.py

## References
- CTI platform: http://localhost:8000/intel/
- Scripts: ~/cti-workspace/collect_*.py
