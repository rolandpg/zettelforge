#!/bin/bash
# Subagent Workspace Cleanup
# Removes stale subagent workspaces from /tmp
# Run via cron or systemd service

TIMEOUT_HOURS=24
TMP_DIR="/tmp"

echo "=== Subagent Workspace Cleanup ==="
echo "Timestamp: $(date -Iseconds)"
echo "Cleaning workspaces older than ${TIMEOUT_HOURS} hours..."

# Find and remove subagent workspaces
CLEANED=0
for dir in $(find $TMP_DIR -maxdepth 1 -type d -name "subagent_*" -mmin +$((TIMEOUT_HOURS * 60)) 2>/dev/null); do
    echo "Removing: $dir"
    rm -rf "$dir"
    ((CLEANED++))
done

# Also clean OpenClaw tmp directory
if [ -d "/home/rolandpg/.openclaw/workspace/tmp" ]; then
    for dir in $(find /home/rolandpg/.openclaw/workspace/tmp -maxdepth 1 -type d -name "subagent_*" -mmin +$((TIMEOUT_HOURS * 60)) 2>/dev/null); do
        echo "Removing: $dir"
        rm -rf "$dir"
        ((CLEANED++))
    done
fi

echo "Cleaned: $CLEANED workspaces"
echo "=== Cleanup Complete ==="
