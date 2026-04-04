# Check Point Research — Feed Collection Status

**Status:** Cloudflare blocks direct RSS/REST API access
**Workaround:** Use `ollama_web_fetch` on individual article URLs

## Collection Strategy

Check Point Research articles are collected when Patrick shares them or when I proactively fetch known research URLs.

RSS feed URL: `https://research.checkpoint.com/feed/`
- Returns 202 Accepted with empty body (Cloudflare JS challenge blocking)

## Known Research URLs (2026)

### Threat Research
- [ ] https://research.checkpoint.com/2026/handala-hack-unveiling-groups-modus-operandi/ ✓ INGESTED
- [ ] https://research.checkpoint.com/2026/the-turkish-rat-evolved-adwind-in-a-massive-ongoing-phishing-campaign/
- [ ] https://research.checkpoint.com/2026/the-next-wannacry-vulnerability-is-here/

### Global Cyber Attack Reports
- [ ] (Check Point publishes weekly global attack reports)

### Older Research (worth reviewing)
- [ ] Check Point 2025 Handala initial report
- [ ] Check Point Void Manticore / Scarred Manticore reports

## Manual Collection Command

To collect a new Check Point article:
```
/fetch https://research.checkpoint.com/2026/article-slug/
```

Then run in CTI workspace:
```bash
cd /home/rolandpg/cti-workspace
python3 -c "
from intel.models import ThreatActor
from collect_checkpoint import ingest_url
actor = ThreatActor.objects.get(slug='checkpoint-research')
ingest_url('https://research.checkpoint.com/...', actor)
"
```

## Actor Created
- **Slug:** checkpoint-research
- **Type:** RESEARCH
- **Risk Level:** MEDIUM
- **Description:** Check Point Software Technologies threat intelligence and research division

## Last Collection
- 2026-03-21: Handala Hack MO report ingested (27 IOCs, full ATT&CK mapping)
