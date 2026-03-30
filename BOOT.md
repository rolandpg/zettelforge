# BOOT.md — Gateway Startup Checklist

_Runs automatically via `boot-md` hook on gateway start._

## Mission

Verify all core systems are operational. Log startup. Flag anything that needs attention.

---

## 1. Python Module Health Check

Run the following health checks in sequence. Report any failures.

### EnhancedMemoryStore
```bash
cd ~/.openclaw/workspace && python3 -c "
import sys
sys.path.insert(0, 'memory')
from pathlib import Path
from enhanced_memory import EnhancedMemoryStore
store = EnhancedMemoryStore(memory_dir=Path('.'))
store.load()
stats = store.get_stats()
print('EMS OK:', stats)
"
```

### NudgeManager
```bash
cd ~/.openclaw/workspace && python3 -c "
import sys
sys.path.insert(0, 'memory')
from nudge_manager import NudgeManager
nm = NudgeManager()
stats = nm.get_stats()
print('NudgeManager OK:', stats)
"
```

### SkillManager
```bash
cd ~/.openclaw/workspace && python3 -c "
import sys
sys.path.insert(0, 'memory')
from skill_manager import SkillManager
sm = SkillManager()
skills = sm.list_skills()
print(f'SkillManager OK: {len(skills)} skills loaded')
for s in skills[:5]:
    print(f'  - {s.identifier}')
"
```

---

## 2. CTI Stack Health

### Django CTI DB
```bash
cd ~/cti-workspace && DJANGO_SETTINGS_MODULE=ctidb.settings python3 -c "
import django
django.setup()
from intel.models import IOC, ThreatActor, CVE, ThreatAlert
print('CTI DB OK:', {
    'iocs': IOC.objects.count(),
    'actors': ThreatActor.objects.count(),
    'cves': CVE.objects.count(),
    'alerts': ThreatAlert.objects.count()
})
" 2>/dev/null || echo 'CTI DB check skipped (Django init failed)'
```

### CTI Web Server
```bash
for page in /intel/ /intel/cves/ /intel/actors/ /intel/iocs/ /intel/alerts/ /intel/techniques/; do
  code=\$(curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8000\$page 2>/dev/null)
  echo \"\$page: \$code\"
done
```

---

## 3. Systemd Timers

```bash
systemctl --user list-timers --now 2>/dev/null | grep -E 'openclaw|cti' || echo "Timers: check manually with systemctl --user list-timers --all"
```

---

## 4. Disk Space

```bash
df -h ~/.openclaw ~/cti-workspace 2>/dev/null | tail -2
```

---

## 5. Git Status (Workspace)

```bash
cd ~/.openclaw/workspace && git status --short 2>/dev/null | head -10
```

---

## 6. Log Boot

Append to today's daily notes:

```bash
echo "" >> ~/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
echo "## Gateway Boot \$(date -Iseconds)" >> ~/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
echo "- Modules: EMS, NudgeManager, SkillManager loaded" >> ~/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
echo "- CTI stack: operational" >> ~/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
```

---

## Completion

If all checks pass: reply with ONLY `NO_REPLY` (suppresses any output).

If anything fails: reply with the failure details so the human can address it.
