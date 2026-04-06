# Architecture

## System Overview

ThreatRecall API is a multi-tenant, cybersecurity-focused memory service built on the A-MEM (Agentic Memory) architecture.

## Components

### 1. API Layer (FastAPI)

**Responsibilities:**
- HTTP request handling
- Authentication (Bearer tokens)
- Request validation (Pydantic models)
- Rate limiting (token bucket)
- OCSF audit logging

**Key Modules:**
- `main.py` — Application entry point
- `api/routes/` — Endpoint handlers
- `api/middleware/` — Audit, rate limiting
- `api/dependencies.py` — DI for tenant context

### 2. Tenant Isolation

Each tenant receives:
- Dedicated subdirectory: `/data/threatrecall/tenants/{tenant_id}/`
- Isolated JSONL file: `notes.jsonl`
- Dedicated LanceDB: `lance/`
- Separate MemoryManager instance

**Storage Layout:**
```
/data/threatrecall/
├── tenants/
│   ├── acme-corp/
│   │   ├── notes.jsonl
│   │   └── lance/
│   └── cyberdyne/
│       ├── notes.jsonl
│       └── lance/
└── cold/  # Archive storage
```

### 3. MemoryManager (A-MEM Core)

The heart of the system — manages the complete memory lifecycle.

**Pipeline:**
```
Input → Deduplication → Enrichment → Entity Extraction → 
Vector Embedding → Linking → Storage → Evolution
```

**Components:**
- **NoteConstructor**: Builds structured notes from raw text
- **EntityIndexer**: Indexes CVEs, actors, tools for fast lookup
- **LinkGenerator**: Connects related notes
- **VectorRetriever**: Semantic search via embeddings
- **MemoryEvolver**: Updates notes based on new information

### 4. Vector Storage (LanceDB)

Stores embeddings for semantic search:
- Model: `nomic-embed-text` via Ollama
- Dimension: 768
- Similarity: Cosine
- Threshold: 0.30

### 5. Entity Resolution

**Alias Resolution:**
- Maps variants to canonical names
- Example: "Fancy Bear" → "APT28"
- Stored in `entity_index.json`

**Supported Entities:**
- CVE IDs (CVE-YYYY-NNNN)
- Threat Actors (APT28, Lazarus Group)
- Tools (Cobalt Strike, Mimikatz)
- Campaigns (SolarWinds, NotPetya)
- Sectors (DIB, Finance, Healthcare)

## Data Flow

### Store Memory (Remember)

```
1. Client POST /api/v1/{tenant}/remember
2. Auth middleware validates Bearer token
3. Audit middleware logs request (OCSF 6002)
4. Rate limiter checks quota
5. TenantContext extracts tenant_id
6. MemoryManager.remember():
   a. Deduplication check
   b. Note construction (LLM enrichment)
   c. Entity extraction
   d. Vector embedding (Ollama)
   e. Link generation
   f. Write to JSONL
   g. Index in LanceDB
   h. Update entity index
   i. Trigger evolution
7. Return note with entities/links
```

### Search Memory (Recall)

```
1. Client POST /api/v1/{tenant}/recall
2. Auth middleware validates token
3. TenantContext extracts tenant_id
4. MemoryManager.recall():
   a. Embed query (Ollama)
   b. Vector search (LanceDB)
   c. Filter by similarity threshold
   d. Expand via links (if requested)
   e. Sort by relevance
5. Return scored results
```

## Security Model

### Authentication

- Bearer tokens per tenant
- Tokens stored in Vault (production)
- Constant-time comparison
- No token in logs

### Authorization

- Tenant isolation at storage layer
- Tokens scoped to single tenant
- Path-based tenant extraction
- No cross-tenant access possible

### Audit Logging

OCSF Class 6002 (API Activity):
```json
{
  "class_uid": 6002,
  "activity_id": 1,
  "status_id": 1,
  "time": "2024-04-05T12:00:00Z",
  "request_id": "req_abc123",
  "tenant_id": "acme-corp",
  "api": {
    "operation": {
      "method": "POST",
      "path": "/api/v1/acme-corp/remember"
    }
  },
  "http_response": {
    "code": 201,
    "latency_ms": 1250
  }
}
```

## Scaling Strategy

### Horizontal Scaling

**Stateless Components:**
- API pods: Scale 3-10 via HPA
- No session affinity required

**Stateful Components:**
- PVC per tenant (ReadWriteOnce)
- Pod anti-affinity spreads across nodes
- Single pod per tenant (for now)

### Future Improvements

1. **Shared Storage**: Move to ReadWriteMany PVC or object storage
2. **Redis**: Distributed rate limiting
3. **Caching**: Redis for frequent queries
4. **Sharding**: Tenant-to-pod mapping for large tenants

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Health check | <10ms | No auth required |
| Remember | 1-3s | Includes LLM embedding |
| Recall | 100-500ms | Vector search + ranking |
| Entity lookup | <50ms | Indexed O(1) access |

**Bottlenecks:**
- Ollama embedding generation (CPU-bound)
- LanceDB index building (first write)
- LLM-based enrichment (optional)

## Deployment Patterns

### Single Node (Homelab)

```
Docker Compose
├── threatrecall-api (container)
├── Ollama (container)
└── Shared volume (bind mount)
```

### Kubernetes (Production)

```
Namespace: threatrecall-production
├── Deployment (3 replicas)
├── Service (ClusterIP)
├── Ingress (TLS termination)
├── PVC (100Gi)
├── HPA (3-10 pods)
├── PDB (min 2 available)
└── ServiceMonitor (Prometheus)
```

## Failure Scenarios

### Pod Restart

- **Impact**: Temporary unavailability
- **Recovery**: Kubernetes recreates pod
- **Data**: Persisted in PVC, no loss

### Node Failure

- **Impact**: Pods on failed node
- **Recovery**: Pods rescheduled, PVC reattached
- **RPO**: Zero (synchronous write)
- **RTO**: ~60s (pod startup)

### Database Corruption

- **Impact**: Tenant data unreadable
- **Recovery**: Restore from Velero backup
- **RPO**: 24 hours (daily backups)

### Ollama Unavailable

- **Impact**: Embeddings fail
- **Recovery**: Automatic retry
- **Fallback**: Keyword search only

## Monitoring Points

### Metrics

- `http_requests_total` — Request count
- `http_request_duration_seconds` — Latency histogram
- `threatrecall_notes_created_total` — Note creation rate
- `threatrecall_recalls_total` — Query rate

### Alerts

- High error rate (>5%)
- High latency (p95 >2s)
- Pod restart loop
- PVC capacity >80%

## Future Architecture

### Phase 2: Distributed

- Redis for shared state
- Separate embedding service
- Async processing queue

### Phase 3: Multi-Region

- Read replicas per region
- Cross-region backup
- Geo-routing

### Phase 4: Serverless

- Knative/Kubernetes Functions
- Pay-per-request
- Auto-scale to zero
