# vault-read — Read Secrets from HashiCorp Vault

## Description

Read secrets from HashiCorp Vault using AppRole authentication. Part of the Roland Fleet secrets management infrastructure per GOV-014.

## Prerequisites

- HashiCorp Vault must be running (`docker ps | grep vault-dev`)
- AppRole credentials must be configured at `~/.openclaw/vault-credentials/{agent}.json`
- Vault must have KV v2 enabled at `secret/`

## Path Convention

Per GOV-014: `{environment}/{service}/{agent}/{secret-name}`

Examples:
- `local/threatrecall/patton/api-key`
- `production/threatrecall/tenant-acme/api-key`
- `local/threatrecall/tamara/content-schedule`

## Usage

### Read a Secret

```python
import hvac

CREDS_FILE = Path.home() / ".openclaw" / "vault-credentials" / "patton.json"

with open(CREDS_FILE) as f:
    creds = json.load(f)

client = hvac.Client(url=creds["vault_addr"])
client.auth.approle.login(
    role_id=creds["role_id"],
    secret_id=creds["secret_id"],
)

result = client.secrets.kv.v2.read_secret_version(
    path="local/threatrecall/patton/test",
    mount_point="secret",
)
value = result["data"]["data"]["value"]
```

### Read with Async

```python
import asyncio
import json
from pathlib import Path
import hvac

async def read_secret(path: str) -> str:
    creds_file = Path.home() / ".openclaw" / "vault-credentials" / "patton.json"
    with open(creds_file) as f:
        creds = json.load(f)
    
    client = hvac.Client(url=creds["vault_addr"])
    client.auth.approle.login(role_id=creds["role_id"], secret_id=creds["secret_id"])
    
    def _read():
        return client.secrets.kv.v2.read_secret_version(path=path, mount_point="secret")
    
    result = await asyncio.to_thread(_read)
    return result["data"]["data"]["value"]
```

### CLI

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=patton-vault-dev-root  # dev only — use AppRole in production

# Read
vault kv get secret/data/local/threatrecall/patton/my-secret
```

## Skills Protocol

Skill name: `vault-read`
Inputs: `path` (string, required) — the secret path within `secret/data/`
Outputs: `value` (string) — the secret value

## Error Handling

- `FileNotFoundError`: Credentials file missing — run vault setup
- `hvac.exceptions.VaultDown`: Vault not reachable — check container
- `hvac.exceptions.Forbidden`: AppRole credentials invalid or expired
- `VaultNamespaceMismatch`: Wrong namespace — not applicable in homelab

## Agent Configuration

Each agent has its own credentials file:
- Patton: `~/.openclaw/vault-credentials/patton.json`
- Tamara: `~/.openclaw/vault-credentials/tamara.json`
- Vigil: `~/.openclaw/vault-credentials/vigil.json`
- Nexus: `~/.openclaw/vault-credentials/nexus.json`

Each agent's policy allows read-only access to its own path: `secret/data/local/threatrecall/{agent}/*`

## Compliance

- Per GOV-014: Secrets never stored in logs, code, or config files
- Per GOV-012: All secret access logged as OCSF events
- Per GOV-019 IA-5: AppRole credentials rotate every 90 days
