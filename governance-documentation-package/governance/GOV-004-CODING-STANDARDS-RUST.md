---
document_id: GOV-004
title: Coding Standards - Rust
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [rust, coding-standards, style-guide, clippy, cargo, naming-conventions, patterns, memory-safety]
compliance_mapping: [FedRAMP-SA-11, FedRAMP-SI-10, FedRAMP-SI-16, NIST-800-171-3.13.13]
---

# Coding Standards - Rust

## Purpose

This document defines the coding standards, naming conventions, tooling requirements, and design patterns for all Rust code in the organization. Rust is used for performance-critical services, systems-level components, and any workload where memory safety guarantees provide security advantages over garbage-collected languages. These standards ensure consistency, safety, and maintainability across Rust codebases.

## Scope

These standards apply to all Rust code: backend services, CLI tools, libraries, WebAssembly modules, and build tooling written in Rust. Rust is the preferred language for: high-throughput data processing pipelines, cryptographic operations, network protocol implementations, and any component where zero-cost abstractions provide measurable performance advantages over Python.

## Rust Toolchain

All projects use the latest stable Rust release. Nightly features are prohibited in production code. The toolchain is pinned via `rust-toolchain.toml` at the repository root to ensure all developers and CI systems use the same compiler version.

```toml
# rust-toolchain.toml
[toolchain]
channel = "stable"
components = ["rustfmt", "clippy", "rust-analyzer"]
```

## Tooling and Automation

**rustfmt** handles all code formatting. Configuration is defined in `rustfmt.toml` at the repository root. The formatter runs in CI and rejects non-conformant code. Developers run `cargo fmt` before committing. The only configuration override from defaults is max line width set to 100 characters to match the Python standard.

```toml
# rustfmt.toml
max_width = 100
edition = "2021"
```

**Clippy** is the primary linter. It runs with the `--all-targets` and `-D warnings` flags, meaning all clippy warnings are treated as errors. Additional lint groups are enabled in `Cargo.toml` or `clippy.toml`. Clippy `allow` annotations are permitted only with a comment explaining the justification.

```toml
# Cargo.toml - workspace-level lint configuration
[workspace.lints.clippy]
pedantic = "warn"
nursery = "warn"
unwrap_used = "deny"
expect_used = "warn"
panic = "deny"
```

**cargo-audit** scans dependencies for known vulnerabilities and runs in CI on every build. See GOV-009 for the full dependency management policy.

**cargo-deny** enforces license compliance and duplicate dependency detection. Configuration is in `deny.toml` at the repository root.

## Naming Conventions

**Crates and modules** use `snake_case`. Example: `user_auth`, `event_processor`. Crate names in `Cargo.toml` use hyphens (`user-auth`) while the Rust module path uses underscores (`user_auth`). This is standard Rust convention.

**Types** (structs, enums, traits, type aliases) use `PascalCase`. Example: `UserAuthenticator`, `EventKind`, `Serializable`. Acronyms follow Rust convention: capitalize only the first letter for acronyms longer than 2 characters (`HttpClient` not `HTTPClient`), but keep 2-letter acronyms uppercase (`IO`, `DB`).

**Functions and methods** use `snake_case`. Getter methods omit the `get_` prefix: `fn name(&self) -> &str` not `fn get_name(&self)`. Conversion methods follow Rust conventions: `as_` for cheap reference conversions, `to_` for expensive conversions that allocate, `into_` for consuming conversions. Boolean-returning methods use `is_` or `has_` prefix: `fn is_valid(&self) -> bool`.

**Constants** use `UPPER_SNAKE_CASE`. Example: `const MAX_RETRY_COUNT: u32 = 3;`. Static variables also use `UPPER_SNAKE_CASE`.

**Lifetimes** use short lowercase names. `'a`, `'b` for generic lifetimes. Descriptive names for clarity when multiple lifetimes interact: `'input`, `'output`.

**Type parameters** use single uppercase letters starting with `T`, or descriptive `PascalCase` when multiple type parameters make single letters ambiguous: `K, V` for key-value, `Item`, `Error`.

## Error Handling

Rust code uses the `Result<T, E>` type for all fallible operations. The `thiserror` crate is used for defining error types with derive macros. The `anyhow` crate is permitted only in binary crates (applications), never in library crates. Library crates must define specific error types so consumers can match on error variants.

`.unwrap()` is prohibited in production code (enforced by clippy). `.expect("message")` is permitted only when the invariant is guaranteed by preceding logic and the message explains why the value cannot be `None`/`Err`. In all other cases, use `?` operator for propagation or explicit match/if-let for handling.

