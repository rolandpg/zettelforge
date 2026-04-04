"""Core configuration for ThreatRecall API.

Per GOV-003: Pydantic Settings for all configuration.
Per GOV-014: Secrets loaded from Vault (not env).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Per GOV-003: Required settings have no defaults.
    Per GOV-014: SECRETS_BACKEND determines Vault vs Azure Key Vault.
    """

    model_config = SettingsConfigDict(
        env_prefix="TR_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Required settings
    data_dir: Path = Path("/data/threatrecall")
    vault_addr: str = "http://localhost:8200"
    secrets_backend: str = "vault"  # vault | azure-keyvault | env

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # Rate limiting (per GOV-005)
    rate_limit_requests_per_minute: int = 100
    rate_limit_requests_per_hour: int = 1000

    # Key rotation (per GOV-014: 180-day standard secret rotation)
    api_key_rotation_days: int = 180
    api_key_grace_period_hours: int = 24

    # Logging (per GOV-012)
    log_level: str = "INFO"

    @property
    def tenant_storage_path(self) -> Path:
        """Base path for tenant data directories."""
        return self.data_dir / "tenants"


settings = Settings()
