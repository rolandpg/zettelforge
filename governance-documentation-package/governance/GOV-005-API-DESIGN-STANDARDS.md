---
document_id: GOV-005
title: API Design Standards
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [api, rest, openapi, versioning, error-handling, pagination, authentication, contracts, azure-endpoints]
compliance_mapping: [FedRAMP-SA-8, FedRAMP-SC-8, FedRAMP-IA-8, NIST-800-171-3.13.8]
---

# API Design Standards

## Purpose

This document defines the design conventions, contract specifications, versioning strategy, error handling patterns, and security requirements for all APIs built by the organization. These standards ensure that APIs are consistent, predictable, well-documented, and interoperable across services. API contracts are the most critical integration boundary in a multi-service architecture. Getting them wrong is expensive to fix after consumers depend on them.

## Scope

These standards apply to all HTTP/REST APIs exposed by the organization's services, whether consumed by internal services, external clients, or LLM-based agents. GraphQL and gRPC APIs follow the relevant sections where applicable, with protocol-specific conventions documented separately if adopted.

## API Contract Definition

Every API must have its contract defined in an OpenAPI 3.1 specification file before implementation begins. The OpenAPI spec is the source of truth for the API's behavior. Code generators, test validators, and documentation are all derived from this spec. The spec file lives in the repository at `api/openapi.yaml` and is version-controlled alongside the implementation.

API contracts are reviewed as part of the design phase (GOV-001, Phase 2) and require approval before implementation starts. Changes to existing API contracts require a design document (GOV-016) if they affect existing consumers.

## URL Design

### Base URL Pattern

APIs use the pattern `https://{host}/api/v{major-version}/{resource}`. The version prefix appears in the URL path. The resource name is a plural noun representing the collection.

### Resource Naming

Resource names use lowercase plural nouns: `/users`, `/audit-logs`, `/access-tokens`. Multi-word resources use kebab-case: `/user-sessions`, not `/userSessions` or `/user_sessions`. Resource names describe the entity, not the action. The HTTP method conveys the action.

### URL Examples

```
GET    /api/v1/users                  # List users (collection)
POST   /api/v1/users                  # Create a user
GET    /api/v1/users/{user_id}        # Get a specific user
PUT    /api/v1/users/{user_id}        # Replace a user
PATCH  /api/v1/users/{user_id}        # Partially update a user
DELETE /api/v1/users/{user_id}        # Delete a user
GET    /api/v1/users/{user_id}/roles  # List roles for a user (sub-resource)
```

### URL Anti-Patterns

Never use verbs in URLs: `/api/v1/getUsers` is wrong. Never use CRUD words: `/api/v1/users/create` is wrong (use POST to the collection). Never nest resources more than two levels deep: `/api/v1/organizations/{org_id}/teams/{team_id}/members` is the maximum. Deeper nesting indicates the need for a top-level resource or a query parameter filter.

## HTTP Methods

`GET` retrieves resources. It must be idempotent and safe (no side effects). Never use GET for operations that modify state.

`POST` creates a new resource or triggers a non-idempotent action. Returns `201 Created` with a `Location` header for resource creation. Returns `200 OK` or `202 Accepted` for action triggers.

`PUT` replaces an entire resource. The request body must include all fields. Returns `200 OK` with the updated resource.

`PATCH` partially updates a resource. The request body includes only the fields to change. Uses JSON Merge Patch (RFC 7396) format. Returns `200 OK` with the updated resource.

`DELETE` removes a resource. Returns `204 No Content` on success. Idempotent: deleting an already-deleted resource returns `204`, not `404`.

## Request and Response Format

All request and response bodies use JSON (`application/json`). The `Content-Type` header is required on all requests with a body. The `Accept` header should be respected but defaults to `application/json` if omitted.

### Request Body Conventions

Field names use `snake_case` in JSON bodies. This aligns with the Python ecosystem (Pydantic models serialize to snake_case by default) and is the most common convention in REST APIs. Rust services handle the conversion via serde rename attributes.

```json
{
    "user_name": "pgroland",
    "email": "user@example.com",
    "role_id": "role-admin-001",
    "is_active": true
}
```

### Response Envelope

All successful responses returning data use a consistent envelope:

```json
{
    "data": { ... },
    "meta": {
        "request_id": "req-abc-123",
        "timestamp": "2026-04-02T14:30:00Z"
    }
}
```

Collection responses include pagination metadata:

```json
{
    "data": [ ... ],
    "meta": {
        "request_id": "req-abc-123",
        "timestamp": "2026-04-02T14:30:00Z"
    },
    "pagination": {
        "cursor": "eyJpZCI6MTAwfQ==",
        "has_more": true,
        "page_size": 25
    }
}
```

## Pagination

All collection endpoints must support pagination. The organization uses cursor-based pagination exclusively. Offset-based pagination (skip/limit) is prohibited because it produces inconsistent results when data changes between pages and degrades performance at high offsets.

