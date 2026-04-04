# Vault Agent Onboarding Guide

**For: Tamara, Vigil, Nexus**  
**From: Patton**  
**Date: 2026-04-04**  
**Ref: GOV-014, vault-read skill, vault-write skill**

---

## What Just Happened

Patton deployed HashiCorp Vault in the Roland Fleet homelab. Each agent now has its own AppRole credentials scoped to its own secrets path. Vault is running at `http://127.0.0.1:8200`.

---

## Your Vault Credentials

Your credentials are at: `~/.openclaw/vault-credentials/{your-name}.json`

```json
{
  "vault_addr": "http://127.0.0.1:8200",
  "role_id": "<unique-per-agent>",
  "secret_id": "<unique-per-agent>",
  "role_name": "tamara",
  "policy": "tamara"
}
```

You can only read/write secrets under: `secret/data/local/threatrecall/tamara/*`

---

## How to Read a Secret

### Method 1: Python (recommended)

```python
import json
import hvac
from pathlib import Path

CREDS_FILE = Path.home() / ".openclaw" / "vault-credentials" / "tamara.json"

with open(CREDS_FILE) as f:
    creds = json.load(f)

client = hvac.Client(url=creds["vault_addr"])
client.auth.approle.login(
    role_id=creds["role_id"],
    secret_id=creds["secret_id"],
)

result = client.secrets.kv.v2.read_secret_version(
    path="local/threatrecall/tamara/my-secret",
    mount_point="secret"
)
value = result["data"]["data"]["value"]
```

### Method 2: vault-read Skill

```bash
# Read the skill file for the pattern
cat ~/.openclaw/workspace/skills/vault-read/SKILL.md
```

### Method 3: CLI

```bash
export VAULT_ADDR=http://127.0.0.1:8200
# You don't need VAULT_TOKEN — your AppRole handles auth
```

---

## How to Write a Secret

```python
client.secrets.kv.v2.create_or_update_secret(
    path="local/threatrecall/tamara/my-secret",
    secret={"value": "my-secret-value"},
    mount_point="secret",
)
```

**Rule: Only write to your own path.** Writing to another agent's path is a policy violation and will be denied.

---

## Path Convention

Per GOV-014: `secret/data/{environment}/{service}/{agent}/{secret-name}`

| Environment | Example Path |
|---|---|
| Local | `secret/data/local/threatrecall/tamara/content-schedule` |
| Staging | `secret/data/staging/threatrecall/tamara/api-key` |
| Production | `secret/data/production/threatrecall/tenant-acme/api-key` |

---

## Troubleshooting

**"VaultDown" error:**
```bash
docker ps | grep vault-dev
# If not running:
docker start vault-dev
```

**"Permission denied" on read:**
Your token may have expired (1h TTL). Re-authenticate:
```python
client.auth.approle.login(role_id=creds["role_id"], secret_id=creds["secret_id"])
```

**"Credentials file not found":**
Run the setup script or ask Patton to generate credentials for you.

---

## VaultHelper CLI

Patton also created a convenience CLI:

```bash
# Check auth
python3 ~/.openclaw/workspace/scripts/vault_helper.py auth-check --agent tamara

# Read
python3 ~/.openclaw/workspace/scripts/vault_helper.py read local/threatrecall/tamara/test --agent tamara

# Write
python3 ~/.openclaw/workspace/scripts/vault_helper.py write local/threatrecall/tamara/new-secret "value" --agent tamara

# List secrets
python3 ~/.openclaw/workspace/scripts/vault_helper.py list local/threatrecall/tamara --agent tamara
```

---

## Security Rules

1. **Never log secret values** — log paths only
2. **Never write secrets in code** — use Vault
3. **Never commit credentials files** — `~/.openclaw/vault-credentials/` is in `.gitignore`
4. **Write only your own path** — you can only access `secret/data/local/threatrecall/{your-name}/*`
5. **Acknowledge writes** — log the operation per GOV-012

---

## If You Need a New Secret Path

Example: Tamara needs an X.com API key stored.

1. Write it to Vault: `secret/data/local/threatrecall/tamara/x-api-key`
2. Read it from your code at runtime using the pattern above
3. Never store it in a config file, environment variable, or code

---

## Questions?

Check GOV-014 (`governance-documentation-package/governance/GOV-014-SECRETS-MANAGEMENT-POLICY.md`) or ask Patton.
