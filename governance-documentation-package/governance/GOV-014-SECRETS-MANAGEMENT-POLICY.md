---
document_id: GOV-014
title: Secrets Management Policy
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal - Sensitive
rag_tags: [secrets, vault, hashicorp, azure-keyvault, credentials, rotation, encryption, keys, certificates, zero-trust]
compliance_mapping: [FedRAMP-IA-5, FedRAMP-SC-12, FedRAMP-SC-28, NIST-800-171-3.5.10, NIST-800-171-3.13.10, NIST-800-171-3.13.11]
---

# Secrets Management Policy

## Purpose

This document defines how secrets (credentials, API keys, encryption keys, certificates, tokens, and any other sensitive authentication or authorization material) are stored, accessed, rotated, and audited. No secret is ever stored in source code, configuration files committed to version control, CI/CD pipeline definitions, container images, log output, or error messages. Violations of this policy are treated as security incidents per GOV-022.

## Scope

This policy covers all secrets used by the organization's software and infrastructure: database credentials, API keys for external services, TLS certificates, JWT signing keys, encryption keys, service account credentials, OAuth client secrets, and any other material whose disclosure would compromise the security of a system or data.

## Secrets Infrastructure Architecture

The organization uses a two-tier secrets management architecture:

**Tier 1: HashiCorp Vault (Community Edition, self-hosted)** is the primary secrets store for the local development and homelab environment. Vault runs on the local infrastructure and serves as the authoritative source for all application secrets in the local environment. Vault is selected for its FOSS availability, mature API, dynamic secret generation capabilities, and fine-grained access control.

**Tier 2: Azure Key Vault** is the secrets store for cloud-deployed workloads. When services run in Azure, they retrieve secrets from Azure Key Vault rather than reaching back to the local Vault instance. Azure Key Vault is selected for native Azure integration, managed HSM backing, and alignment with the Azure cloud strategy.

The two tiers operate independently. Secrets are not synchronized between them. Each environment (local, cloud staging, cloud production) has its own secret values. The application code uses an abstraction layer that resolves the correct secrets source based on the runtime environment configuration.

### Secrets Resolution Pattern

Applications determine the secrets source from the `SECRETS_BACKEND` environment variable:

`SECRETS_BACKEND=vault` uses the local HashiCorp Vault instance. The application authenticates to Vault using AppRole authentication. The Vault address is configured via `VAULT_ADDR` (default: `https://vault.local:8200`).

`SECRETS_BACKEND=azure-keyvault` uses Azure Key Vault. The application authenticates using Azure Managed Identity (in Azure-hosted environments) or Azure CLI credentials (in development). The Key Vault URL is configured via `AZURE_KEYVAULT_URL`.

`SECRETS_BACKEND=env` is permitted only in local development and CI testing. Secrets are loaded from environment variables. This backend is never used in staging or production.

```python
# Python abstraction pattern
from abc import ABC, abstractmethod

class SecretsProvider(ABC):
    @abstractmethod
    async def get_secret(self, name: str) -> str: ...

class VaultProvider(SecretsProvider):
    """HashiCorp Vault via hvac client library."""
    async def get_secret(self, name: str) -> str:
        return self._client.secrets.kv.v2.read_secret_version(
            path=name, mount_point="secret"
        )["data"]["data"]["value"]

class AzureKeyVaultProvider(SecretsProvider):
    """Azure Key Vault via azure-keyvault-secrets client."""
    async def get_secret(self, name: str) -> str:
        return (await self._client.get_secret(name)).value
```

## Secret Classification

**Critical secrets** are encryption keys, JWT signing keys, database root credentials, and any secret whose compromise would require incident response and potentially data breach notification. Critical secrets must be stored in a hardware-backed store (Vault with auto-unseal via Azure Key Vault HSM, or Azure Key Vault Premium with HSM backing in production).

**Standard secrets** are application database credentials, API keys for external services, OAuth client secrets, and service account tokens. Standard secrets are stored in the appropriate secrets backend for the environment.

