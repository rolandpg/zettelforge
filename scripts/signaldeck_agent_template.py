#!/usr/bin/env python3
"""SignalDeck connector template for fleet agents.

Copy and customize for: tamara, vigil, nexus
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add SignalDeck SDK to path
SDK_PATH = Path("/home/rolandpg/FleetSpeak/sdk/src")
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

try:
    from signaldeck import SignalDeckClient
except ImportError:
    print("ERROR: SignalDeck SDK not found.")
    sys.exit(1)

# Configuration - customize per agent
AGENT_ID = "AGENT_NAME"  # Change to: tamara, vigil, or nexus
SIGNALDECK_URL = "http://localhost:8080"


def load_api_key() -> str:
    """Load SignalDeck API key from Vault."""
    vault_creds_path = Path.home() / f".openclaw/vault-credentials/{AGENT_ID}.json"
    
    if vault_creds_path.exists():
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "/home/rolandpg/.openclaw/workspace/scripts/vault_helper.py",
                 "read", f"local/threatrecall/{AGENT_ID}/signaldeck-apikey"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("api_key", "")
        except Exception as e:
            print(f"Warning: Could not read from Vault: {e}")
    
    raise RuntimeError(f"No API key found for {AGENT_ID}")


class AgentSignalDeckConnector:
    """SignalDeck connector for fleet agents."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.client: SignalDeckClient | None = None
        self.api_key: str | None = None
        
    async def connect(self) -> SignalDeckClient:
        """Connect to SignalDeck."""
        self.api_key = load_api_key()
        
        self.client = SignalDeckClient(
            url=SIGNALDECK_URL,
            agent_id=self.agent_id,
            api_key=self.api_key,
            heartbeat_interval=30.0,
            reconnect_max_backoff=60.0
        )
        
        await self.client._http.open()
        await self.client._ws.connect()
        self.client._ws.start_loops()
        
        self._register_handlers()
        
        print(f"[SignalDeck] {self.agent_id} connected")
        return self.client
    
    def _register_handlers(self):
        """Register message handlers."""
        
        @self.client.on("message.new")
        async def on_message(data: dict):
            sender = data.get("sender", {}).get("username", "unknown")
            content = data.get("content", "")
            
            print(f"[SignalDeck/{self.agent_id}] Message from {sender}: {content[:100]}...")
            
            # Handle @mentions
            if f"@{self.agent_id}" in content:
                await self._handle_mention(sender, content)
        
        @self.client.on("presence.changed")
        async def on_presence(data: dict):
            user = data.get("user_id", "unknown")
            status = data.get("status", "unknown")
            print(f"[SignalDeck/{self.agent_id}] {user} is {status}")
    
    async def _handle_mention(self, sender: str, content: str):
        """Handle when agent is mentioned."""
        pass  # Override in agent-specific subclass
    
    async def disconnect(self):
        """Disconnect from SignalDeck."""
        if self.client:
            await self.client._ws.disconnect()
            await self.client._http.close()
            print(f"[SignalDeck] {self.agent_id} disconnected")
    
    async def send_to_channel(self, channel: str, message: str):
        """Send a message to a channel."""
        if not self.client:
            raise RuntimeError("Not connected")
        await self.client.send_message(channel_id=channel, content=message)


# Singleton
_connector: AgentSignalDeckConnector | None = None


async def init_signaldeck(agent_id: str) -> SignalDeckClient:
    """Initialize SignalDeck connection."""
    global _connector, AGENT_ID
    AGENT_ID = agent_id
    _connector = AgentSignalDeckConnector(agent_id)
    return await _connector.connect()


async def send_message(channel: str, message: str):
    """Send a message to a channel."""
    if _connector:
        await _connector.send_to_channel(channel, message)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("agent", help="Agent ID (tamara, vigil, nexus)")
    args = parser.parse_args()
    
    async def test():
        client = await init_signaldeck(args.agent)
        await send_message("general", f"{args.agent} reporting for duty via SignalDeck.")
        await asyncio.sleep(5)
        await _connector.disconnect()
    
    asyncio.run(test())
