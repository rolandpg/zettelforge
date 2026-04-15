---
title: "Configure OpenCTI Integration"
description: "Connect ZettelForge Enterprise to an OpenCTI instance for bi-directional threat intelligence sync using pycti. Pull attack patterns, intrusion sets, malware, indicators, vulnerabilities, and reports; push notes and annotations back to OpenCTI."
diataxis_type: "how-to"
audience: "CTI platform engineers connecting ZettelForge Enterprise to an OpenCTI deployment"
tags: [opencti, pycti, stix, integration, sync, threat-intelligence, enterprise]
last_updated: "2026-04-14"
version: "2.1.1"
---

# Configure OpenCTI Integration

Connect ZettelForge Enterprise to an OpenCTI instance for bi-directional STIX 2.1 sync. Pull threat intelligence from OpenCTI into ZettelForge memory; push ZettelForge notes and analyst annotations back to OpenCTI as reports.

The sync client uses [pycti](https://github.com/OpenCTI-Platform/client-python) and supports all six STIX Domain Object (SDO) types, preserves structured fields (TLP markings, STIX confidence, CVSS v3/v4, EPSS), and deduplicates on re-sync so re-running the same pull is always safe.

## Prerequisites

- **ZettelForge Enterprise** installed (`pip install zettelforge-enterprise`)
- **Enterprise license** set via `THREATENGRAM_LICENSE_KEY`
- **OpenCTI** running and reachable (self-hosted or cloud, v6.x+)
- **pycti** installed: `pip install pycti`
- An OpenCTI API token with read access for pull operations; write access for push

> [!NOTE]
> OpenCTI integration is an Enterprise feature. It is not available in ZettelForge Community. To check your edition, run `python -c "from zettelforge.edition import get_edition; print(get_edition())"`.

## Steps

### 1. Obtain your OpenCTI API token

In the OpenCTI web interface, navigate to **Settings → Security → Users**, open your user profile, and copy the API key from the **API Access** section.

The token has the same permissions as the user account it belongs to. For a read-only pull, a user with the `KNOWLEDGE` role is sufficient. For push operations, the user also needs the `KNOWLEDGE_KNUPDATE` permission.

### 2. Set environment variables

The minimum required configuration is the OpenCTI URL and your API token:

```bash
export OPENCTI_URL="http://localhost:8080"
export OPENCTI_TOKEN="your-api-token-here"
```

Verify connectivity before proceeding:

```python
from pycti import OpenCTIApiClient

client = OpenCTIApiClient(
    url="http://localhost:8080",
    token="your-api-token-here",
)
print(client.health_check())  # True
```

Expected output: `True`

If you see `ConnectionRefusedError`, check that OpenCTI is reachable at the URL and that the token is valid.

### 3. Configure via config.yaml

For persistent configuration, add the `opencti` block to your `config.yaml`:

```yaml
opencti:
  url: http://localhost:8080
  token: ""            # Leave blank — set via OPENCTI_TOKEN env var
  sync_interval: 3600  # Seconds between automatic syncs (0 = manual only)
```

> [!TIP]
> Keep `token: ""` in `config.yaml` and supply the value via `OPENCTI_TOKEN`. This prevents the token from being committed to version control. `config.yaml` is already in `.gitignore`.

Environment variables take priority over `config.yaml` values. See [Configuration Reference](../reference/configuration.md) for the full precedence order.

### 4. Pull threat intelligence from OpenCTI

The sync client pulls six SDO types in a single call. Each entity type maps to structured ZettelForge note fields:

| OpenCTI Entity | ZettelForge Entity Type | Structured Fields Preserved |
|----------------|------------------------|-----------------------------|
| Attack Pattern | `attack_pattern` | MITRE ATT&CK ID, tactic, description |
| Intrusion Set  | `intrusion_set` | Primary motivation, resource level, aliases |
| Malware        | `malware` | Malware types, implementation languages, is_family |
| Indicator      | `indicator` | STIX pattern, valid_from, valid_until, confidence |
| Vulnerability  | `vulnerability` | CVSS v3 score + vector, EPSS score, CISA KEV flag |
| Report         | `report` | Publication date, confidence, object_refs |

All entities also receive `tlp` (TLP marking from OpenCTI's marking definitions) and `stix_confidence` (STIX integer 0–100) from the source object.

```python
from zettelforge.integrations.opencti import OpenCTISync

sync = OpenCTISync()

# Pull all six entity types (safe to re-run — deduplicates by STIX ID)
result = sync.pull()

print(f"Attack patterns:  {result.counts['attack_pattern']}")
print(f"Intrusion sets:   {result.counts['intrusion_set']}")
print(f"Malware:          {result.counts['malware']}")
print(f"Indicators:       {result.counts['indicator']}")
print(f"Vulnerabilities:  {result.counts['vulnerability']}")
print(f"Reports:          {result.counts['report']}")
print(f"Skipped (dupes):  {result.skipped}")
```

To pull a specific entity type only:

```python
# Pull only vulnerabilities
result = sync.pull(entity_types=["vulnerability"])
print(f"Vulnerabilities pulled: {result.counts['vulnerability']}")

# Pull attack patterns and malware
result = sync.pull(entity_types=["attack_pattern", "malware"])
```

### 5. Pull threat actors

Threat actors in OpenCTI map to the `threat-actor` STIX type, which is distinct from `intrusion-set`. ZettelForge stores both and preserves the distinction to avoid misattribution.

```python
from zettelforge.integrations.opencti import OpenCTISync
from zettelforge.memory_manager import MemoryManager

sync = OpenCTISync()
mm = MemoryManager()

# Pull threat actors specifically
result = sync.pull(entity_types=["threat_actor"])
print(f"Threat actors pulled: {result.counts['threat_actor']}")

# Verify they are queryable
notes = mm.recall_actor("APT28", k=5)
print(f"Notes found for APT28: {len(notes)}")
for note in notes:
    print(f"  [{note.metadata.tlp or 'unclassified'}] {note.content.raw[:80]}")
```

### 6. Pull reports

Reports pull as a note per report, with the report's publication date as the note's temporal anchor and the full report description as the content. Object references are stored as entity mentions in the knowledge graph.

```python
result = sync.pull(entity_types=["report"])
print(f"Reports pulled: {result.counts['report']}")

# Synthesize across pulled reports
from zettelforge.memory_manager import MemoryManager
mm = MemoryManager()
answer = mm.synthesize(
    "What are the most recent threat actor campaigns targeting financial sector?",
    format="synthesized_brief"
)
print(answer)
```

### 7. Push notes to OpenCTI

Push ZettelForge notes back to OpenCTI as reports. Notes are exported as STIX 2.1 report objects with the note content as the report description, the source domain as a label, and any extracted entities as `object_refs`.

```python
from zettelforge.memory_manager import MemoryManager
from zettelforge.integrations.opencti import OpenCTISync

mm = MemoryManager()
sync = OpenCTISync()

# Store a note locally first
note, _ = mm.remember(
    content="Sandworm deployed a new wiper variant targeting Ukrainian energy infrastructure in Q1 2026.",
    domain="cti",
    source_type="analyst_report",
)

# Push the note to OpenCTI as a report
opencti_id = sync.push_note(note)
print(f"Published to OpenCTI: {opencti_id}")
```

To push all notes created since a specific date:

```python
from datetime import datetime, timezone

# Push all notes from the last 7 days
result = sync.push_since(
    since=datetime(2026, 4, 7, tzinfo=timezone.utc),
    domain="cti",
)
print(f"Pushed {result.pushed} notes, skipped {result.skipped} already published")
```

### 8. Verify entity counts after sync

After a pull, verify the expected entities are present in ZettelForge:

```python
from zettelforge.memory_manager import MemoryManager

mm = MemoryManager()
stats = mm.stats()

print(f"Total notes: {stats['total_notes']}")
print(f"Graph nodes: {stats['graph_nodes']}")
print(f"Graph edges: {stats['graph_edges']}")

# Check entity breakdown
for entity_type, count in stats.get("entity_counts", {}).items():
    print(f"  {entity_type}: {count}")
```

Query a specific entity type to confirm the pull worked:

```python
# Check that attack patterns arrived
from zettelforge.memory_manager import MemoryManager

mm = MemoryManager()
results = mm.recall("MITRE ATT&CK phishing spearphishing attachment", k=5)

for note in results:
    confidence = note.metadata.stix_confidence
    tlp = note.metadata.tlp or "unclassified"
    print(f"[{tlp}] confidence={confidence} {note.content.raw[:100]}")
```

To verify vulnerability fields specifically:

```python
results = mm.recall_cve("CVE-2024-1111", k=3)

for note in results:
    if note.metadata.vuln:
        v = note.metadata.vuln
        print(f"CVSS v3:  {v.cvss_v3_score} ({v.cvss_v3_vector})")
        print(f"EPSS:     {v.epss_score:.4f} ({v.epss_percentile:.0%} percentile)")
        print(f"CISA KEV: {v.cisa_kev}")
```

### 9. Enable automatic sync

Set `sync_interval` in `config.yaml` to have ZettelForge pull from OpenCTI on a schedule:

```yaml
opencti:
  url: http://localhost:8080
  token: ""
  sync_interval: 3600  # Pull every hour
```

Verify the scheduler is running:

```python
from zettelforge.integrations.opencti import OpenCTISync

sync = OpenCTISync()
print(f"Auto-sync enabled: {sync.scheduler_active}")
print(f"Sync interval:     {sync.sync_interval}s")
print(f"Last sync:         {sync.last_sync_at}")
print(f"Next sync:         {sync.next_sync_at}")
```

To disable automatic sync without changing `config.yaml`:

```bash
export OPENCTI_SYNC_INTERVAL=0
```

## Troubleshooting

### `OpenCTIEnterpriseError: license not active`

```bash
# Verify your license key is set
echo $THREATENGRAM_LICENSE_KEY

# Check the edition
python -c "from zettelforge.edition import get_edition; print(get_edition())"
```

The output should be `enterprise`. If it prints `community`, `pip install zettelforge-enterprise` and set the license key.

### `pycti.exceptions.OpenCTIApiException: 401 Unauthorized`

The token is invalid or expired. In OpenCTI, navigate to **Settings → Security → Users**, open your user, and regenerate the API key.

### `ConnectionRefusedError` on `sync.pull()`

```bash
# Check OpenCTI is running
curl -f http://localhost:8080/health

# Confirm the URL matches your OpenCTI deployment
echo $OPENCTI_URL
```

For Docker-based OpenCTI deployments, the default port is `8080`. Cloud deployments use HTTPS on port 443 — set `OPENCTI_URL=https://your-tenant.opencti.io`.

### Duplicate notes after re-sync

The sync client deduplicates on the STIX `id` field. If you are seeing duplicates, check whether the source OpenCTI objects have changed IDs (for example, after a migration). Re-sync with the `force_dedup=True` flag to recheck all IDs:

```python
result = sync.pull(force_dedup=True)
print(f"Deduplication pass: {result.deduplicated} merged")
```

### Entities missing TLP or confidence after pull

TLP and confidence fields are only populated when the source OpenCTI object has marking definitions or a confidence value set. Objects with no marking definition in OpenCTI arrive with `tlp: ""` (unclassified). Objects with no confidence value arrive with `stix_confidence: -1`.

To filter out unclassified notes from synthesis:

```python
results = mm.recall("APT28", k=20)
classified = [n for n in results if n.metadata.tlp in ("GREEN", "AMBER", "RED")]
```

## LLM Quick Reference

**Task**: Connect ZettelForge Enterprise to OpenCTI for bi-directional threat intelligence sync.

**Prerequisites**: `pip install zettelforge-enterprise pycti`. Enterprise license via `THREATENGRAM_LICENSE_KEY`. OpenCTI v6.x+ running and reachable.

**Config**: `OPENCTI_URL` (default `http://localhost:8080`), `OPENCTI_TOKEN` (required, no default). `config.yaml` key: `opencti.sync_interval` (seconds, `0` = disabled).

**Pull**: `OpenCTISync().pull()` syncs all six entity types. `pull(entity_types=["vulnerability"])` targets a single type. Deduplicates on STIX `id` — safe to re-run. `pull(force_dedup=True)` for a full dedup pass.

**Supported entity types**: `attack_pattern`, `intrusion_set`, `threat_actor`, `malware`, `indicator`, `vulnerability`, `report`.

**Structured fields preserved**: `tlp` (TLP marking label), `stix_confidence` (0–100 integer, -1 if unset), `vuln.cvss_v3_score`, `vuln.cvss_v3_vector`, `vuln.epss_score`, `vuln.epss_percentile`, `vuln.cisa_kev`.

**Push**: `sync.push_note(note)` publishes a single ZettelForge note to OpenCTI as a STIX report. `sync.push_since(since=datetime(...))` batch-pushes notes by date range.

**Verify**: `mm.stats()` returns `total_notes`, `graph_nodes`, `graph_edges`, `entity_counts`. `mm.recall_cve()` with `note.metadata.vuln` confirms CVSS/EPSS fields.

**Auto-sync**: `opencti.sync_interval: 3600` in `config.yaml` enables hourly pulls. Disable with `OPENCTI_SYNC_INTERVAL=0`.