Query parameters for pagination: `page_size` (integer, default 25, max 100) and `cursor` (opaque string, omitted for the first page). The cursor is a base64-encoded value that the server uses to determine the starting point. Clients must treat cursors as opaque and must not construct or modify them.

## Error Response Format

All error responses use this format regardless of the error type:

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable description of the error",
        "details": [
            {
                "field": "email",
                "issue": "Invalid email format",
                "value": "not-an-email"
            }
        ],
        "request_id": "req-abc-123",
        "documentation_url": "https://docs.example.com/errors/VALIDATION_ERROR"
    }
}
```

### Error Codes

Error codes are `UPPER_SNAKE_CASE` strings that are stable and machine-parseable. They never change once published. The HTTP status code conveys the error category. The error code conveys the specific error within that category. Common codes: `VALIDATION_ERROR` (400), `AUTHENTICATION_REQUIRED` (401), `INSUFFICIENT_PERMISSIONS` (403), `RESOURCE_NOT_FOUND` (404), `CONFLICT` (409), `RATE_LIMITED` (429), `INTERNAL_ERROR` (500), `SERVICE_UNAVAILABLE` (503).

### Status Code Usage

`200 OK` for successful retrieval or update. `201 Created` for successful resource creation (include `Location` header). `204 No Content` for successful deletion. `400 Bad Request` for malformed requests or validation failures. `401 Unauthorized` for missing or invalid authentication. `403 Forbidden` for authenticated but insufficient permissions. `404 Not Found` for nonexistent resources. `409 Conflict` for state conflicts (duplicate creation, concurrent modification). `422 Unprocessable Entity` for semantically invalid requests (well-formed JSON but business rule violations). `429 Too Many Requests` for rate limiting (include `Retry-After` header). `500 Internal Server Error` for unexpected failures (never expose internal details). `503 Service Unavailable` for temporary unavailability (include `Retry-After` header).

Never use `200 OK` with an error payload in the body. The status code must accurately reflect the outcome.

## API Versioning

APIs use URL path versioning: `/api/v1/`, `/api/v2/`. The version number is the major version and increments only on breaking changes. Non-breaking changes (additive fields, new endpoints, new query parameters) do not require a version bump. Breaking changes (removing fields, changing field types, altering semantics) require a new major version and a migration guide.

Old API versions are supported for a minimum of 6 months after the new version is released. Deprecation is communicated through a `Deprecation` response header with the sunset date and a `Link` header pointing to the migration guide.

## Authentication and Authorization

All API endpoints require authentication unless explicitly documented as public. Authentication uses Bearer tokens in the `Authorization` header: `Authorization: Bearer <token>`. Token acquisition, validation, and refresh follow the patterns defined in GOV-011 and GOV-014.

Authorization follows the principle of least privilege. Each endpoint documents its required permissions in the OpenAPI spec using security schemes. Authorization failures return `403 Forbidden` with a clear error code indicating which permission is missing.

## Rate Limiting

All APIs implement rate limiting. Rate limits are communicated through response headers on every response: `X-RateLimit-Limit` (maximum requests per window), `X-RateLimit-Remaining` (requests remaining in current window), `X-RateLimit-Reset` (UTC epoch seconds when the window resets). When the limit is exceeded, return `429 Too Many Requests` with a `Retry-After` header in seconds.

## Request Identification

Every API request is assigned a unique `request_id` (UUID v4). If the client provides an `X-Request-ID` header, the server uses that value (after validation) to enable end-to-end tracing. If not provided, the server generates one. The `request_id` appears in all response bodies, error responses, and log entries (see GOV-012) to enable correlation between client logs, server logs, and monitoring systems.

## Azure Cloud Endpoint Configuration

Services that interact with Azure APIs must support multiple Azure cloud environments. The target cloud is determined by configuration, never hardcoded. See GOV-018 for the complete endpoint reference. The API design must account for environment-specific behavior differences, particularly around authentication endpoints, resource manager URLs, and service availability. API clients must accept the Azure cloud identifier as a configuration parameter and resolve endpoints accordingly.

## API Documentation

The OpenAPI specification is the primary documentation. It is supplemented by: a getting-started guide for new consumers, authentication setup instructions, example request/response pairs for common workflows, a changelog documenting every API change with its version, and error handling guidance with recovery suggestions for each error code.

API documentation is generated from the OpenAPI spec using Swagger UI (FOSS) and served at `/api/docs` in non-production environments. Production documentation is hosted separately and does not expose the interactive Swagger UI testing interface.

## Contract Testing

API producers and consumers each maintain contract tests. The producer's tests validate that the implementation matches the OpenAPI spec. The consumer's tests validate that the consumer correctly handles all response types, including error responses. Contract tests run in CI on every build. When a producer changes their API, consumer contract tests must still pass against the new implementation or the change is blocked until consumers are updated.

## Compliance Notes

These standards support FedRAMP SC-8 (Transmission Confidentiality and Integrity) through HTTPS-only requirements, IA-8 (Identification and Authentication for Non-Organizational Users) through mandatory authentication, and SA-8 (Security Engineering Principles) through consistent, secure-by-default API design patterns.
