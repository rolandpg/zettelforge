#!/usr/bin/env python3
"""
Hybrid Honcho Test - Remote Honcho with Local Ollama
Troubleshooting version.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import requests

print("=== Honcho Hybrid Test (Remote + Local Ollama) ===")
print("Current time: 2026-04-06 10:25 CDT")

load_dotenv('.env.honcho.hybrid')

api_key = os.getenv("HONCHO_API_KEY")
base_url = os.getenv("HONCHO_BASE_URL", "https://api.honcho.dev")

print(f"API Key (first 20 chars): {api_key[:20]}...")
print(f"Base URL: {base_url}")

# Test 1: Basic HTTP connection to health endpoint
print("\n1. Testing health endpoint...")
try:
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{base_url}/health", headers=headers, timeout=10)
    print(f"Health check status: {response.status_code}")
    print(f"Health response: {response.text}")
except Exception as e:
    print(f"Health check failed: {e}")

# Test 2: Try the SDK
print("\n2. Testing SDK...")
try:
    from honcho.client import Honcho
    client = Honcho(
        api_key=api_key,
        base_url=base_url
    )
    peers = client.peers()
    print(f"✅ SDK connected. Found {len(peers.data)} peers.")
except Exception as e:
    print(f"❌ SDK test failed: {e}")

print("\nTest completed.")
print("If you see 'Forbidden', the API key is not authorized for this instance.")
print("Please provide the correct API endpoint from your Honcho account dashboard.")
