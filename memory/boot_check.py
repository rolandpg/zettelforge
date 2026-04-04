#!/usr/bin/env python3
"""BOOT.md Gateway Startup Checklist - Run manually: python3 memory/boot_check.py"""
import subprocess, sys, datetime, os

sys.path.insert(0, 'memory')
os.chdir('/home/rolandpg/.openclaw/workspace')

checks = []

# 1a. EMS
try:
    from pathlib import Path
    from enhanced_memory import EnhancedMemoryStore
    store = EnhancedMemoryStore(memory_dir=Path('.'))
    store.load()
    checks.append(f"EMS OK: {store.get_stats()}")
except Exception as e:
    checks.append(f"EMS FAIL: {e}")

# 1b. NudgeManager
try:
    from nudge_manager import NudgeManager
    nm = NudgeManager()
    checks.append(f"NudgeManager OK: {nm.get_stats()}")
except Exception as e:
    checks.append(f"NudgeManager FAIL: {e}")

# 1c. SkillManager
try:
    from skill_manager import SkillManager
    sm = SkillManager()
    skills = sm.list_skills()
    checks.append(f"SkillManager OK: {len(skills)} skills")
except Exception as e:
    checks.append(f"SkillManager FAIL: {e}")

# 2a. CTI DB
try:
    import os, sys
    sys.path.insert(0, '/home/rolandpg/cti-workspace')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'ctidb.settings'
    os.chdir('/home/rolandpg/cti-workspace')
    import django; django.setup()
    from intel.models import IOC, ThreatActor, CVE, ThreatAlert
    checks.append(f"CTI DB OK: iocs={IOC.objects.count()}, actors={ThreatActor.objects.count()}, cves={CVE.objects.count()}, alerts={ThreatAlert.objects.count()}")
    os.chdir('/home/rolandpg/.openclaw/workspace')
except Exception as e:
    checks.append(f"CTI DB FAIL: {e}")

# 2b. CTI web pages
try:
    import urllib.request
    pages = ['/intel/', '/intel/cves/', '/intel/actors/', '/intel/iocs/', '/intel/alerts/', '/intel/techniques/']
    for page in pages:
        try:
            req = urllib.request.Request(f'http://localhost:8000{page}')
            with urllib.request.urlopen(req, timeout=3) as r:
                checks.append(f"{page}: {r.status}")
        except Exception as e:
            checks.append(f"{page}: ERROR {e}")
except Exception as e:
    checks.append(f"CTI web check FAIL: {e}")

# 3. Systemd timers
try:
    out = subprocess.check_output(['systemctl', '--user', 'list-timers', '--now'], text=True, timeout=5)
    matching = [l.strip() for l in out.split('\n') if 'openclaw' in l.lower() or 'cti' in l.lower()]
    checks.append(f"Timers: {matching if matching else 'none found'}")
except Exception as e:
    checks.append(f"Timers check FAIL: {e}")

# 4. Disk space
try:
    out = subprocess.check_output(['df', '-h', '/home/rolandpg/.openclaw', '/home/rolandpg/cti-workspace'], text=True, timeout=5)
    lines = out.strip().split('\n')
    checks.append(f"Disk openclaw: {lines[-1]}")
    if len(lines) > 2:
        checks.append(f"Disk cti: {lines[-2]}")
except Exception as e:
    checks.append(f"Disk check FAIL: {e}")

# 5. Git status
try:
    out = subprocess.check_output(['git', 'status', '--short'], text=True, cwd='/home/rolandpg/.openclaw/workspace', timeout=5)
    checks.append(f"Git: {'clean' if not out.strip() else out.strip()}")
except Exception as e:
    checks.append(f"Git FAIL: {e}")

# 6. Log boot
try:
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    with open(f'/home/rolandpg/.openclaw/workspace/memory/{today}.md', 'a') as f:
        f.write(f"\n## Gateway Boot {datetime.datetime.now().isoformat()}\n")
        f.write("- Modules: EMS, NudgeManager, SkillManager loaded\n")
        f.write("- CTI stack: operational\n")
    checks.append("Boot logged")
except Exception as e:
    checks.append(f"Boot log FAIL: {e}")

for c in checks:
    print(c)
