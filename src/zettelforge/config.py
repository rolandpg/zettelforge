"""
ZettelForge Configuration Loader

Resolution order (highest priority first):
  1. Environment variables (ZETTELFORGE_*, TYPEDB_*, AMEM_*)
  2. config.yaml in working directory
  3. config.yaml in project root
  4. config.default.yaml in project root
  5. Hardcoded defaults in this module

Usage:
    from zettelforge.config import get_config
    cfg = get_config()
    cfg.typedb.host       # "localhost"
    cfg.embedding.url     # "http://127.0.0.1:11434"
    cfg.retrieval.default_k  # 10
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class StorageConfig:
    data_dir: str = "~/.amem"


@dataclass
class TypeDBConfig:
    host: str = "localhost"
    port: int = 1729
    database: str = "zettelforge"
    username: str = "admin"
    password: str = "password"


@dataclass
class EmbeddingConfig:
    provider: str = "fastembed"  # "fastembed" (in-process ONNX) or "ollama" (HTTP server)
    url: str = "http://127.0.0.1:11434"  # only used when provider=ollama
    model: str = "nomic-ai/nomic-embed-text-v1.5-Q"
    dimensions: int = 768


@dataclass
class LLMConfig:
    provider: str = "local"  # "local" (llama-cpp-python, in-process) or "ollama" (HTTP server)
    model: str = "Qwen/Qwen2.5-3B-Instruct-GGUF"  # HuggingFace repo for local, model name for ollama
    url: str = "http://localhost:11434"  # only used when provider=ollama
    temperature: float = 0.1


@dataclass
class ExtractionConfig:
    max_facts: int = 5
    min_importance: int = 3


@dataclass
class RetrievalConfig:
    default_k: int = 10
    similarity_threshold: float = 0.25
    entity_boost: float = 2.5
    max_graph_depth: int = 2


@dataclass
class SynthesisConfig:
    max_context_tokens: int = 3000
    default_format: str = "direct_answer"
    tier_filter: List[str] = field(default_factory=lambda: ["A", "B"])


@dataclass
class GovernanceConfig:
    enabled: bool = True
    min_content_length: int = 1


@dataclass
class CacheConfig:
    ttl_seconds: int = 300
    max_entries: int = 1024


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_intents: bool = True
    log_causal: bool = True
    log_file: str = ""  # Default set at runtime from data_dir
    log_to_stdout: bool = True
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 9


@dataclass
class EnterpriseConfig:
    """Enterprise edition settings (ignored in Community)."""
    license_key: str = ""
    blended_retrieval: bool = True
    cross_encoder_reranking: bool = True
    report_ingestion: bool = True
    multi_tenant: bool = False


@dataclass
class ZettelForgeConfig:
    storage: StorageConfig = field(default_factory=StorageConfig)
    typedb: TypeDBConfig = field(default_factory=TypeDBConfig)
    backend: str = "typedb"
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    synthesis: SynthesisConfig = field(default_factory=SynthesisConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    enterprise: EnterpriseConfig = field(default_factory=EnterpriseConfig)


def _find_config_file() -> Optional[Path]:
    """Find config.yaml in standard locations."""
    candidates = [
        Path("config.yaml"),
        Path("config.yml"),
        Path(__file__).parent.parent.parent / "config.yaml",
        Path(__file__).parent.parent.parent / "config.yml",
        Path(__file__).parent.parent.parent / "config.default.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _load_yaml(path: Path) -> dict:
    """Load YAML file, return empty dict on failure."""
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fall back to basic parsing if PyYAML not installed
        return _parse_simple_yaml(path)
    except Exception:
        return {}


def _parse_simple_yaml(path: Path) -> dict:
    """Minimal YAML parser for flat key: value pairs (no PyYAML dependency)."""
    result = {}
    current_section = None
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line.startswith(" ") and stripped.endswith(":"):
                current_section = stripped[:-1]
                result[current_section] = {}
            elif current_section and ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                # Parse basic types
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.startswith("[") or value.startswith("-"):
                    continue  # Skip lists in simple parser
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                result[current_section][key] = value
            elif ":" in stripped and current_section is None:
                key, _, value = stripped.partition(":")
                result[key.strip()] = value.strip()
    return result


def _apply_yaml(cfg: ZettelForgeConfig, data: dict):
    """Apply YAML dict to config dataclass."""
    if "storage" in data and isinstance(data["storage"], dict):
        for k, v in data["storage"].items():
            if hasattr(cfg.storage, k):
                setattr(cfg.storage, k, v)

    if "typedb" in data and isinstance(data["typedb"], dict):
        for k, v in data["typedb"].items():
            if hasattr(cfg.typedb, k):
                setattr(cfg.typedb, k, v)

    if "backend" in data:
        cfg.backend = str(data["backend"])

    if "embedding" in data and isinstance(data["embedding"], dict):
        for k, v in data["embedding"].items():
            if hasattr(cfg.embedding, k):
                setattr(cfg.embedding, k, v)

    if "llm" in data and isinstance(data["llm"], dict):
        for k, v in data["llm"].items():
            if hasattr(cfg.llm, k):
                setattr(cfg.llm, k, v)

    if "extraction" in data and isinstance(data["extraction"], dict):
        for k, v in data["extraction"].items():
            if hasattr(cfg.extraction, k):
                setattr(cfg.extraction, k, v)

    if "retrieval" in data and isinstance(data["retrieval"], dict):
        for k, v in data["retrieval"].items():
            if hasattr(cfg.retrieval, k):
                setattr(cfg.retrieval, k, v)

    if "synthesis" in data and isinstance(data["synthesis"], dict):
        for k, v in data["synthesis"].items():
            if hasattr(cfg.synthesis, k):
                setattr(cfg.synthesis, k, v)

    if "governance" in data and isinstance(data["governance"], dict):
        for k, v in data["governance"].items():
            if hasattr(cfg.governance, k):
                setattr(cfg.governance, k, v)

    if "cache" in data and isinstance(data["cache"], dict):
        for k, v in data["cache"].items():
            if hasattr(cfg.cache, k):
                setattr(cfg.cache, k, v)

    if "logging" in data and isinstance(data["logging"], dict):
        for k, v in data["logging"].items():
            if hasattr(cfg.logging, k):
                setattr(cfg.logging, k, v)

    if "enterprise" in data and isinstance(data["enterprise"], dict):
        for k, v in data["enterprise"].items():
            if hasattr(cfg.enterprise, k):
                setattr(cfg.enterprise, k, v)


def _apply_env(cfg: ZettelForgeConfig):
    """Apply environment variable overrides (highest priority)."""
    # Storage
    if v := os.environ.get("AMEM_DATA_DIR"):
        cfg.storage.data_dir = v

    # TypeDB
    if v := os.environ.get("TYPEDB_HOST"):
        cfg.typedb.host = v
    if v := os.environ.get("TYPEDB_PORT"):
        cfg.typedb.port = int(v)
    if v := os.environ.get("TYPEDB_DATABASE"):
        cfg.typedb.database = v
    if v := os.environ.get("TYPEDB_USERNAME"):
        cfg.typedb.username = v
    if v := os.environ.get("TYPEDB_PASSWORD"):
        cfg.typedb.password = v

    # Backend
    if v := os.environ.get("ZETTELFORGE_BACKEND"):
        cfg.backend = v

    # Embedding
    if v := os.environ.get("ZETTELFORGE_EMBEDDING_PROVIDER"):
        cfg.embedding.provider = v
    if v := os.environ.get("AMEM_EMBEDDING_URL"):
        cfg.embedding.url = v
    if v := os.environ.get("AMEM_EMBEDDING_MODEL"):
        cfg.embedding.model = v

    # LLM
    if v := os.environ.get("ZETTELFORGE_LLM_PROVIDER"):
        cfg.llm.provider = v
    if v := os.environ.get("ZETTELFORGE_LLM_MODEL"):
        cfg.llm.model = v
    if v := os.environ.get("ZETTELFORGE_LLM_URL"):
        cfg.llm.url = v

    # Enterprise
    if v := os.environ.get("THREATENGRAM_LICENSE_KEY"):
        cfg.enterprise.license_key = v


# ── Singleton ──────────────────────────────────────────────

_config: Optional[ZettelForgeConfig] = None


def get_config() -> ZettelForgeConfig:
    """Get global configuration. Loads once, caches thereafter."""
    global _config
    if _config is None:
        _config = ZettelForgeConfig()

        # Layer 1: config file
        config_file = _find_config_file()
        if config_file:
            data = _load_yaml(config_file)
            _apply_yaml(_config, data)

        # Layer 2: environment variables (override)
        _apply_env(_config)

    return _config


def reload_config() -> ZettelForgeConfig:
    """Force reload configuration from file + environment."""
    global _config
    _config = None
    return get_config()
