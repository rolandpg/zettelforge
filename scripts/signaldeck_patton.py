#!/usr/bin/env python3
"""SignalDeck connector for Patton agent.

Integrates Patton with the SignalDeck communication hub.
Auto-connects on boot and provides message handlers.
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
    from signaldeck.exceptions import AuthenticationError
except ImportError:
    print("ERROR: SignalDeck SDK not found. Run from FleetSpeak directory.")
    sys.exit(1)

# Configuration
SIGNALDECK_URL = "http://localhost:8080"
AGENT_ID = "patton"

# Load API key from Vault credentials
def load_api_key() -> str:
    """Load SignalDeck API key from Vault or local storage."""
    # Try Vault first
    vault_creds_path = Path.home() / ".openclaw/vault-credentials/patton.json"
    if vault_creds_path.exists():
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "/home/rolandpg/.openclaw/workspace/scripts/vault_helper.py", 
                 "read", "local/threatrecall/patton/signaldeck-apikey"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("api_key", "")
        except Exception:
            pass
    
    # Fallback to local file (check workspace root)
    local_key_path = Path.home() / ".openclaw/workspace/.signaldeck_key"
    if local_key_path.exists():
        return local_key_path.read_text().strip()
    
    raise RuntimeError("No API key found. Check Vault or create .signaldeck_key file.")

# Store reference to active client
_active_client: SignalDeckClient | None = None


class PattonSignalDeckConnector:
    """SignalDeck connector for Patton agent."""
    
    def __init__(self):
        self.client: SignalDeckClient | None = None
        self.api_key: str | None = None
        self._channel_map: dict[str, str] = {}
        
    async def connect(self) -> SignalDeckClient:
        """Connect to SignalDeck."""
        self.api_key = load_api_key()
        
        # First, authenticate via REST API to get JWT token
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SIGNALDECK_URL}/api/auth/agent",
                json={"agent_id": AGENT_ID, "api_key": self.api_key}
            )
            if resp.status_code != 200:
                raise AuthenticationError(f"Auth failed: {resp.status_code}")
            auth_data = resp.json()
            jwt_token = auth_data["access_token"]
        
        self.client = SignalDeckClient(
            url=SIGNALDECK_URL,
            agent_id=AGENT_ID,
            api_key=jwt_token,  # Use JWT token for WebSocket auth
            heartbeat_interval=30.0,
            reconnect_max_backoff=60.0
        )
        
        await self.client._http.open()
        await self.client._ws.connect()
        self.client._ws.start_loops()
        
        # Register event handlers
        self._register_handlers()
        
        # Join default channels
        await self._join_default_channels()
        
        global _active_client
        _active_client = self.client
        
        print(f"[SignalDeck] Patton connected to {SIGNALDECK_URL}")
        return self.client
    
    def _register_handlers(self):
        """Register message handlers."""
        
        @self.client.on("message.new")
        async def on_message(data: dict):
            """Handle incoming messages."""
            payload = data.get("payload", {})
            sender = payload.get("sender", {}).get("username", "unknown")
            content = payload.get("content", "")
            channel = payload.get("channel_id", "unknown")
            
            print(f"[SignalDeck] Message from {sender}: {content[:100]}...")
            
            # Handle @patton mentions
            if f"@{AGENT_ID}" in content or f"<@{AGENT_ID}>" in content:
                await self._handle_mention(sender, content, channel)
        
        @self.client.on("presence.changed")
        async def on_presence(data: dict):
            """Handle presence changes."""
            payload = data.get("payload", {})
            user = payload.get("user_id", "unknown")
            status = payload.get("status", "unknown")
            print(f"[SignalDeck] {user} is now {status}")
    
    async def _handle_mention(self, sender: str, content: str, channel: str):
        """Handle when Patton is mentioned."""
        # Send acknowledgment
        if self.client:
            await self.client.send_message(
                channel_id=channel,
                content=f"@{sender} Acknowledged. Patton standing by."
            )
    
    async def _join_default_channels(self):
        """Join default channels - store channel ID mappings."""
        # Hardcoded channel IDs from bootstrap
        self._channel_map = {
            "general": "c494b663-8867-4e8c-8793-1971fe7674ab",
            "alerts": "4c1de042-5f77-4caf-82a3-f9d02204b46c"
        }
        print(f"[SignalDeck] Channel mappings loaded: {list(self._channel_map.keys())}")
    
    async def disconnect(self):
        """Disconnect from SignalDeck."""
        if self.client:
            await self.client._ws.disconnect()
            await self.client._http.close()
            print("[SignalDeck] Patton disconnected")
    
    async def send_to_channel(self, channel: str, message: str):
        """Send a message to a channel (by slug name or ID)."""
        if not self.client:
            raise RuntimeError("Not connected to SignalDeck")
        # Use mapped channel ID if available, otherwise assume it's already an ID
        channel_id = self._channel_map.get(channel, channel)
        await self.client.send_message(channel_id=channel_id, content=message)
    
    async def send_alert(self, message: str):
        """Send an alert to #alerts channel."""
        await self.send_to_channel("alerts", f"🚨 {message}")


# Singleton instance
_connector: PattonSignalDeckConnector | None = None


async def init_signaldeck() -> SignalDeckClient:
    """Initialize SignalDeck connection for Patton.
    
    Call this during agent boot sequence.
    """
    global _connector
    _connector = PattonSignalDeckConnector()
    return await _connector.connect()


def get_connector() -> PattonSignalDeckConnector | None:
    """Get the active connector instance."""
    return _connector


async def send_message(channel: str, message: str):
    """Send a message to a channel (convenience function)."""
    if _connector and _connector.client:
        await _connector.send_to_channel(channel, message)
    else:
        raise RuntimeError("SignalDeck not connected")


async def send_alert(message: str):
    """Send an alert to #alerts (convenience function)."""
    await send_message("alerts", f"🚨 {message}")


# Test connection if run directly
if __name__ == "__main__":
    async def test():
        try:
            client = await init_signaldeck()
            print("✅ Connected to SignalDeck")
            
            # Send test message to #general
            await send_message("general", "Patton reporting for duty. SignalDeck integration online.")
            print("✅ Test message sent to #general")
            
            # Keep connection alive for 10 seconds
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if _connector:
                await _connector.disconnect()
    
    asyncio.run(test())
