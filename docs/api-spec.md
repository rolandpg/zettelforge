# ThreatRecall API Specification

**Document ID:** TR-API-001  
**Version:** 1.0.0-draft  
**Status:** Draft  
**Classification:** Internal  
**Last Updated:** 2026-04-03  
**Owner:** ThreatRecall Team  

---

## Overview

ThreatRecall is a memory-as-a-service platform for threat intelligence. This document defines the API contract for the first production release.

**Core capability:** Store, recall, and evolve threat intelligence notes with semantic search and entity linking.

---

## Architecture

### Multi-Tenancy Model

**Full isolation.** Per GOV-019 FedRAMP Moderate alignment and customer requirement for complete tenant separation.

Each tenant has:
- Isolated data directory: `{data_dir}/tenants/{tenant_id}/`
- Dedicated LanceDB instance
- Isolated `notes.jsonl` and `entity_index.json`
- No cross-tenant queries possible at storage layer

### Authentication

Per GOV-005 and GOV-014:
- Bearer token authentication: `Authorization: Bearer <api_key>`
- API keys stored in HashiCorp Vault: `production/threatrecall/{tenant_id}/api-key`
- Rotation: 180 days (standard secret per GOV-014)
- Grace period: 24 hours during rotation

### Base URL

```
https://{host}/api/v1
```

---

## Endpoints

### Tenant Admin Endpoints

#### Create Tenant

**POST** `/admin/tenants`

Creates a new tenant with isolated storage.

**Request:**
```json
{
  "tenant_id": "acme-corp",
  "tenant_name": "Acme Corporation",
  "contact_email": "security@acme.com"
}
```

**Response (201 Created):**
```json
{
  "data": {
    "tenant_id": "acme-corp",
    "tenant_name": "Acme Corporation",
    "api_key": "tr_live_xxxxxxxxxxxxxxxxxxxx",
    "created_at": "2026-04-03T22:30:00Z",
    "storage_path": "/data/tenants/acme-corp"
  },
  "meta": {
    "request_id": "req-abc-123",
    "timestamp": "2026-04-03T22:30:00Z"
  }
}
```

**Errors:**
- `409 CONFLICT` — Tenant ID already exists
- `400 VALIDATION_ERROR` — Invalid tenant_id format (must be lowercase alphanumeric with hyphens, max 64 chars)

---

#### Rotate API Key

**POST** `/admin/tenants/{tenant_id}/rotate-key`

Generates a new API key. Old key remains valid for 24 hours (grace period).

**Request:**
```json
{
  "reason": "scheduled_rotation"
}
```

**Response (200 OK):**
```json
{
  "data": {
    "tenant_id": "acme-corp",
    "new_api_key": "tr_live_yyyyyyyyyyyyyyyyyyyy",
    "old_key_expires_at": "2026-04-04T22:30:00Z",
    "rotated_at": "2026-04-03T22:30:00Z"
  },
  "meta": {
    "request_id": "req-def-456",
    "timestamp": "2026-04-03T22:30:00Z"
  }
}
```

---

#### Delete Tenant

**DELETE** `/admin/tenants/{tenant_id}`

Marks tenant for deletion. Data retained for 30 days then purged.

**Response (202 Accepted):**
```json
{
  "data": {
    "tenant_id": "acme-corp",
    "status": "scheduled_deletion",
    "deletion_at": "2026-05-03T22:30:00Z"
  },
  "meta": {
    "request_id": "req-ghi-789",
    "timestamp": "2026-04-03T22:30:00Z"
  }
}
```

---

### Memory Endpoints

#### Remember

**POST** `/api/v1/{tenant_id}/remember`

Store a note in memory with optional entity extraction and linking.

**Request:**
```json
{
  "content": "APT28 used CVE-2024-1234 in spear-phishing campaigns targeting defense contractors in Q1 2026. The exploit delivers a custom backdoor with C2 at 192.168.1.100.",
  "metadata": {
    "source": "CISA AA25-100A",
    "confidence": "high",
    "tlp": "TLP_AMBER"
  },
  "options": {
    "extract_entities": true,
    "link_existing": true
  }
}
```

**Response (201 Created):**
```json
{
  "data": {
    "note_id": "note-abc123",
    "content": "APT28 used CVE-2024-1234...",
    "created_at": "2026-04-03T22:30:00Z",
    "entities": [
      {"type": "threat_actor", "name": "APT28", "confidence": 0.95},
      {"type": "cve", "name": "CVE-2024-1234", "confidence": 0.99},
      {"type": "ioc_ipv4", "name": "192.168.1.100", "confidence": 0.98}
    ],
    "linked_notes": ["note-xyz789"]
  },
  "meta": {
    "request_id": "req-jkl-012",
    "timestamp": "2026-04-03T22:30:00Z"
  }
}
```

**Errors:**
- `400 VALIDATION_ERROR` — Content exceeds 10,000 characters
- `400 VALIDATION_ERROR` — Invalid TLP classification
- `413 PAYLOAD_TOO_LARGE` — Request body exceeds 1MB
- `429 RATE_LIMITED` — Tenant rate limit exceeded

---

#### Recall

**POST** `/api/v1/{tenant_id}/recall`

Semantic search across stored notes.

