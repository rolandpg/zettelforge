#!/usr/bin/env bash
# vault-setup.sh — Provision HashiCorp Vault and agent credentials
# Part of Roland Fleet secrets infrastructure per GOV-014
# Usage: ./vault-setup.sh [--reset]

set -euo pipefail

VAULT_CONTAINER="vault-dev"
VAULT_VERSION="1.18"
VAULT_ADDR="http://127.0.0.1:8200"
ROOT_TOKEN="patton-vault-dev-root"
VAULT_DATA_DIR="${HOME}/.vault/data"
VAULT_CONFIG_DIR="${HOME}/.vault/config"
CREDS_DIR="${HOME}/.openclaw/vault-credentials"
POLICIES_DIR="${HOME}/.vault/policies"
AGENTS=("patton" "tamara" "vigil" "nexus")

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required"; exit 1; }

# Reset flag
if [[ "${1:-}" == "--reset" ]]; then
  echo "Resetting Vault..."
  docker stop "${VAULT_CONTAINER}" 2>/dev/null || true
  docker rm "${VAULT_CONTAINER}" 2>/dev/null || true
  rm -rf "${VAULT_DATA_DIR}" "${VAULT_CONFIG_DIR}"
  rm -f "${CREDS_DIR}"/*.json
  echo "Reset complete."
fi

# Create directories
mkdir -p "${VAULT_DATA_DIR}" "${VAULT_CONFIG_DIR}" "${CREDS_DIR}" "${POLICIES_DIR}"

# Start Vault container
if docker ps --format '{{.Names}}' | grep -q "^${VAULT_CONTAINER}$"; then
  echo "Vault already running."
else
  echo "Starting Vault..."
  docker run -d \
    --name "${VAULT_CONTAINER}" \
    --network host \
    -e VAULT_ADDR="${VAULT_ADDR}" \
    -e VAULT_DEV_ROOT_TOKEN_ID="${ROOT_TOKEN}" \
    -e VAULT_TOKEN="${ROOT_TOKEN}" \
    -v "${VAULT_DATA_DIR}:/vault/data" \
    --cap-add=IPC_LOCK \
    "hashicorp/vault:${VAULT_VERSION}" \
    vault server -dev \
    -dev-root-token-id="${ROOT_TOKEN}" \
    2>&1

  echo "Waiting for Vault to initialize..."
  sleep 5
fi

# Wait for Vault API
until curl -sf "${VAULT_ADDR}/v1/sys/health" >/dev/null 2>&1; do
  sleep 1
done
echo "Vault is up."

# Enable KV v2 and AppRole
docker exec "${VAULT_CONTAINER}" vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV v2 already enabled"
docker exec "${VAULT_CONTAINER}" vault auth enable approle 2>/dev/null || echo "AppRole already enabled"

# Create and provision per-agent policies and roles
for agent in "${AGENTS[@]}"; do
  echo "Provisioning ${agent}..."

  # Write policy file
  cat > "${POLICIES_DIR}/${agent}.hcl" << POLICY
# ${agent} agent policy — per GOV-014 least privilege
path "secret/data/local/threatrecall/${agent}/*" {
  capabilities = ["read", "list", "create", "update"]
}
path "secret/data/local/threatrecall/${agent}" {
  capabilities = ["list"]
}
path "secret/metadata/local/threatrecall/${agent}/*" {
  capabilities = ["read", "list"]
}
POLICY

  # Upload policy to Vault
  docker cp "${POLICIES_DIR}/${agent}.hcl" "${VAULT_CONTAINER}:/tmp/${agent}.hcl"
  docker exec "${VAULT_CONTAINER}" vault policy write "${agent}" "/tmp/${agent}.hcl"

  # Create or update AppRole role
  docker exec "${VAULT_CONTAINER}" vault write "auth/approle/role/${agent}" \
    token_ttl=1h \
    token_max_ttl=24h \
    token_policies="${agent}"

  # Generate RoleID/SecretID
  ROLE_ID=$(docker exec "${VAULT_CONTAINER}" vault read -field=role_id "auth/approle/role/${agent}/role-id")
  SECRET_ID=$(docker exec "${VAULT_CONTAINER}" vault write -f -field=secret_id "auth/approle/role/${agent}/secret-id")

  # Write credentials file
  cat > "${CREDS_DIR}/${agent}.json" << CREDS
{
  "vault_addr": "${VAULT_ADDR}",
  "role_id": "${ROLE_ID}",
  "secret_id": "${SECRET_ID}",
  "role_name": "${agent}",
  "policy": "${agent}"
}
CREDS
  chmod 600 "${CREDS_DIR}/${agent}.json"

  echo "  RoleID: ${ROLE_ID}"
  echo "  Credentials written to ${CREDS_DIR}/${agent}.json"
done

# Write admin test secret
docker exec "${VAULT_CONTAINER}" vault kv put "secret/data/local/threatrecall/patton/test" \
  value="vault-integration-verified-$(date +%Y-%m-%d)" \
  owner="patton" \
  purpose="vault-integration-test" 2>/dev/null || true

echo ""
echo "Vault setup complete."
echo "Root token: ${ROOT_TOKEN}"
echo "Vault UI: http://127.0.0.1:8200/ui"
echo ""
echo "Verify with:"
echo "  python3 scripts/vault_helper.py auth-check"
echo "  python3 scripts/vault_helper.py read local/threatrecall/patton/test"