```rust
// Correct: specific error type, ? propagation
#[derive(Debug, thiserror::Error)]
pub enum AuthError {
    #[error("Token expired for user {user_id}")]
    TokenExpired { user_id: String },

    #[error("Invalid signature")]
    InvalidSignature,

    #[error("Key vault unavailable: {0}")]
    KeyVaultError(#[from] azure_core::Error),
}

pub fn validate_token(token: &str) -> Result<Claims, AuthError> {
    let claims = decode_jwt(token)?;
    if claims.is_expired() {
        return Err(AuthError::TokenExpired {
            user_id: claims.sub.clone(),
        });
    }
    Ok(claims)
}

// Incorrect: unwrap in production code
pub fn validate_token(token: &str) -> Claims {
    decode_jwt(token).unwrap()  // Panics on invalid token
}
```

## Unsafe Code

`unsafe` blocks are prohibited unless explicitly approved by the CTO/CIO or designated Rust safety reviewer. Every `unsafe` block must include a `// SAFETY:` comment explaining why the unsafe operation is sound. Approved unsafe usage is tracked in an `UNSAFE_USAGE.md` file in the repository root documenting each instance, its justification, and the reviewer who approved it. Prefer safe abstractions from well-audited crates (`bytemuck`, `zerocopy`) over hand-written unsafe code.

## Concurrency Patterns

Rust's ownership model prevents data races at compile time. For async workloads, use `tokio` as the async runtime (it is the ecosystem standard and best-supported). Use `Arc<Mutex<T>>` sparingly and prefer message-passing via `tokio::sync::mpsc` channels when possible. Never hold a mutex guard across an `.await` point (this is a common source of deadlocks and is flagged by clippy).

For CPU-bound parallelism, use `rayon` for data-parallel workloads. Do not spawn OS threads directly unless there is a specific reason that `rayon` or `tokio::task::spawn_blocking` cannot serve the use case.

## Dependency Selection Criteria

Rust dependencies must meet these criteria: actively maintained (commit activity within 6 months), license compatible (MIT, Apache-2.0, or BSD), no `unsafe` code that has not been audited (check with `cargo-geiger`), and available on crates.io (no git dependencies in production). Feature flags should be used to minimize the dependency tree: disable default features and enable only what the project needs.

## Project Structure

Rust projects follow this layout for binary crates:

```
project-name/
    src/
        main.rs             # Entry point, minimal (calls lib)
        lib.rs              # Library root (all logic lives here)
        config.rs           # Configuration (from environment)
        error.rs            # Error type definitions
        models/             # Data structures
        services/           # Business logic
        api/                # HTTP handlers (if web service)
        db/                 # Database access layer
    tests/                  # Integration tests
    benches/                # Benchmarks
    Cargo.toml
    Cargo.lock              # Always committed for binary crates
    rust-toolchain.toml
    clippy.toml
    rustfmt.toml
    deny.toml
```

For library crates, omit `main.rs` and do not commit `Cargo.lock` (let consumers resolve versions).

## Documentation

All public items must have doc comments (`///`). Module-level documentation uses `//!`. Doc comments include a summary line, a detailed description for non-trivial items, and `# Examples` sections for public API functions. Doc tests (`cargo test --doc`) run in CI and must pass. Internal/private functions use regular comments (`//`) for non-obvious logic.

```rust
/// Validates a JWT token and returns the decoded claims.
///
/// Checks the token signature against the configured signing key,
/// verifies the expiration time, and extracts the claims payload.
///
/// # Errors
///
/// Returns `AuthError::TokenExpired` if the token's `exp` claim is in the past.
/// Returns `AuthError::InvalidSignature` if the signature verification fails.
///
/// # Examples
///
/// ```
/// let claims = validate_token("eyJ...")?;
/// assert_eq!(claims.sub, "user-123");
/// ```
pub fn validate_token(token: &str) -> Result<Claims, AuthError> {
    // ...
}
```

## Configuration

Rust services load configuration from environment variables using the `config` crate with the `Environment` source. The pattern mirrors the Python approach: a `Settings` struct with typed fields, defaults for development, and mandatory overrides for production. See GOV-014 for secrets loading from Vault and Key Vault.

## Logging

Rust code uses the `tracing` crate for structured logging, which integrates with the OCSF schema requirements defined in GOV-012. Use `tracing::instrument` on async functions to automatically capture span context. Never log secrets, credentials, or PII. Use structured fields, not format strings, for log data.

```rust
use tracing::{info, instrument};

#[instrument(skip(password))]  // Skip sensitive fields
async fn authenticate_user(username: &str, password: &str) -> Result<User, AuthError> {
    info!(user = username, method = "password", "Authentication attempt");
    // ...
}
```

## Compliance Notes

Rust's memory safety guarantees directly support FedRAMP SI-16 (Memory Protection). The language's type system and borrow checker eliminate entire classes of vulnerabilities (buffer overflows, use-after-free, double-free, data races) at compile time without runtime overhead. This provides stronger memory safety guarantees than C/C++ and comparable safety to managed languages without the garbage collection pause characteristics.
