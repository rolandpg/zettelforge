#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

# Run the burnin script with limit=5
from burnin_ingest_real_data import main

# Simulate command line args
sys.argv = ['burnin_ingest_real_data.py', '--limit', '5', '--source', 'all']
main()