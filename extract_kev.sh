#!/bin/bash
set -e

FILE="$HOME/.openclaw/workspace/memory/alert-queue.md"
OUTPUT_FILE="$HOME/.openclaw/workspace/drafts/2026-03-30-1200-engagement-thread.md"

# Get the line numbers of KEV_ADDITION
LINE_NUMS=$(grep -n "Type: KEV_ADDITION" "$FILE" | cut -d: -f1)

# Reverse the line numbers and take the first 5 (most recent)
REVERSED_LINE_NUMS=$(echo "$LINE_NUMS" | tac)
LAST_FIVE=$(echo "$REVERSED_LINE_NUMS" | head -5)

# We'll collect the alerts
ALERTS=""

for LINE in $LAST_FIVE; do
    # Extract from this line to the next line that is "---" (exclusive of the "---" line)
    # We use sed to print from LINE to the line before the next "---"
    ALERT=$(sed -n "${LINE},/^---$/{/^---$/q;p}" "$FILE")
    # Append the alert to ALERTS, separated by a newline and then a divider if we want
    ALERTS="${ALERTS}${ALERT}---"$'\n'
done

# Write the output to the output file
echo -e "$ALERTS" > "$OUTPUT_FILE"