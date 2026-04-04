"""Secrets management per GOV-014.

Tier 1: HashiCorp Vault (local)
Tier 2: Azure Key Vault (cloud/production)
Tier 3: Environment variables (local dev only)

API keys stored at: secret/data/{environment}/threatrecall/{agent_name}/{secret-name}
Path convention: {environment}/{service}/{agent_name}/{secret-name}
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class SecretsProvider(ABC):
    """Abstract secrets provider per GOV-014 abstraction pattern."""

    @abstractmethod
    async def get_secret(self, name: str) -> str:
        """Retrieve a secret value by name."""
        ...

    @abstractmethod
    async def set_secret(self, name: str, value: str) -> None:
        """Store a secret value."""
        ...

    @abstractmethod
    async def delete_secret(self, name: str) -> None:
        """Delete a secret."""
        ...


class VaultProvider(SecretsProvider):
    """HashiCorp Vault via hvac client library with AppRole authentication.

    Per GOV-014: AppRole auth for non-interactive workloads.
    Path convention: {environment}/{service}/{agent_name}/{secret-name}
    e.g. secret/data/local/threatrecall/patton/api-key
    """

    _CREDENTIALS_FILE = Path.home() / ".openclaw" / "vault-credentials" / "patton.json"

    def __init__(self, vault_addr: str) -> None:
        import hvac

        self._vault_addr = vault_addr
        self._client = hvac.Client(url=vault_addr)
        self._mount_point = "secret"
        self._role_id: str | None = None
        self._secret_id: str | None = None
        self._agent_name = "patton"

        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate via AppRole. Reads credentials from file per GOV-014."""
        creds_file = self._CREDENTIALS_FILE
        if not creds_file.exists():
            msg = f"Vault credentials file not found: {creds_file}. Run vault setup first."
            raise FileNotFoundError(msg)

        with open(creds_file) as f:
            creds = json.load(f)

        self._role_id = creds.get("role_id")
        self._secret_id = creds.get("secret_id")
        self._agent_name = creds.get("role_name", "patton")
        self._vault_addr = creds.get("vault_addr", self._vault_addr)

        if not self._role_id or not self._secret_id:
            msg = "role_id and secret_id must be set in vault credentials file"
            raise ValueError(msg)

        # AppRole login
        self._client.auth.approle.login(
            role_id=self._role_id,
            secret_id=self._secret_id,
        )
        logger.info(
            "vault_authenticated",
            agent=self._agent_name,
            vault_addr=self._vault_addr,
        )

    async def get_secret(self, name: str) -> str:
        """Retrieve a secret from Vault KV v2.

        Full path: secret/data/{environment}/{service}/{agent}/{name}
        e.g. secret/data/local/threatrecall/patton/test
        """
        import asyncio

        # Always re-authenticate to ensure valid token (tokens expire in 1h)
        self._authenticate()

        result = await asyncio.to_thread(
            self._client.secrets.kv.v2.read_secret_version,
            path=name,
            mount_point=self._mount_point,
        )
        return result["data"]["data"]["value"]

    async def set_secret(self, name: str, value: str) -> None:
        """Store a secret in Vault KV v2."""
        import asyncio

        # Always re-authenticate to ensure valid token
        self._authenticate()

        await asyncio.to_thread(
            self._client.secrets.kv.v2.create_or_update_secret,
            secret_path=name,
            secret={"value": value},
            mount_point=self._mount_point,
        )
        logger.info(
            "secret_stored",
            path=name,
            vault_path=f"secret/data/{name}",
            agent=self._agent_name,
        )

    async def delete_secret(self, name: str) -> None:
        """Delete all versions of a secret."""
        import asyncio

        # Always re-authenticate
        self._authenticate()

        await asyncio.to_thread(
            self._client.secrets.kv.v2.delete_metadata_and_all_versions,
            path=name,
            mount_point=self._mount_point,
        )
        logger.info(
            "secret_deleted",
            path=name,
            agent=self._agent_name,
        )


class EnvProvider(SecretsProvider):
    """Environment variable backend per GOV-014.

    Only for local development and CI testing.
    NEVER used in staging or production.
    """

    async def get_secret(self, name: str) -> str:
        import os

        value = os.environ.get(f"TR_SECRET_{name.upper()}")
        if value is None:
            msg = f"Secret {name} not found in environment"
            raise ValueError(msg)
        return value

    async def set_secret(self, name: str, value: str) -> None:
        import os

        os.environ[f"TR_SECRET_{name.upper()}"] = value

    async def delete_secret(self, name: str) -> None:
        import os

        os.environ.pop(f"TR_SECRET_{name.upper()}", None)


def get_secrets_provider() -> SecretsProvider:
    """Factory per GOV-014 SECRETS_BACKEND resolution."""
    from threatrecall_api.core.config import settings

    match settings.secrets_backend:
        case "vault":
            return VaultProvider(vault_addr=settings.vault_addr)
        case "env":
            return EnvProvider()
        case _:
            msg = f"Unknown secrets backend: {settings.secrets_backend}"
            raise ValueError(msg)
