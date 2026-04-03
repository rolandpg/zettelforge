#!/usr/bin/env python3
"""
Real CTI Data Ingestion for 30-Day Burn-In Test
================================================

This script ingests actual threat intelligence data from the Roland Fleet
CTI pipeline into the ThreatRecall memory system for burn-in testing.

Data Sources:
- Django CTI Database (90K+ IOCs, 1,558 CVEs, 31 Actors, 4 Alerts)
- DIB Advisories (CSAF format, daily since 2026-03-19)
- CISA KEV Catalog
- NVD CVE Feed

Usage:
    python3 burnin_ingest_real_data.py [--limit N] [--source all|cisa|nvd|alerts|actors]

Author: Patton (Roland Fleet)
Date: 2026-04-02
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
MEMORY_DIR = Path("/home/rolandpg/.openclaw/workspace/memory")
CTI_DIR = Path("/home/rolandpg/cti-workspace")
sys.path.insert(0, str(MEMORY_DIR))
sys.path.insert(0, str(CTI_DIR))

from burnin_harness import BurnInHarness
from memory_manager import get_memory_manager

# Django setup for CTI database
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ctidb.settings')
sys.path.insert(0, str(CTI_DIR))


def setup_django():
    """Initialize Django ORM for CTI database access."""
    import django
    django.setup()


def ingest_cves_from_django(harness, limit=100):
    """Ingest CVEs from Django CTI database."""
    from intel.models import CVE
    
    print(f"\n[1/4] Ingesting CVEs from Django database (limit: {limit})...")
    count = 0
    errors = 0
    
    cves = CVE.objects.all().order_by('-published')[:limit]
    
    for cve in cves:
        try:
            # Build rich content from CVE data
            content = f"""CVE: {cve.cve_id}
Vendor: {cve.vendor or 'Unknown'}
Product: {cve.product or 'Unknown'}
CVSS Score: {cve.cvss_score or 'N/A'}
EPSS Score: {cve.epss_score or 'N/A'}
In CISA KEV: {'Yes' if cve.is_in_kev else 'No'}

Description:
{cve.description or 'No description available'}

References:
{cve.references or 'No references'}
"""
            
            result = harness.ingest(
                content=content,
                source_type="cisa_advisory" if cve.is_in_kev else "nvd_entry",
                source_ref=cve.cve_id,
                source_url=f"https://nvd.nist.gov/vuln/detail/{cve.cve_id}"
            )
            
            if result.status in ("created", "duplicate_skipped"):
                count += 1
                if count % 10 == 0:
                    print(f"      Progress: {count}/{limit} CVEs ingested")
            else:
                errors += 1
                
        except Exception as e:
            errors += 1
            print(f"      Error ingesting {cve.cve_id}: {e}")
    
    print(f"      ✓ CVE ingestion complete: {count} succeeded, {errors} errors")
    return count, errors


def ingest_threat_actors_from_django(harness, limit=31):
    """Ingest Threat Actors from Django CTI database."""
    from intel.models import ThreatActor
    
    print(f"\n[2/4] Ingesting Threat Actors from Django database...")
    count = 0
    errors = 0
    
    actors = ThreatActor.objects.all()[:limit]
    
    for actor in actors:
        try:
            content = f"""Threat Actor: {actor.name}

Description:
{actor.description or 'No description available'}

Known Aliases:
{actor.aka or 'No aliases recorded'}

Origin:
{actor.origin or 'Unknown'}

Motivation:
{actor.motivation or 'Unknown'}
"""
            
            result = harness.ingest(
                content=content,
                source_type="threat_report",
                source_ref=f"actor-{actor.name.lower().replace(' ', '-')}"
            )
            
            if result.status in ("created", "duplicate_skipped"):
                count += 1
            else:
                errors += 1
                
        except Exception as e:
            errors += 1
            print(f"      Error ingesting {actor.name}: {e}")
    
    print(f"      ✓ Actor ingestion complete: {count} succeeded, {errors} errors")
    return count, errors


def ingest_threat_alerts_from_django(harness, limit=10):
    """Ingest Threat Alerts from Django CTI database."""
    from intel.models import ThreatAlert
    
    print(f"\n[3/4] Ingesting Threat Alerts from Django database...")
    count = 0
    errors = 0
    
    alerts = ThreatAlert.objects.all()[:limit]
    
    for alert in alerts:
        try:
            content = f"""ALERT: {alert.title}
Severity: {alert.severity or 'Unknown'}
Type: {alert.alert_type or 'General'}
Published: {alert.published_at or 'Unknown'}

Summary:
{alert.summary or 'No summary available'}

Details:
{alert.details or 'No details available'}
"""
            
            result = harness.ingest(
                content=content,
                source_type="cisa_advisory",
                source_ref=f"alert-{alert.id}",
                source_url=None
            )
            
            if result.status in ("created", "duplicate_skipped"):
                count += 1
            else:
                errors += 1
                
        except Exception as e:
            errors += 1
            print(f"      Error ingesting alert {alert.id}: {e}")
    
    print(f"      ✓ Alert ingestion complete: {count} succeeded, {errors} errors")
    return count, errors


def ingest_dib_advisories(harness, limit=20):
    """Ingest DIB Advisories from CSAF JSON files."""
    print(f"\n[4/4] Ingesting DIB Advisories from CSAF files (limit: {limit})...")
    
    advisory_dir = CTI_DIR / "data" / "cti"
    advisories = sorted(advisory_dir.glob("dib_advisory_*.json"))[:limit]
    
    count = 0
    errors = 0
    
    for adv_file in advisories:
        try:
            with open(adv_file, 'r') as f:
                data = json.load(f)
            
            doc = data.get('document', {})
            title = doc.get('title', 'Unknown Advisory')
            tracking = doc.get('tracking', {})
            adv_id = tracking.get('id', 'unknown')
            
            # Extract vulnerability info
            vulns = data.get('vulnerabilities', [])
            vuln_details = []
            for v in vulns:
                cve = v.get('cve', 'Unknown')
                title = v.get('title', 'No title')
                vuln_details.append(f"- {cve}: {title}")
            
            content = f"""DIB ADVISORY: {title}
