---
document_id: GOV-003
title: Coding Standards - Python
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [python, coding-standards, style-guide, ruff, mypy, type-hints, naming-conventions, patterns]
compliance_mapping: [FedRAMP-SA-11, FedRAMP-SI-10, NIST-800-171-3.13.13]
---

# Coding Standards - Python

## Purpose

This document defines the coding standards, naming conventions, tooling requirements, design patterns, and anti-patterns for all Python code in the organization. These standards exist to ensure consistency across codebases, reduce cognitive load during code review, enable effective automated quality enforcement, and produce code that is readable by both humans and LLM-based development tools.

## Scope

These standards apply to all Python code: application services, CLI tools, automation scripts, infrastructure utilities, test code, and migration scripts. Test code follows the same standards with specific exceptions noted in the Testing section.

## Python Version

All Python code targets Python 3.12 or later. New projects must use the latest stable Python 3.x release available at project start. Python 2 is not supported under any circumstances. Version pinning for production deployments uses the full version specifier (e.g., `python:3.12.7-slim` in container images).

## Tooling and Automation

The following tools are mandatory and enforced in the CI pipeline. All tools use their default configurations unless explicitly overridden in this document. Configuration lives in `pyproject.toml` at the repository root.

**Ruff** is the primary linter and formatter. It replaces flake8, isort, black, and pyflakes with a single high-performance tool. The Ruff configuration must enable at minimum these rule sets: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `S` (bandit/security), `B` (bugbear), `UP` (pyupgrade), `SIM` (simplify), `RUF` (ruff-specific). Line length is set to 100 characters. Ruff format is used for all code formatting with no exceptions.

```toml
# pyproject.toml - Ruff configuration
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "S", "B", "UP", "SIM", "RUF", "N", "ANN", "T20"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]  # Allow assert in tests
```

**Mypy** is the static type checker. All Python code must include type annotations. Mypy runs in strict mode. The goal is zero type errors, not suppressed type errors. If a type annotation is genuinely impossible (rare with modern Python), use `# type: ignore[specific-error]` with a comment explaining why.

```toml
# pyproject.toml - Mypy configuration
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Bandit** security checks are covered by Ruff's `S` rules. Additional SAST scanning is defined in the Security Development Lifecycle (GOV-011).

**Pre-commit hooks** run Ruff lint, Ruff format, and Mypy before every commit. The `.pre-commit-config.yaml` is standardized across all Python repositories.

## Naming Conventions

**Modules and packages** use `snake_case` with short, descriptive names. Example: `user_auth.py`, `event_processor.py`. Never use hyphens in Python module names.

**Classes** use `PascalCase`. Example: `UserAuthenticator`, `EventProcessor`, `AzureKeyVaultClient`. Acronyms longer than 2 characters use title case: `HttpClient` not `HTTPClient`, but `IO` stays uppercase.

**Functions and methods** use `snake_case` with a verb prefix that describes the action. Example: `validate_token()`, `create_user()`, `fetch_audit_logs()`. Never use generic names like `process()`, `handle()`, or `do_thing()` without additional specificity.

**Variables** use `snake_case`. Names must be descriptive enough that a reader understands the purpose without checking the assignment. `user_count` is acceptable. `uc` is not. `x` is acceptable only as a loop variable over a trivially short range or in mathematical contexts where the variable name has conventional meaning.

**Constants** use `UPPER_SNAKE_CASE`. Example: `MAX_RETRY_COUNT = 3`, `DEFAULT_TIMEOUT_SECONDS = 30`. Constants are defined at module level or within a dedicated constants module, never inline in function bodies.

**Private members** use a single leading underscore: `_internal_cache`. Double underscore name mangling (`__private`) is reserved for avoiding name collisions in inheritance hierarchies and is almost never needed. If you think you need it, you probably need a different design.

**Type variables and generics** use `PascalCase` with a `T` suffix or descriptive name: `ItemT`, `ResponseT`.

## Code Organization

### Project Structure

Python projects follow this standard layout:

```
project-name/
    src/
        project_name/         # Main package (importable)
            __init__.py
            main.py           # Entry point
            config.py         # Configuration loading
            models/           # Data models and schemas
            services/         # Business logic
            api/              # API route handlers
            repositories/     # Data access layer
            utils/            # Shared utilities
    tests/
        unit/
        integration/
        conftest.py
    pyproject.toml
    README.md
    CHANGELOG.md
