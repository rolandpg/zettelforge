# vault-setup — Vault Initialization and Agent Credential Provisioning

## Description

Complete setup guide for HashiCorp Vault in the Roland Fleet homelab. Run once to establish the Vault server and provision AppRole credentials for each agent. Per GOV-014.

## What This Does

1. Start HashiCorp Vault in dev mode (Docker)
2. Enable KV v2 secrets engine at `secret/`
3. Enable AppRole auth method
4. Create per-agent policies (least privilege per GOV-014)
5. Create per-agent AppRole roles
6. Generate RoleID/SecretID pairs for each agent
7. Store credentials files for each agent

## Prerequisites

- Docker installed and running
- Network access to pull `hashicorp/vault:1.18`
- Port 8200 available

## Run Full Setup

```bash
# 1. Start Vault container
docker run -d \
  --name vault-dev \
  --network bridge \
  -p 8200:8200 \
  -e VAULT_ADDR=http://localhost:8200 \
  -e VAULT_DEV_ROOT_TOKEN_ID=patton-vault-dev-root \
  -e VAULT_TOKEN=patton-vault-dev-root \
  -v ~/.vault/data:/vault/data \
  --cap-add=IPC_LOCK \
  hashicorp/vault:1.18 \
  vault server -dev -dev-root-token-id=patton-vault-dev-root

# 2. Verify
docker exec vault-dev vault status

# 3. Enable KV v2 and AppRole
docker exec vault-dev vault secrets enable -path=secret kv-v2
docker exec vault-dev vault auth enable approle

# 4. Create policies and roles
# (See setup script in ~/.openclaw/workspace/scripts/vault-setup.sh)

# 5. Generate credentials for each agent
ROLE_ID=$(docker exec vault-dev vault read -field=role_id auth/approle/role/patton/role-id)
SECRET_ID=$(docker exec vault-dev vault write -field=secret_id auth/approle/role/patton/secret-id)
```

## Per-Agent Path Convention

Per GOV-014: `secret/data/{environment}/{service}/{agent}/{secret-name}`

| Agent   | Policy Path                       | Example Secrets                  |
|---------|-----------------------------------|----------------------------------|
| patton  | `secret/data/local/threatrecall/patton/*` | api-key, memory-credentials |
| tamara  | `secret/data/local/threatrecall/tamara/*` | content-schedule, x-api-key |
| vigil   | `secret/data/local/threatrecall/vigil/*` | cti-feeds, collector-tokens |
| nexus   | `secret/data/local/threatrecall/nexus/*` | research-credentials       |

## Agent Credential Files

Stored at: `~/.openclaw/vault-credentials/{agent}.json`

```json
{
  "vault_addr": "http://localhost:8200",
  "role_id": "<role-id>",
  "secret_id": "<secret-id>",
  "role_name": "patton",
  "policy": "patton"
}
```

**Security**: These files contain live credentials. They are in `.gitignore`.

## Credential Lifecycle

- **Token TTL**: 1 hour (auto-renewed by VaultProvider)
- **AppRole SecretID**: No expiration by default — rotate via `vault write -f auth/approle/role/{agent}/secret-id`
- **Rotation schedule**: Every 90 days per GOV-014 (critical secrets) or 180 days (standard)

## Admin Operations

### Rotate an Agent's SecretID

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=patton-vault-dev-root

# Generate new secret_id (old one is still valid for 1h until token expires)
NEW_SECRET=$(docker exec vault-dev vault write -field=secret_id auth/approle/role/tamara/secret-id)

# Update credentials file
# Edit ~/.openclaw/vault-credentials/tamara.json with new secret_id
```

### Add a New Agent

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=patton-vault-dev-root

# 1. Create policy file
cat > /tmp/newagent.hcl << EOF
path "secret/data/local/threatrecall/newagent/*" {
  capabilities = ["read", "list"]
}
path "secret/metadata/local/threatrecall/newagent/*" {
  capabilities = ["read", "list"]
}
EOF

# 2. Write policy and create role
docker cp /tmp/newagent.hcl vault-dev:/tmp/newagent.hcl
docker exec vault-dev vault policy write newagent /tmp/newagent.hcl
docker exec vault-dev vault write auth/approle/role/newagent \
  token_ttl=1h \
  token_max_ttl=24h \
  token_policies=newagent

# 3. Generate credentials
ROLE_ID=$(docker exec vault-dev vault read -field=role-id auth/approle/role/newagent/role-id)
SECRET_ID=$(docker exec vault-dev vault write -field=secret-id auth/approle/role/newagent/secret-id)

# 4. Create credentials file for the new agent
```

## Verify Setup

```bash
# Check all containers
docker ps --filter name=vault

# Check Vault is unsealed and initialized
docker exec vault-dev vault status

# Check AppRole is enabled
docker exec vault-dev vault auth list

# Check KV v2 is enabled
docker exec vault-dev vault secrets list

# Check policies exist
docker exec vault-dev vault policy list

# Check roles exist
docker exec vault-dev vault list auth/approle/role

# Test with each agent's credentials
docker exec vault-dev vault write -field=token \
  auth/approle/login \
  role_id=<role_id> \
  secret_id=<secret_id>
```

## Compliance Notes

- **GOV-014**: Tier 1 secrets store for local environment
- **GOV-019 IA-5**: AppRole credentials satisfy authenticator management requirements
- **GOV-012**: All vault operations logged as OCSF events (class 3001 for auth, class 3003 for access)
- **GOV-021 Tier 3**: Vault credential files are Tier 3 — never commit, never log values