**Development secrets** are credentials for local development databases, test API keys for sandbox environments, and similar non-production material. Development secrets may use the `env` backend but must still never appear in version control.

## Secret Naming Convention

Secrets are named using a hierarchical path convention: `{environment}/{service}/{secret-name}`.

In HashiCorp Vault, this maps to the KV v2 secret path: `secret/data/production/user-service/db-password`. In Azure Key Vault, hierarchical paths are not natively supported, so the name uses hyphens as separators: `production-user-service-db-password`. The application's secrets provider handles the translation between the naming convention and the backend-specific format.

## Secret Rotation

All secrets must have defined rotation schedules. The rotation schedule is based on the secret classification:

Critical secrets are rotated every 90 days or immediately upon suspected compromise. Standard secrets are rotated every 180 days or immediately upon suspected compromise. API keys for external services are rotated per the external provider's recommendations or at least annually.

HashiCorp Vault's dynamic secrets capability is used where supported (database credentials, cloud provider access tokens). Dynamic secrets are generated on demand with short TTLs (1 hour default for database credentials) and are never reused. This is the preferred approach as it eliminates the need for manual rotation entirely.

For secrets that cannot use dynamic generation, rotation is tracked in a secrets inventory maintained by the security team. A scheduled CI job checks secret ages and creates alerts when rotation is due.

## Access Control

Access to secrets follows the principle of least privilege. Each service, application, or automation has its own identity and is granted access only to the specific secrets it requires.

In HashiCorp Vault, access is controlled through policies attached to AppRole identities. Each service has its own AppRole with a policy that grants read access only to its specific secret paths. No service has access to another service's secrets. Administrative access to Vault (policy creation, secret writing) is restricted to the CTO/CIO and designated security personnel.

In Azure Key Vault, access is controlled through Azure RBAC. Each service's Managed Identity is granted the `Key Vault Secrets User` role scoped to the specific Key Vault instance. Administrative access uses the `Key Vault Administrator` role and is restricted to designated personnel.

## Secrets in CI/CD Pipelines

CI/CD pipelines that require secrets (deployment credentials, registry authentication) use the pipeline platform's native secrets management (Gitea Actions secrets, Azure DevOps service connections). Secrets are injected as environment variables at runtime and are masked in pipeline logs. Pipeline secrets are never written to files, echoed in scripts, or passed as command-line arguments (which appear in process listings).

## Audit Logging

All secret access events are logged per the OCSF schema (GOV-012). HashiCorp Vault's audit backend is enabled and logs every secret read, write, and authentication event. Azure Key Vault diagnostic logs are enabled and forwarded to the log aggregation pipeline. Audit logs capture: who accessed the secret (identity), when (timestamp), what secret was accessed (path/name), and the operation type (read, write, delete, list). These logs are retained for 1 year per the audit log retention requirements in GOV-012.

## Emergency Secret Rotation

If a secret is suspected or confirmed compromised, the following procedure applies immediately: the compromised secret is rotated to a new value, all active sessions or tokens derived from the compromised secret are invalidated, the incident is logged per GOV-022, all systems using the secret are restarted to pick up the new value, and the event is reviewed in a post-incident retrospective within 5 business days to determine root cause and preventive measures.

## Local Development

Developers use a local Vault instance (dev mode is acceptable for individual workstations) or the `env` backend with a `.env` file for local development. The `.env` file is listed in `.gitignore` and never committed. A `.env.example` file is committed with placeholder values and comments describing each required secret. The onboarding guide (GOV-017) includes instructions for obtaining development credentials.

## Compliance Notes

This policy satisfies FedRAMP IA-5 (Authenticator Management) through secret rotation and access controls, SC-12 (Cryptographic Key Establishment and Management) through the key management and rotation requirements, and SC-28 (Protection of Information at Rest) through the encrypted storage of secrets in both Vault and Key Vault. The audit logging requirements satisfy AU-2 and AU-3 for secrets access events.
