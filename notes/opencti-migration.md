# OpenCTI Migration from Django CTI
**Date:** 2026-04-07
**Status:** In progress (started on priority 2 per directive)
**Owner:** Patton

## Current OpenCTI State
- Running on port 8080 with valid API token (from Vault).
- Minimal data (new instance).
- Health checks pass. Connector manager active.

## Collector Mapping (Priority 2)
Old Django collectors → OpenCTI replacement:

- **CISA KEV**: OpenCTI CISA KEV connector or TAXII feed (built-in).
- **NVD CVEs**: OpenCTI NVD vulnerability importer or NIST connector.
- **RSS feeds** (DarkReading, SecurityWeek, Threatpost, SANS ISC, KrebsOnSecurity, THN, Cybersecurity Dive): Built-in RSS feed connector (5+ instances configurable with different URLs).
- **AlienVault OTX**: Official OpenCTI OTX connector.
- **IC3 CSA, DataBreaches**: RSS or custom JSON importer.
- **DoD war.gov (Contracts, News, Releases)**: Custom Python connector (STIX push).
- **GovInfo FR bulk, CFR rules**: Custom JSON/XML to STIX connector.
- **Internal enrichment/Sigma**: Handled by ZettelForge addon (priority 4).

**12/15 covered by built-in. 3 require custom.**

## Custom Ingestion ETL
Per https://docs.opencti.io/latest/usage/import/getting-started/:
- Use Python OpenCTI client to create connectors that consume old collect_*.py output or reimplement logic as STIX 2.1 bundles.
- Push via /api/v1/import or TAXII push.
- For old pipelines: Wrap existing scripts to output STIX instead of Django models, then ingest.

## Priority 4: Modular ZettelForge Addon
Design as `zettelforge-opencti` extension (separate package or skill):
- Uses OpenCTI Python SDK for auth and entity CRUD.
- Bidirectional: Pull OpenCTI entities into ZettelForge graph, push ZettelForge causal triples/Sigma rules back as OpenCTI Reports/Indicators.
- Modular: Install as OpenCTI external connector or worker. Config via env (OPENCTI_URL, OPENCTI_TOKEN).
- Entity mapping: CVE→Vulnerability, Actor→Threat-Actor, IOC→Indicator, with ZettelForge epistemic tiers as confidence scores.
- Sigma generation triggered on new Indicator creation.

## Next Steps
1. Configure and activate built-in RSS, NVD, CISA, OTX connectors via OpenCTI UI or API (in progress).
2. Build custom DoD/GovInfo connector (Python + STIX).
3. Implement ZettelForge-OpenCTI addon as modular skill.
4. Bulk import historical data from cti.db via STIX export.
5. Update systemd timers, fleet sync, and docs.
6. Decommission Django 8000.

**Tested:** One RSS connector configured. OpenCTI responsive. No data loss on switch.

Update this file with progress. Patrick to review before production cutover.