**Request:**
```json
{
  "query": "APT28 campaigns targeting defense contractors",
  "options": {
    "limit": 10,
    "include_entities": true,
    "min_confidence": 0.7,
    "filters": {
      "source": "CISA",
      "date_range": {
        "start": "2026-01-01",
        "end": "2026-04-03"
      }
    }
  }
}
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "note_id": "note-abc123",
      "content": "APT28 used CVE-2024-1234...",
      "score": 0.89,
      "created_at": "2026-04-03T22:30:00Z",
      "entities": [...]
    }
  ],
  "meta": {
    "request_id": "req-mno-345",
    "timestamp": "2026-04-03T22:30:00Z"
  },
  "pagination": {
    "cursor": "eyJub3RlX2lkIjoibm90ZS1kZWY0NTYifQ==",
    "has_more": false,
    "page_size": 10
  }
}
```

---

#### Get Note

**GET** `/api/v1/{tenant_id}/notes/{note_id}`

Retrieve a specific note by ID.

**Response (200 OK):**
```json
{
  "data": {
    "note_id": "note-abc123",
    "content": "APT28 used CVE-2024-1234...",
    "created_at": "2026-04-03T22:30:00Z",
    "updated_at": "2026-04-03T22:30:00Z",
    "metadata": {
      "source": "CISA AA25-100A",
      "confidence": "high",
      "tlp": "TLP_AMBER"
    },
    "entities": [...],
    "links": [
      {"target_note_id": "note-xyz789", "relation": "references"}
    ]
  },
  "meta": {
    "request_id": "req-pqr-678",
    "timestamp": "2026-04-03T22:30:00Z"
  }
}
```

**Errors:**
- `404 RESOURCE_NOT_FOUND` — Note does not exist

---

#### List Notes

**GET** `/api/v1/{tenant_id}/notes`

List notes with pagination and filtering.

**Query Parameters:**
- `page_size` (integer, default 25, max 100)
- `cursor` (opaque string for pagination)
- `source` (filter by source)
- `start_date`, `end_date` (ISO 8601 date filter)
- `tlp` (filter by TLP classification)

**Response (200 OK):**
```json
{
  "data": [...],
  "meta": {
    "request_id": "req-stu-901",
    "timestamp": "2026-04-03T22:30:00Z"
  },
  "pagination": {
    "cursor": "...",
    "has_more": true,
    "page_size": 25
  }
}
```

---

#### Delete Note

**DELETE** `/api/v1/{tenant_id}/notes/{note_id}`

Soft delete a note. Marked for deletion, removed from search index.

**Response (204 No Content)**

---

### Health Endpoints

#### Health Check

**GET** `/api/v1/{tenant_id}/health`

Returns tenant health status.

**Response (200 OK):**
```json
{
  "data": {
    "tenant_id": "acme-corp",
    "status": "healthy",
    "components": {
      "storage": "ok",
      "vector_index": "ok",
      "entity_index": "ok"
    },
    "metrics": {
      "note_count": 1847,
      "storage_bytes": 45678901,
      "last_write": "2026-04-03T22:25:00Z"
    }
  },
  "meta": {
    "request_id": "req-vwx-234",
    "timestamp": "2026-04-03T22:30:00Z"
  }
}
```

**Errors:**
- `503 SERVICE_UNAVAILABLE` — One or more components degraded

---

## Error Response Format

Per GOV-005, all errors use this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Content exceeds maximum length",
    "details": [
      {
        "field": "content",
        "issue": "exceeds_10000_characters",
        "value": "15000"
      }
    ],
    "request_id": "req-abc-123",
    "documentation_url": "https://docs.threatrecall.com/errors/VALIDATION_ERROR"
  }
}
```

### Standard Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_REQUIRED` | 401 | Missing or invalid API key |
| `INSUFFICIENT_PERMISSIONS` | 403 | Valid auth but wrong tenant access |
| `RESOURCE_NOT_FOUND` | 404 | Note or tenant not found |
| `CONFLICT` | 409 | Duplicate resource |
| `PAYLOAD_TOO_LARGE` | 413 | Request body exceeds limit |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Temporary unavailability |

---

## Rate Limiting

Per GOV-005:

**Default limits:**
- 100 requests/minute per tenant
- 1000 requests/hour per tenant

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1712192400
```

**429 Response:**
```
Retry-After: 60
```

---

## Request Identification

Per GOV-005, every request gets a unique `request_id` (UUID v4).

**Client-provided:**
```
X-Request-ID: client-generated-uuid
```

**Server-generated if omitted:** included in all responses and logs for correlation.

---

## OpenAPI 3.1 Specification

Full contract in: `api/openapi.yaml` (to be created)

---

## Compliance Mapping

| Control | Implementation |
|---------|----------------|
| GOV-005 | OpenAPI 3.1 spec, Bearer auth, cursor pagination, error envelope |
| GOV-014 | Vault-backed API keys, 180-day rotation, scoped per-tenant |
| GOV-019 IA-5 | Key rotation, authenticator management |
| GOV-019 IA-8 | API authentication for non-organizational users |
| GOV-019 SC-8 | HTTPS-only, TLS 1.2+ |
| GOV-021 | TLP classification in metadata, per-tenant isolation |

---

## Implementation Priority

**Phase 1 (MVP):**
1. Tenant provisioning endpoint
2. Remember endpoint
3. Recall endpoint
4. Health endpoint

**Phase 2:**
5. Note listing with pagination
6. Note retrieval by ID
7. Note deletion

**Phase 3:**
8. API key rotation
9. Tenant deletion with retention