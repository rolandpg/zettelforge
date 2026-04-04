"""Secrets management per GOV-014.

Tier 1: HashiCorp Vault (local)
Tier 2: Azure Key Vault (cloud/production)
Tier 3: Environment variables (local dev only)

API keys stored at: secret/data/{environment}/threatrecall/{tenant_id}/api-key
"""

from abc import ABC, abstractmethod

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
    """HashiCorp Vault via hvac client library.

    Path convention per GOV-014: {environment}/{service}/{secret-name}
    """

    def __init__(self, vault_addr: str) -> None:
        import hvac

        self._client = hvac.Client(url=vault_addr)
        self._mount_point = "secret"

    async def get_secret(self, name: str) -> str:
        import asyncio

        result = await asyncio.to_thread(
            self._client.secrets.kv.v2.read_secret_version,
            path=name,
            mount_point=self._mount_point,
        )
        return result["data"]["data"]["value"]

    async def set_secret(self, name: str, value: str) -> None:
        import asyncio

        await asyncio.to_thread(
            self._client.secrets.kv.v2.create_or_update_secret,
            secret_path=name,
            secret=dict(value=value),
            mount_point=self._mount_point,
        )
        logger.info("secret_stored", path=name, vault_path=f"secret/data/{name}")

    async def delete_secret(self, name: str) -> None:
        import asyncio

        await asyncio.to_thread(
            self._client.secrets.kv.v2.delete_metadata_and_all_versions,
            path=name,
            mount_point=self._mount_point,
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
