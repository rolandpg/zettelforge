# Secrets Management Setup

## Overview

ThreatRecall API supports multiple secrets backends:
- **env**: Environment variables (development)
- **vault**: HashiCorp Vault (production)

## Vault Setup (Production)

### 1. Enable Kubernetes Auth

```bash
# In Vault
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
  kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
```

### 2. Create Vault Policy

```bash
vault policy write threatrecall-api - <<EOF
path "secret/data/threatrecall/*" {
  capabilities = ["read"]
}
EOF
```

### 3. Create Kubernetes Auth Role

```bash
vault write auth/kubernetes/role/threatrecall-api \
  bound_service_account_names=threatrecall-api \
  bound_service_account_namespaces=threatrecall-production \
  policies=threatrecall-api \
  ttl=1h
```

### 4. Store Secrets

```bash
# API encryption key
vault kv put secret/threatrecall/api api-key="$(openssl rand -base64 32)"

# Vault token for app
vault kv put secret/threatrecall/vault token="s.xxx"
```

### 5. Deploy with Vault

```bash
# Update deployment to use Vault
kubectl apply -k k8s/overlays/production/

# Verify secrets are injected
kubectl get secret threatrecall-api-secrets -n threatrecall-production
```

## CSI Driver (Alternative)

Using Secrets Store CSI Driver with Vault:

```bash
# Install CSI driver
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi secrets-store-csi-driver/secrets-store-csi-driver

# Install Vault provider
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault-csi-provider hashicorp/vault-csi-provider
```

## Local Development

```bash
# Use env backend
export TR_SECRETS_BACKEND=env
export TR_VAULT_TOKEN=dev-token
python run_dev.py
```

## Rotating Secrets

```bash
# Rotate API key
vault kv put secret/threatrecall/api api-key="$(openssl rand -base64 32)"

# Restart pods to pick up new secret
kubectl rollout restart deployment/threatrecall-api -n threatrecall-production
```
