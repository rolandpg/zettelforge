#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace/memory')

from burnin_ingest_real_data import main
sys.argv = ['burnin_ingest_real_data.py', '--limit', '10', '--source', 'all']
main()