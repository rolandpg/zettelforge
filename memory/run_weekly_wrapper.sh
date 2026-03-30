#!/bin/bash
cd /home/rolandpg/.openclaw/workspace/memory
unset PYTHONHOME
export PYTHONPATH=/home/rolandpg/.openclaw/workspace/memory
HOME=/home/rolandpg /usr/bin/python3 -B weekly_maintenance.py
