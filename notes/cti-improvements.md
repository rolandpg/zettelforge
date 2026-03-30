# CTI Stack Improvements

Track all enhancements to the CTI pipeline here.

## 2026-03-24

### Target Market Clarified
Mid-tier and SMB government contractors — DoD tier 2-4, CMMC-mandated, limited security staff.

**This changes collection and content priorities:**
- IT/service provider supply chain compromises (Handala's exact playbook)
- Known CVEs in accessible tools (n8n, SolarWinds WHD, Fortinet, Cisco ASA, Zoho ManageEngine)
- Ransomware via backup/BCP failures
- Living-off-the-land techniques that bypass legacy signatures

### Content Strategy Update
1. CVE/KEV threads — especially CVEs in tools this population uses
2. Ransomware intel — immediate operational relevance
3. Actor profile threads — MOIS, Volt Typhoon, APT28 targeting DIB
4. MSSP ops content — operational war stories
5. CMMC policy — niche authoritative positioning
6. Reply engagement — PE/VC, CISO community, DHS/CISA

### IOC Linking Fix Approach
- OTX search returns wrong content; subscription = honeypot data
- Fix: Manual enrichment layer — cross-reference unlinked IOCs against known actor profiles
- Priority actors for this market: Handala Hack, MuddyWater, Volt Typhoon, APT28, Qilin

---

## 2026-03-21

### Added
- CTI metadata framework in threat_alert.py (confidence, source reliability A-F, calibrated language, ATT&CK mapping)
- Custom Django template filters (split, trim) for ATT&CK techniques page
- Templatetags: `intel/templatetags/cti_filters.py`
- UX QA subagent — full platform test completed, 1 critical fixed (techniques page 500)
- OTX cron fix — bash export wrapper for API key
- OTX collector — switched from subscribed pulses (honeypot data) to targeted actor/DIB searches
- OTX API endpoint fixed — `/pulses/search` → `/search/pulses`
- Pagination controls on CVEs, Actors, IOCs pages

### Fixed
- ATT&CK Techniques page HTTP 500 — Django template syntax error
- OTX cron API key not loading
- Empty actor slug ("Iran MOIS" → "iran-mois")
- threat_links field error in CVE detail view
- EPSS percentile display bug

---

## Gap Analysis — Ongoing

### High Priority (2026-03-24 Updated)
| Gap | Status | Notes |
|-----|--------|-------|
| IOC actor linking | Fix in progress | OTX broken; build manual enrichment |
| Sigma/YARA rules | Not started | 10x X post value for clients |
| Strategic CTI briefings | Not started | Executive-level, sector-specific |
| DIB-specific feeds | Not started | DCSA, IT-ISAC |

### Medium Priority
| Gap | Status | Notes |
|-----|--------|-------|
| Dark web monitoring | Not started | Shodan/Censys/GreyNoise |
| MISP integration | Not started | Contribute + consume |
| ATT&CK TTP auto-mapping | Partial | CVETechnique links exist |
| Check Point RSS | Done | Use ollama_web_fetch on article URLs |
| Feedback loop | Not started | Track IOC accuracy |
