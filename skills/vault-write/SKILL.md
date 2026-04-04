# vault-write — Write Secrets to HashiCorp Vault

## Description

Write secrets to HashiCorp Vault using AppRole authentication. Part of the Roland Fleet secrets management infrastructure per GOV-014.

## Prerequisites

- HashiCorp Vault must be running (`docker ps | grep vault-dev`)
- AppRole credentials must be configured at `~/.openclaw/vault-credentials/{agent}.json`
- Vault must have KV v2 enabled at `secret/`
- **Agent must have write permissions** — only Patton (admin) and specific write roles can write

## Path Convention

Per GOV-014: `{environment}/{service}/{agent}/{secret-name}`

Examples:
- `local/threatrecall/patton/api-key`
- `production/threatrecall/tenant-acme/api-key`
- `local/threatrecall/tamara/content-schedule`

**Never write secrets for other agents.** Each agent manages its own secrets only.

## Usage

### Write a Secret

```python
import json
from pathlib import Path
import hvac

CREDS_FILE = Path.home() / ".openclaw" / "vault-credentials" / "patton.json"

with open(CREDS_FILE) as f:
    creds = json.load(f)

client = hvac.Client(url=creds["vault_addr"])
client.auth.approle.login(
    role_id=creds["role_id"],
    secret_id=creds["secret_id"],
)

client.secrets.kv.v2.create_or_update_secret(
    path="local/threatrecall/patton/my-secret",
    secret={"value": "super-secret-value"},
    mount_point="secret",
)
```

### Write with Async

```python
import asyncio
import json
from pathlib import Path
import hvac

async def write_secret(path: str, value: str) -> None:
    creds_file = Path.home() / ".openclaw" / "vault-credentials" / "patton.json"
    with open(creds_file) as f:
        creds = json.load(f)
    
    client = hvac.Client(url=creds["vault_addr"])
    client.auth.approle.login(role_id=creds["role_id"], secret_id=creds["secret_id"])
    
    def _write():
        client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret={"value": value},
            mount_point="secret",
        )
    
    await asyncio.to_thread(_write)
```

### CLI

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=patton-vault-dev-root  # dev only

# Write
vault kv put secret/data/local/threatrecall/patton/my-secret value="secret-here"
vault kv put secret/data/local/threatrecall/patton/api-key owner="patton" purpose="threatrecall-api"
```

## Skills Protocol

Skill name: `vault-write`
Inputs: `path` (string, required), `value` (string, required)
Outputs: confirmation of write

## Error Handling

- `FileNotFoundError`: Credentials file missing — run vault setup
- `hvac.exceptions.VaultDown`: Vault not reachable
- `hvac.exceptions.Forbidden`: Agent lacks write permission to this path
- `VaultNamespaceMismatch`: Wrong namespace

## Security Rules

1. **Never log secret values** — log paths only
2. **Never write secrets in code** — always use Vault
3. **Never commit credentials files** — `.vault-credentials/` is in `.gitignore`
4. **Write only your own path** — tampering with other agents' secrets is a policy violation
5. **Acknowledge every write** — log the write operation per GOV-012

## Compliance

- Per GOV-014: Secrets never stored in logs, code, or config files
- Per GOV-012: All secret writes logged as OCSF events
- Per GOV-019 IA-5: Secret rotation required every 90 days
- Per GOV-021: Secrets are Tier 3 (Confidential) — handle accordingly

## Rotation

Secrets should be rotated every 180 days (standard secrets per GOV-014).
To rotate: write new value, invalidate old token, generate new AppRole credentials.
