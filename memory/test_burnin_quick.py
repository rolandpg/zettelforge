#!/usr/bin/env python3
"""
Quick burn-in test to verify vector_retriever fix
Tests 5 CVE ingestions to confirm the error is resolved
"""
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')
sys.path.insert(0, '/home/rolandpg/cti-workspace')

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ctidb.settings')

import django
django.setup()

from burnin_harness import BurnInHarness
from memory_manager import get_memory_manager
from intel.models import CVE

print("Testing burn-in with 5 CVEs...")
print()

mm = get_memory_manager()
harness = BurnInHarness(
    mm=mm,
    log_dir="/home/rolandpg/.openclaw/workspace/memory/burnin/logs",
    report_dir="/home/rolandpg/.openclaw/workspace/memory/burnin/reports"
)

cves = CVE.objects.filter(is_in_kev=True).order_by('-published')[:5]

success = 0
errors = 0

for cve in cves:
    content = f"""CVE: {cve.cve_id}
Vendor: {cve.vendor or 'Unknown'}
Product: {cve.product or 'Unknown'}
CVSS Score: {cve.cvss_score or 'N/A'}
EPSS Score: {cve.epss_score or 'N/A'}
In CISA KEV: {'Yes' if cve.is_in_kev else 'No'}

Description:
{cve.description or 'No description available'}
"""
    
    result = harness.ingest(
        content=content,
        source_type="cisa_advisory",
        source_ref=cve.cve_id,
        source_url=f"https://nvd.nist.gov/vuln/detail/{cve.cve_id}"
    )
    
    if result.status == "created":
        success += 1
        print(f"✓ {cve.cve_id}: CREATED")
    elif result.status == "duplicate_skipped":
        success += 1
        print(f"✓ {cve.cve_id}: DUPLICATE (already exists)")
    else:
        errors += 1
        print(f"✗ {cve.cve_id}: ERROR - {result.error}")

print()
print(f"Results: {success} succeeded, {errors} errors")
print()

if errors == 0:
    print("✅ Burn-in test PASSED - vector_retriever import is fixed!")
    sys.exit(0)
else:
    print("❌ Burn-in test FAILED - errors still present")
    sys.exit(1)