Advisory ID: {adv_id}
Date: {tracking.get('current_release_date', 'Unknown')}
TLP: {doc.get('distribution', {}).get('tlp', 'Unknown')}

Vulnerabilities:
{'\n'.join(vuln_details) if vuln_details else 'None listed'}

Publisher: {doc.get('publisher', {}).get('name', 'Unknown')}
"""
            
            result = harness.ingest(
                content=content,
                source_type="cisa_advisory",
                source_ref=adv_id
            )
            
            if result.status in ("created", "duplicate_skipped"):
                count += 1
            else:
                errors += 1
                
        except Exception as e:
            errors += 1
            print(f"      Error ingesting {adv_file.name}: {e}")
    
    print(f"      ✓ Advisory ingestion complete: {count} succeeded, {errors} errors")
    return count, errors


def ingest_iocs_sample(harness, limit=50):
    """Ingest a sample of IOCs from Django database."""
    from intel.models import IOC
    
    print(f"\n[Bonus] Ingesting IOC sample (limit: {limit})...")
    count = 0
    errors = 0
    
    # Get diverse IOC types
    iocs = IOC.objects.all()[:limit]
    
    for ioc in iocs:
        try:
            content = f"""IOC: {ioc.value}
Type: {ioc.ioc_type}
Threat Type: {ioc.threat_type or 'Unknown'}
First Seen: {ioc.first_seen or 'Unknown'}
Last Seen: {ioc.last_seen or 'Unknown'}
"""
            
            result = harness.ingest(
                content=content,
                source_type="otx_pulse",
                source_ref=f"ioc-{ioc.id}"
            )
            
            if result.status in ("created", "duplicate_skipped"):
                count += 1
            else:
                errors += 1
                
        except Exception as e:
            errors += 1
            # Silently continue for IOCs (there are 90K+)
    
    print(f"      ✓ IOC ingestion complete: {count} succeeded, {errors} errors")
    return count, errors


def main():
    parser = argparse.ArgumentParser(description='Real CTI Data Ingestion for Burn-In')
    parser.add_argument('--limit', type=int, default=100, help='Limit per source (default: 100)')
    parser.add_argument('--source', type=str, default='all', 
                       choices=['all', 'cves', 'actors', 'alerts', 'advisories', 'iocs'],
                       help='Data source to ingest (default: all)')
    args = parser.parse_args()
    
    print("=" * 70)
    print("ThreatRecall 30-Day Burn-In — Real CTI Data Ingestion")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)
    
    # Initialize Django for CTI database
    print("\n[0/4] Initializing Django ORM for CTI database...")
    setup_django()
    print("      ✓ Django initialized")
    
    # Initialize memory manager and harness
    print("\n[0/4] Initializing ThreatRecall memory system...")
    mm = get_memory_manager()
    harness = BurnInHarness(
        mm=mm,
        log_dir="/home/rolandpg/.openclaw/workspace/memory/burnin/logs",
        report_dir="/home/rolandpg/.openclaw/workspace/memory/burnin/reports"
    )
    print(f"      ✓ Memory system ready")
    print(f"      Current note count: {len(list(mm.store.iterate_notes()))}")
    
    # Track totals
    total_ingested = 0
    total_errors = 0
    
    # Ingest based on source selection
    if args.source in ['all', 'cves']:
        c, e = ingest_cves_from_django(harness, limit=args.limit)
        total_ingested += c
        total_errors += e
    
    if args.source in ['all', 'actors']:
        c, e = ingest_threat_actors_from_django(harness, limit=31)
        total_ingested += c
        total_errors += e
    
    if args.source in ['all', 'alerts']:
        c, e = ingest_threat_alerts_from_django(harness, limit=10)
        total_ingested += c
        total_errors += e
    
    if args.source in ['all', 'advisories']:
        c, e = ingest_dib_advisories(harness, limit=20)
        total_ingested += c
        total_errors += e
    
    if args.source in ['all', 'iocs']:
        c, e = ingest_iocs_sample(harness, limit=min(args.limit, 100))
        total_ingested += c
        total_errors += e
    
    # Generate summary
    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)
    
    summary = harness.daily_summary()
    
    print(f"\nTotal Items Ingested: {total_ingested}")
    print(f"Total Errors: {total_errors}")
    print(f"Success Rate: {(total_ingested / (total_ingested + total_errors) * 100):.1f}%")
    
    print(f"\nPerformance Summary:")
    print(f"  - Avg latency: {summary.get('avg_latency_ms', 0):.0f}ms")
    print(f"  - Notes created: {summary.get('notes_created', 0)}")
    print(f"  - Duplicates skipped: {summary.get('duplicates_skipped', 0)}")
    
    print(f"\nFinal note count: {len(list(mm.store.iterate_notes()))}")
    print(f"\nLogs saved to: {harness.log_dir}")
    print(f"Reports saved to: {harness.report_dir}")
    
    print("\n" + "=" * 70)
    print(f"Completed: {datetime.now().isoformat()}")
    print("=" * 70)
    
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    exit(main())