```

The `src/` layout is mandatory. It prevents the common pitfall where the project directory is importable instead of the package, causing subtle import resolution bugs. All imports reference the package name, not relative paths from the project root.

### Import Ordering

Imports are sorted by Ruff (isort rules) into three groups separated by blank lines: standard library imports, third-party imports, and local application imports. Within each group, imports are alphabetical. Use absolute imports exclusively. Relative imports (using dots) are prohibited because they break when modules are moved and are harder for LLMs and static analysis tools to resolve.

```python
# Standard library
import logging
from datetime import datetime, timezone
from pathlib import Path

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# Local application
from project_name.config import settings
from project_name.models.user import User
from project_name.services.auth import AuthService
```

## Type Annotations

Every function signature must include type annotations for all parameters and the return type. Variable annotations are required when the type is not obvious from the assignment.

```python
# Correct: fully annotated
def create_user(
    username: str,
    email: str,
    role: UserRole = UserRole.VIEWER,
) -> User:
    ...

# Correct: variable annotation where type is not obvious
session_timeout: int = config.get("session_timeout", 3600)

# Incorrect: missing return type
def create_user(username: str, email: str):
    ...

# Incorrect: no parameter types
def create_user(username, email):
    ...
```

Use `collections.abc` types for parameter annotations to accept the widest useful input: `Sequence` instead of `list` for read-only ordered collections, `Mapping` instead of `dict` for read-only key-value access. Use concrete types for return annotations so callers know exactly what they receive.

## Error Handling

Never use bare `except:` or `except Exception:` without re-raising or specific handling logic. Catch the most specific exception possible. Log the exception with stack trace at the point of handling using structured logging per GOV-012. Raise custom exceptions from a project-level exception hierarchy rather than re-using built-in exceptions for domain-specific errors.

```python
# Correct: specific exception, structured logging, custom error
class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has passed its expiration time."""

try:
    payload = jwt.decode(token, key=signing_key, algorithms=["RS256"])
except jwt.ExpiredSignatureError as exc:
    logger.warning("Token expired", extra={"user_id": user_id, "token_exp": str(exc)})
    raise TokenExpiredError(f"Token expired for user {user_id}") from exc

# Incorrect: broad catch, print statement, no structured data
try:
    payload = jwt.decode(token, key=signing_key, algorithms=["RS256"])
except Exception as e:
    print(f"Error: {e}")
    return None
```

Never return `None` to indicate an error condition. Either raise an exception or return a result type (using a union type or a dedicated Result class). Functions that can legitimately return `None` (e.g., a lookup that may not find a result) must annotate the return type as `Optional[T]` or `T | None`.

## Configuration Management

Application configuration is loaded from environment variables using Pydantic Settings. Configuration values are never hardcoded in application code. Default values are provided for development convenience but every production-relevant setting must be explicitly configured through environment variables.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
    )
    # Required settings (no default = must be set in environment)
    database_url: str
    vault_addr: str

    # Settings with safe defaults
    log_level: str = "INFO"
    api_port: int = 8000
    max_retry_count: int = 3

    # Azure cloud selection (see GOV-018 for endpoint resolution)
    azure_cloud: str = "commercial"  # commercial | gcc-high | dod
```

See GOV-014 (Secrets Management) for how secrets are loaded from HashiCorp Vault and Azure Key Vault rather than environment variables.

## Logging

All logging follows the OCSF schema defined in GOV-012. Use the `structlog` library for structured JSON logging. Never use `print()` for operational output. Never log secrets, credentials, tokens, or PII. Log messages use static strings with structured data in the `extra` dict, never f-strings that embed variable data into the message template (this breaks log aggregation).

```python
# Correct: static message, structured data
logger.info("User authenticated", extra={"user_id": user_id, "method": "jwt"})

# Incorrect: dynamic message string (breaks log aggregation and indexing)
logger.info(f"User {user_id} authenticated via jwt")
```

## Dependency Injection

Services and data access layers use dependency injection rather than module-level singletons or global state. For FastAPI applications, use the built-in `Depends()` system. For non-web applications, use constructor injection. This makes components testable in isolation without monkeypatching.

## Async Guidelines

Use `async`/`await` for I/O-bound operations in web services (database queries, HTTP calls, file operations). Do not use async for CPU-bound work (use multiprocessing or offload to a task queue instead). Never mix sync and async code by calling sync I/O functions inside an async context without wrapping in `asyncio.to_thread()`. All new web services use an async framework (FastAPI with uvicorn).

## Anti-Patterns

The following patterns are prohibited and will be flagged in code review:

Mutable default arguments (`def func(items: list = [])`) cause shared state bugs. Use `None` with a conditional assignment instead. Global mutable state (module-level dicts or lists modified at runtime) makes code untestable and non-thread-safe. Star imports (`from module import *`) pollute the namespace and make dependency tracking impossible. Nested function definitions beyond one level deep indicate logic that should be extracted into a named function or class. String concatenation for building SQL queries is a SQL injection vulnerability (use parameterized queries exclusively).

## Compliance Notes

These standards support FedRAMP SA-11 (Developer Security Testing and Evaluation) through mandatory SAST integration and SI-10 (Information Input Validation) through the type annotation and input validation requirements.
