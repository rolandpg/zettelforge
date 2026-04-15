#!/bin/bash
# Record the ZettelForge demo as an asciinema cast file.
# Run this from the repo root: bash scripts/record-demo.sh
#
# Prerequisites:
#   sudo apt install asciinema
#   pip install asciinema-agg  # for GIF conversion
#
# After recording, convert to GIF:
#   agg docs/assets/demo.cast docs/assets/demo.gif --cols 80 --rows 24

set -e
CAST_FILE="docs/assets/demo.cast"
mkdir -p docs/assets

echo "Recording demo to $CAST_FILE ..."
echo "The demo will run automatically. Just watch."
echo ""

asciinema rec "$CAST_FILE" \
  --cols 80 \
  --rows 24 \
  --title "ZettelForge Demo — CTI Agentic Memory" \
  --command "PYTHONPATH=src python3 -m zettelforge demo"

echo ""
echo "Recording saved to $CAST_FILE"
echo ""
echo "Convert to GIF:"
echo "  pip install asciinema-agg"
echo "  agg $CAST_FILE docs/assets/demo.gif --cols 80 --rows 24"
