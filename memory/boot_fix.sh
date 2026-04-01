#!/bin/bash
# One-shot CTI server restart + boot verification
# Run: bash /home/rolandpg/.openclaw/workspace/memory/boot_fix.sh

set -e

LOG="/tmp/boot_fix.log"
echo "=== Boot Fix $(date) ===" >> $LOG

# 1. Kill any stale CTI server
echo "[1] Killing stale CTI server..." >> $LOG
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1

# 2. Start CTI server properly daemonized
echo "[2] Starting CTI server..." >> $LOG
cd /home/rolandpg/cti-workspace
nohup python3 manage.py runserver 0.0.0.0:8000 >> /tmp/cti-server.log 2>&1 &
CTI_PID=$!
echo "CTI PID: $CTI_PID" >> $LOG
sleep 4

# 3. Verify CTI web server
echo "[3] Checking CTI web server..." >> $LOG
for page in /intel/ /intel/cves/ /intel/actors/ /intel/iocs/ /intel/alerts/ /intel/techniques/; do
    code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000$page)
    echo "  $page: $code" >> $LOG
done

# 4. Fix DJANGO_SETTINGS_MODULE in boot_check.py
echo "[4] Fixing boot_check.py..." >> $LOG
cd /home/rolandpg/.openclaw/workspace
python3 << 'PYEOF' >> $LOG 2>&1
import sys
sys.path.insert(0, 'memory')

# Fix the CTI DB section in boot_check.py
with open('memory/boot_check.py', 'r') as f:
    content = f.read()

old_block = """# 2a. CTI DB
try:
    import os
    os.chdir('/home/rolandpg/cti-workspace')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'ctidb.settings'
    import django
    django.setup()"""

new_block = """# 2a. CTI DB
try:
    import os
    os.chdir('/home/rolandpg/cti-workspace')
    import django
    import sys
    sys.path.insert(0, '/home/rolandpg/cti-workspace')
    django.setup()"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('memory/boot_check.py', 'w') as f:
        f.write(content)
    print("boot_check.py fixed")
else:
    print("boot_check.py already fixed or unexpected format")

PYEOF

# 5. Run full boot check
echo "[5] Running boot check..." >> $LOG
python3 memory/boot_check.py >> $LOG 2>&1

# 6. Show results
echo "" >> $LOG
echo "=== RESULTS ===" >> $LOG
cat $LOG | tail -30
