#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/rolandpg/cti-workspace')
import subprocess

collectors = [
    'collect_cisa_kev.py',
    'collect_nvd_cve.py', 
    'collect_ransomware.py',
    'collect_otx.py',
    'collect_thn.py',
    'collect_rss.py'
]

print("=== Morning CTI Collection ===")
for collector in collectors:
    print(f"\nRunning {collector}...")
    try:
        result = subprocess.run(
            ['python3', f'/home/rolandpg/cti-workspace/{collector}'],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print(f"  ✓ Success")
            if result.stdout:
                print(f"  {result.stdout.strip()[-100:]}")
        else:
            print(f"  ✗ Failed: {result.stderr[:100]}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n=== Collection Complete ===")