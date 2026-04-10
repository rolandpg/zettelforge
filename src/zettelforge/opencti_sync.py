"""
OpenCTI Sync — Continuous STIX ingestion from OpenCTI into ZettelForge.

Polls OpenCTI's GraphQL API for new/updated STIX objects and auto-ingests
them into ZettelForge memory via remember_with_extraction().

Usage:
    # One-shot sync (pull latest)
    from zettelforge.opencti_sync import sync_opencti
    stats = sync_opencti(mm)

    # Continuous polling
    from zettelforge.opencti_sync import start_sync_loop
    start_sync_loop(mm, interval_minutes=15)

Requires:
    - pip install pycti
    - OpenCTI running (default: http://localhost:8080)
    - OPENCTI_URL and OPENCTI_TOKEN env vars (or config.yaml)
"""
import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path


def _get_opencti_client():
    """Create OpenCTI API client from env or config."""
    from pycti import OpenCTIApiClient

    url = os.environ.get("OPENCTI_URL", "http://localhost:8080")
    token = os.environ.get("OPENCTI_TOKEN", "")

    if not token:
        # Try to get from Docker container — try common container names
        import subprocess
        for container in ["opencti-platform", "docker-opencti-1", "opencti-opencti-1", "opencti"]:
            try:
                result = subprocess.run(
                    ["docker", "exec", container, "printenv", "OPENCTI_TOKEN"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    token = result.stdout.strip()
                    break
            except Exception:
                continue

    if not token:
        raise ConnectionError(
            "OPENCTI_TOKEN not set. Export it or set in config.yaml.\n"
            "Find it: docker exec <opencti-container> printenv OPENCTI_TOKEN"
        )

    return OpenCTIApiClient(url, token)


# ── Rate Limiting ────────────────────────────────────────────────────────────

class RateLimiter:
    """Token bucket rate limiter for API calls and ingestion."""

    def __init__(self, calls_per_second: float = 2.0, burst: int = 5):
        self.rate = calls_per_second
        self.burst = burst
        self._tokens = float(burst)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def wait(self):
        """Block until a token is available."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate)

            if self._tokens < 1.0:
                sleep_time = (1.0 - self._tokens) / self.rate
                time.sleep(sleep_time)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


def _retry_with_backoff(fn, max_retries: int = 3, base_delay: float = 1.0):
    """Call fn() with exponential backoff on failure."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"[OpenCTI Sync] Retry {attempt + 1}/{max_retries} in {delay:.1f}s: {e}")
            time.sleep(delay)


def _get_sync_state_path() -> Path:
    """Path to sync state file (tracks last sync timestamp)."""
    from zettelforge.memory_store import get_default_data_dir
    return get_default_data_dir() / "opencti_sync_state.json"


def _load_sync_state() -> Dict:
    """Load last sync timestamp."""
    path = _get_sync_state_path()
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"last_sync": None, "synced_ids": []}


def _save_sync_state(state: Dict):
    """Save sync state."""
    path = _get_sync_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def _format_report(report: Dict) -> str:
    """Format an OpenCTI report into text for ZettelForge ingestion."""
    parts = []
    name = report.get("name", "Untitled Report")
    description = report.get("description", "")
    published = report.get("published", "")
    created_by = report.get("createdBy", {})
    author = created_by.get("name", "Unknown") if created_by else "Unknown"

    parts.append(f"# {name}")
    if published:
        parts.append(f"Published: {published[:10]}")
    parts.append(f"Author: {author}")
    if description:
        parts.append(f"\n{description}")

    # Add object labels
    labels = report.get("objectLabel", [])
    if labels:
        label_names = [l.get("value", "") for l in labels if l]
        parts.append(f"\nTags: {', '.join(label_names)}")

    return "\n".join(parts)


def _format_indicator(indicator: Dict) -> str:
    """Format an OpenCTI indicator for ingestion."""
    pattern = indicator.get("pattern", "")
    name = indicator.get("name", pattern[:80])
    valid_from = indicator.get("valid_from", "")
    description = indicator.get("description", "")
    created_by = indicator.get("createdBy", {})
    author = created_by.get("name", "Unknown") if created_by else "Unknown"

    parts = [f"Indicator: {name}"]
    if pattern:
        parts.append(f"Pattern: {pattern}")
    if valid_from:
        parts.append(f"Valid from: {valid_from[:10]}")
    parts.append(f"Source: {author}")
    if description:
        parts.append(description)

    return "\n".join(parts)


def _format_threat_actor(actor: Dict) -> str:
    """Format an OpenCTI threat actor for ingestion."""
    name = actor.get("name", "Unknown")
    description = actor.get("description", "")
    aliases = actor.get("aliases", []) or []
    sophistication = actor.get("sophistication", "")
    goals = actor.get("goals", []) or []

    parts = [f"Threat Actor: {name}"]
    if aliases:
        parts.append(f"Aliases: {', '.join(aliases)}")
    if sophistication:
        parts.append(f"Sophistication: {sophistication}")
    if goals:
        parts.append(f"Goals: {', '.join(goals)}")
    if description:
        parts.append(f"\n{description}")

    return "\n".join(parts)


def _format_malware(malware: Dict) -> str:
    """Format an OpenCTI malware for ingestion."""
    name = malware.get("name", "Unknown")
    description = malware.get("description", "")
    is_family = malware.get("is_family", False)
    malware_types = malware.get("malware_types", []) or []

    parts = [f"Malware: {name}"]
    if malware_types:
        parts.append(f"Types: {', '.join(malware_types)}")
    if is_family:
        parts.append("(Malware family)")
    if description:
        parts.append(f"\n{description}")

    return "\n".join(parts)


def _format_vulnerability(vuln: Dict) -> str:
    """Format an OpenCTI vulnerability for ingestion."""
    name = vuln.get("name", "Unknown")
    description = vuln.get("description", "")
    x_opencti_cvss_base_score = vuln.get("x_opencti_cvss_base_score", None)

    parts = [f"Vulnerability: {name}"]
    if x_opencti_cvss_base_score:
        parts.append(f"CVSS: {x_opencti_cvss_base_score}")
    if description:
        parts.append(f"\n{description[:1000]}")

    return "\n".join(parts)


def sync_opencti(
    memory_manager,
    entity_types: List[str] = None,
    since: str = None,
    limit: int = 100,
    use_extraction: bool = True,
) -> Dict:
    """
    One-shot sync: pull new/updated STIX objects from OpenCTI into ZettelForge.

    Args:
        memory_manager: ZettelForge MemoryManager instance.
        entity_types: Which types to sync. Default: reports, indicators, threat-actors, malware, vulnerabilities.
        since: ISO timestamp. Only sync objects modified after this. Default: last sync time.
        limit: Max objects per type per sync.
        use_extraction: Use remember_with_extraction() (selective) vs remember() (append-only).

    Returns:
        Dict with sync stats: {synced, skipped, errors, duration_s, by_type}
    """
    if entity_types is None:
        entity_types = ["report", "indicator", "threat-actor-group", "malware", "vulnerability"]

    api = _retry_with_backoff(_get_opencti_client)
    state = _load_sync_state()

    if since is None:
        since = state.get("last_sync")

    # Build date filter
    filters = None
    if since:
        filters = {
            "mode": "and",
            "filters": [{"key": "modified", "values": [since], "operator": "gt"}],
            "filterGroups": [],
        }

    synced = 0
    skipped = 0
    errors = 0
    by_type = {}
    synced_ids = set(state.get("synced_ids", [])[-10000:])  # Keep last 10K IDs
    start = time.perf_counter()

    # Rate limiters: API calls (2/s burst 5) and ingestion (1/s burst 3)
    api_limiter = RateLimiter(calls_per_second=2.0, burst=5)
    ingest_limiter = RateLimiter(calls_per_second=1.0, burst=3)

    formatters = {
        "report": (_fetch_reports, _format_report),
        "indicator": (_fetch_indicators, _format_indicator),
        "threat-actor-group": (_fetch_threat_actors, _format_threat_actor),
        "malware": (_fetch_malware, _format_malware),
        "vulnerability": (_fetch_vulnerabilities, _format_vulnerability),
    }

    for etype in entity_types:
        if etype not in formatters:
            continue

        fetch_fn, format_fn = formatters[etype]
        type_count = 0

        try:
            api_limiter.wait()
            objects = _retry_with_backoff(lambda: fetch_fn(api, filters=filters, limit=limit))
            for obj in objects:
                obj_id = obj.get("id", obj.get("standard_id", ""))
                if obj_id in synced_ids:
                    skipped += 1
                    continue

                content = format_fn(obj)
                if not content or len(content) < 20:
                    skipped += 1
                    continue

                try:
                    ingest_limiter.wait()
                    source_ref = f"opencti:{etype}:{obj_id}"
                    if use_extraction:
                        memory_manager.remember_with_extraction(
                            content=content,
                            source_type="opencti",
                            source_ref=source_ref,
                            domain="cti",
                        )
                    else:
                        memory_manager.remember(
                            content=content,
                            source_type="opencti",
                            source_ref=source_ref,
                            domain="cti",
                        )
                    synced += 1
                    type_count += 1
                    synced_ids.add(obj_id)
                except Exception as e:
                    errors += 1

        except Exception as e:
            print(f"[OpenCTI Sync] Error fetching {etype}: {e}")
            errors += 1

        by_type[etype] = type_count

    duration = time.perf_counter() - start

    # Save state
    state["last_sync"] = datetime.utcnow().isoformat()
    state["synced_ids"] = list(synced_ids)[-10000:]
    _save_sync_state(state)

    stats = {
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
        "duration_s": round(duration, 1),
        "by_type": by_type,
        "timestamp": state["last_sync"],
    }

    print(f"[OpenCTI Sync] Synced {synced}, skipped {skipped}, errors {errors} in {duration:.1f}s")
    for etype, count in by_type.items():
        if count > 0:
            print(f"  {etype}: {count}")

    return stats


def _fetch_reports(api, filters=None, limit=100) -> List[Dict]:
    result = api.report.list(first=limit, filters=filters, withPagination=False)
    return result if isinstance(result, list) else []


def _fetch_indicators(api, filters=None, limit=100) -> List[Dict]:
    result = api.indicator.list(first=limit, filters=filters, withPagination=False)
    return result if isinstance(result, list) else []


def _fetch_threat_actors(api, filters=None, limit=100) -> List[Dict]:
    result = api.threat_actor_group.list(first=limit, filters=filters, withPagination=False)
    return result if isinstance(result, list) else []


def _fetch_malware(api, filters=None, limit=100) -> List[Dict]:
    result = api.malware.list(first=limit, filters=filters, withPagination=False)
    return result if isinstance(result, list) else []


def _fetch_vulnerabilities(api, filters=None, limit=100) -> List[Dict]:
    result = api.vulnerability.list(first=limit, filters=filters, withPagination=False)
    return result if isinstance(result, list) else []


def start_sync_loop(
    memory_manager,
    interval_minutes: int = 15,
    entity_types: List[str] = None,
    limit: int = 50,
):
    """
    Start a background thread that polls OpenCTI every interval_minutes.

    Args:
        memory_manager: ZettelForge MemoryManager.
        interval_minutes: Polling interval (default 15 min).
        entity_types: Which types to sync.
        limit: Max objects per type per poll.
    """
    def _loop():
        while True:
            try:
                sync_opencti(
                    memory_manager,
                    entity_types=entity_types,
                    limit=limit,
                    use_extraction=False,  # Faster for continuous sync
                )
            except Exception as e:
                print(f"[OpenCTI Sync] Loop error: {e}")
            time.sleep(interval_minutes * 60)

    thread = threading.Thread(target=_loop, daemon=True, name="opencti-sync")
    thread.start()
    print(f"[OpenCTI Sync] Background sync started (every {interval_minutes}min)")
    return thread
