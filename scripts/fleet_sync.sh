#!/bin/bash
# Fleet Daily Sync — Patton writes morning status
# Runs: 07:00 CDT daily

DATE=$(date +%Y-%m-%d)

# Read Tamara's sync if it exists
TAMARA_SYNC="$HOME/.openclaw/workspace-tamara/fleet/tamara_daily.md"
if [ -f "$TAMARA_SYNC" ]; then
    echo "=== Tamara's Sync ===" 
    cat "$TAMARA_SYNC"
    echo ""
fi

# Write Patton's daily sync
PATTON_SYNC="$HOME/.openclaw/workspace/fleet/patton_daily.md"
cat > "$PATTON_SYNC" << EOF
# Patton Daily Sync
**Date:** $DATE

## CTI Findings
-

## Infrastructure Alerts
-

## Strategy Shifts
-

## Open Items for Tamara
-

## Notes
EOF

echo "Fleet sync complete: $DATE"
