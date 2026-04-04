---
document_id: GOV-007
title: Testing Standards
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [testing, unit-tests, integration-tests, coverage, pytest, cargo-test, test-pyramid, fixtures]
compliance_mapping: [FedRAMP-SA-11, FedRAMP-SI-6, NIST-800-171-3.14.1, NIST-800-171-3.14.2]
---

# Testing Standards

## Purpose

This document defines the testing types, coverage requirements, naming conventions, tooling, and practices for all software projects. Tests are the primary mechanism for proving that software behaves correctly and continues to behave correctly as it evolves. These standards ensure that testing effort is proportional to risk, that tests are reliable and fast, and that test code is maintained with the same rigor as production code.

## Test Pyramid

The organization follows the test pyramid model. The majority of tests are unit tests (fast, isolated, testing single functions or methods). A moderate number are integration tests (testing component boundaries, database interactions, API contracts). A small number are end-to-end tests (testing critical user workflows through the full stack). This ratio optimizes for fast feedback loops while still validating system-level behavior.

Target distribution: approximately 70% unit tests, 20% integration tests, 10% end-to-end tests. These are guidelines, not rigid quotas. A pure library may have 95% unit tests. A service with complex integrations may have a higher proportion of integration tests.

## Coverage Requirements

Line coverage minimum is 80% for all production code. Branch coverage minimum is 70%. These thresholds are enforced in CI and block merging if not met. Coverage is measured using `coverage.py` with `pytest-cov` for Python and `cargo-tarpaulin` or `cargo-llvm-cov` for Rust.

Coverage thresholds apply to new and changed code, not retroactively to legacy code. Legacy code below threshold is tracked as technical debt per GOV-015. New code must meet or exceed the threshold from the start.

Coverage metrics alone do not guarantee quality. A test that executes code without meaningful assertions provides coverage without value. Reviewers evaluate assertion quality during code review (GOV-006).

## Python Testing

### Framework

All Python projects use `pytest` as the test framework. Do not use `unittest.TestCase` classes. Pytest's function-based test style with fixtures produces more readable and maintainable tests.

### Test File Naming

Test files mirror the module they test with a `test_` prefix. The module `src/project_name/services/auth.py` is tested in `tests/unit/services/test_auth.py`. Integration tests live in `tests/integration/`. End-to-end tests live in `tests/e2e/`.

### Test Function Naming

Test function names describe the behavior being tested, not the method name: `test_expired_token_raises_authentication_error` is correct. `test_validate_token` is too vague to serve as documentation. `test_validate_token_3` is unacceptable. The pattern is `test_<scenario>_<expected_outcome>`.

### Fixtures and Test Data

Pytest fixtures handle setup and teardown. Fixtures are defined in `conftest.py` files at the appropriate directory level. Test data uses factories (via `factory_boy` or inline fixture functions) rather than static JSON files when the data has relationships or requires variation. Database fixtures use transactions that roll back after each test to ensure isolation.

Fixtures must never depend on external services, network connectivity, or mutable shared state. External service calls are mocked using `pytest-httpx` for HTTP clients or `unittest.mock.patch` for other interfaces.

### Assertions

Use plain `assert` statements (pytest rewrites them for informative failure messages). Do not use `self.assertEqual` or similar unittest methods. Assert specific values, not truthiness: `assert result.status_code == 200` not `assert result.ok`. For complex comparisons, use `pytest.approx` for floating-point values and explicit field comparisons for objects.

## Rust Testing

### Framework

Rust projects use the built-in `#[test]` and `#[tokio::test]` attributes. Additional assertion macros come from the standard library (`assert!`, `assert_eq!`, `assert_ne!`). For property-based testing, use `proptest`. For snapshot testing, use `insta`.

### Test Organization

Unit tests live in a `#[cfg(test)] mod tests` block within the same file as the code they test. Integration tests live in the `tests/` directory at the crate root. This follows standard Rust project layout conventions.

### Test Naming

Test function names follow the same `<scenario>_<expected_outcome>` pattern as Python: `fn expired_token_returns_auth_error()`. The `test_` prefix is not required in Rust (the `#[test]` attribute marks them), but use it for consistency with the Python convention.

## Integration Testing

Integration tests validate that components work together correctly across boundaries: database queries, HTTP API handlers, message queue consumers, and external service clients. Integration tests use real (containerized) dependencies where feasible. For databases, use a Dockerized instance of the actual database (PostgreSQL) provisioned in CI. For external services that cannot be containerized, use contract-based mocks (wiremock for Rust, `pytest-httpx` or `responses` for Python).

Integration tests are tagged or placed in separate directories so they can be run independently from unit tests. CI runs unit tests first (fast feedback) and integration tests second (slower but validates boundaries).

## Security Testing

Security-specific tests validate: input validation rejects malformed or malicious input, authentication endpoints handle invalid credentials correctly, authorization checks prevent privilege escalation, rate limiting activates at the configured threshold, and sensitive data does not appear in logs or error responses. These tests are part of the standard test suite, not a separate security-only suite. See GOV-011 for SAST/DAST requirements that supplement code-level security tests.

## Test Environment

Tests must be deterministic. They must not depend on execution order, wall clock time, random values without seeding, network connectivity, or file system state left by other tests. Each test sets up its own preconditions and cleans up after itself (or uses transactional rollback).

Tests that depend on time use injectable clock abstractions rather than calling `datetime.now()` or `SystemTime::now()` directly. Tests that depend on randomness use seeded RNGs with the seed logged on failure for reproducibility.

## Compliance Notes

Testing practices support FedRAMP SA-11 (Developer Security Testing and Evaluation) through security-specific test requirements and SI-6 (Security Function Verification) through automated testing of security controls in CI.
