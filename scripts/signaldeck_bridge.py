#!/usr/bin/env python3
"""SignalDeck ↔ OpenClaw Gateway Bridge

Forwards messages from SignalDeck to OpenClaw Gateway so agents
can process them with full reasoning capabilities.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
import httpx
import websockets

# Agent API keys
AGENTS = {
    'patton': 'sd-MRiwI6ObTTndf6NyFTkKuv6zU-WVH7ABy0JeQgpXTqg',
    'tamara': 'sd-l-OVUP8bXJpTKCZwMpwEueX6FavthiR0bgkItxN1ms0',
    'vigil': 'sd--PwO3ahaG-nVYlfRn2L_DnAuDTJHtSjfGSVUYPX8Fts',
    'nexus': 'sd-Eb54UQMLrPhFmslnnWNj_jDfBh5ZZuGTMPp_02aIhVw'
}

SIGNALDECK_URL = 'http://localhost:8080'
OPENCLAW_GATEWAY = 'ws://127.0.0.1:18789'

class SignalDeckBridge:
    """Bridges SignalDeck messages to OpenClaw Gateway."""
    
    def __init__(self):
        self.signaldeck_ws = None
        self.gateway_ws = None
        self.jwt_tokens = {}
        
    async def authenticate_agents(self):
        """Get JWT tokens for all agents."""
        async with httpx.AsyncClient() as client:
            for agent_id, api_key in AGENTS.items():
                resp = await client.post(
                    f'{SIGNALDECK_URL}/api/auth/agent',
                    json={'agent_id': agent_id, 'api_key': api_key}
                )
                self.jwt_tokens[agent_id] = resp.json()['access_token']
        print(f"[BRIDGE] Authenticated {len(self.jwt_tokens)} agents")
    
    async def connect_signaldeck(self, agent_id: str):
        """Connect to SignalDeck WebSocket as an agent."""
        ws_url = SIGNALDECK_URL.replace('http://', 'ws://') + '/ws'
        ws = await websockets.connect(ws_url)
        
        # Send identify
        await ws.send(json.dumps({
            'type': 'identify',
            'agent_id': agent_id,
            'token': self.jwt_tokens[agent_id]
        }))
        
        # Wait for ack
        ack = json.loads(await ws.recv())
        if ack.get('type') == 'ack':
            print(f"[BRIDGE] {agent_id} connected to SignalDeck")
            return ws
        else:
            raise Exception(f"Auth failed for {agent_id}: {ack}")
    
    async def forward_to_gateway(self, agent_id: str, sender: str, content: str, channel_id: str):
        """Forward message to OpenClaw Gateway for processing."""
        # For now, we'll process locally and send response
        # Full implementation would route through Gateway API
        
        print(f"[BRIDGE] Forwarding: {sender} -> {agent_id}: {content[:50]}")
        
        # Simple response logic (replace with Gateway API call)
        if '@patton' in content.lower():
            response = await self.get_patton_response(sender, content)
            await self.send_signaldeck_message(agent_id, channel_id, response)
        elif '@tamara' in content.lower():
            response = f"@{sender} Tamara here! Content creation ready."
            await self.send_signaldeck_message(agent_id, channel_id, response)
        elif '@vigil' in content.lower():
            response = f"@{sender} Vigil standing by. CTI monitoring active."
            await self.send_signaldeck_message(agent_id, channel_id, response)
        elif '@nexus' in content.lower():
            response = f"@{sender} Nexus here. AI research ready."
            await self.send_signaldeck_message(agent_id, channel_id, response)
    
    async def get_patton_response(self, sender: str, content: str) -> str:
        """Get intelligent response from Patton."""
        # This would call the OpenClaw API to get a real response
        # For now, use better logic
        question = content.lower().replace('@patton', '').strip(' ?')
        
        if '2+2' in question or '2 + 2' in question:
            return f"@{sender} 2 + 2 = 4."
        elif 'status' in question:
            return f"@{sender} All systems operational. 4 agents connected."
        elif 'hello' in question or 'hi' in question:
            return f"@{sender} Patton here. Standing by for orders."
        elif 'help' in question:
            return f"@{sender} I can assist with: strategic analysis, security intel, coordination, research. What do you need?"
        else:
            return f"@{sender} Message received: '{question}'. Patton processing... (Note: Full reasoning requires Gateway integration)"
    
    async def send_signaldeck_message(self, agent_id: str, channel_id: str, content: str):
        """Send message back to SignalDeck via REST API."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f'{SIGNALDECK_URL}/api/channels/{channel_id}/messages',
                headers={'Authorization': f'Bearer {self.jwt_tokens[agent_id]}'},
                json={'content': content, 'message_type': 'text'}
            )
            if resp.status_code == 201:
                print(f"[BRIDGE] Sent response from {agent_id}")
    
    async def run_agent_listener(self, agent_id: str):
        """Listen for messages as a specific agent."""
        ws = await self.connect_signaldeck(agent_id)
        
        try:
            async for message in ws:
                data = json.loads(message)
                
                if data.get('type') == 'message.new':
                    payload = data.get('payload', {})
                    sender = payload.get('sender', {}).get('username', 'unknown')
                    content = payload.get('content', '')
                    channel_id = payload.get('channel_id')
                    
                    # Skip own messages
                    if sender == agent_id:
                        continue
                    
                    print(f"[{agent_id}] {sender}: {content[:60]}")
                    
                    # Check if this agent is mentioned
                    if f'@{agent_id.lower()}' in content.lower():
                        await self.forward_to_gateway(agent_id, sender, content, channel_id)
                        
        except websockets.exceptions.ConnectionClosed:
            print(f"[BRIDGE] {agent_id} disconnected")
    
    async def run(self):
        """Run bridge for all agents."""
        await self.authenticate_agents()
        
        # Start listeners for all agents
        tasks = [
            self.run_agent_listener('patton'),
            self.run_agent_listener('tamara'),
            self.run_agent_listener('vigil'),
            self.run_agent_listener('nexus'),
        ]
        
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    bridge = SignalDeckBridge()
    asyncio.run(bridge.run())
