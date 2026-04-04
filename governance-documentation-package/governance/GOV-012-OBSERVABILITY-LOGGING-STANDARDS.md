---
document_id: GOV-012
title: Observability and Logging Standards
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [logging, ocsf, observability, metrics, tracing, structured-logging, audit, cmmc, siem, fluentd, prometheus, grafana]
compliance_mapping: [FedRAMP-AU-2, FedRAMP-AU-3, FedRAMP-AU-6, FedRAMP-AU-8, FedRAMP-AU-12, FedRAMP-SI-4, NIST-800-171-3.3.1, NIST-800-171-3.3.2, NIST-800-171-3.3.3, NIST-800-171-3.3.4]
---

# Observability and Logging Standards

## Purpose

This document defines the mandatory logging format, audit event requirements, metrics collection, distributed tracing, and alerting standards for all software. Observability is how you know your systems are working correctly. Audit logging is how you prove to compliance auditors that security controls are functioning. These standards use the Open Cybersecurity Schema Framework (OCSF) as the canonical event schema to ensure all security-relevant events are structured, normalized, and ingestible by any SIEM platform, including Microsoft Sentinel.

## Scope

These standards apply to all software components: backend services, API gateways, background workers, scheduled tasks, CLI tools that run in production, and infrastructure automation. Every component that runs in a managed environment produces structured logs.

## OCSF Event Schema

All security-relevant events use the OCSF schema (https://schema.ocsf.io). OCSF provides a vendor-agnostic, normalized event format that maps directly to CMMC and NIST 800-171 audit requirements. The organization uses OCSF v1.3 as the baseline schema version.

### Required OCSF Base Fields

Every log event must include these OCSF base attributes:

```json
{
    "class_uid": 3001,
    "class_name": "Authentication",
    "category_uid": 3,
    "category_name": "Identity & Access Management",
    "severity_id": 1,
    "severity": "Informational",
    "activity_id": 1,
    "activity_name": "Logon",
    "status_id": 1,
    "status": "Success",
    "time": "2026-04-02T14:30:00.000Z",
    "timezone_offset": -360,
    "metadata": {
        "version": "1.3.0",
        "product": {
            "name": "project-name",
            "vendor_name": "organization-name",
            "version": "1.2.3"
        },
        "log_name": "application",
        "log_provider": "structlog"
    },
    "observables": [],
    "unmapped": {}
}
```

### OCSF Event Classes in Use

The following OCSF event classes are mandatory for the organization's logging requirements. Each maps to specific CMMC/NIST 800-171 audit requirements.

**Authentication (class_uid: 3001)** captures all authentication attempts, both successful and failed. Maps to NIST 800-171 3.3.1 (create and retain system audit logs) and 3.3.2 (ensure actions are traceable to individual users). Required fields: `actor` (who attempted authentication), `auth_protocol` (method used), `dst_endpoint` (target system), `status_id` (success/failure), `src_endpoint` (origin IP/hostname).

**Authorization (class_uid: 3003)** captures all authorization decisions where access is granted or denied. Maps to NIST 800-171 3.3.1 and 3.1.2 (limit system access to authorized transactions). Required fields: `actor`, `privileges` (requested permissions), `resource` (target resource), `status_id`, `policy` (which policy or rule applied).

**API Activity (class_uid: 6002)** captures all API requests and responses for audit trail purposes. Maps to NIST 800-171 3.3.1 and 3.14.6 (monitor organizational systems). Required fields: `actor`, `api` (endpoint, method, version), `http_request` (method, url, user_agent), `http_response` (code), `src_endpoint`, `dst_endpoint`.

**Configuration Change (class_uid: 5002)** captures all changes to system configuration, feature flags, and environment settings. Maps to NIST 800-171 3.4.3 (track, review, approve configuration changes). Required fields: `actor`, `resource` (what was changed), `prev_value`, `new_value`, `status_id`.

**File Activity (class_uid: 1001)** captures file creation, modification, deletion, and access events for sensitive data. Maps to NIST 800-171 3.3.1 and 3.8.4 (mark media with CUI markings and distribution limitations). Required fields: `actor`, `file` (name, path, type, hash), `activity_id` (create/read/update/delete).

**Process Activity (class_uid: 1007)** captures service start, stop, crash, and restart events. Maps to NIST 800-171 3.3.1. Required fields: `process` (name, pid, command_line), `activity_id`, `status_id`.

**Account Change (class_uid: 3005)** captures user account creation, modification, disabling, and deletion. Maps to NIST 800-171 3.3.1 and 3.5.7 (enforce minimum password complexity). Required fields: `actor`, `user` (the account being modified), `activity_id`, `prev_value`, `new_value`.

### OCSF Severity Mapping

OCSF severity IDs map to operational meaning as follows. Severity 0 (Unknown) is never used in production logging. Severity 1 (Informational) captures routine successful operations: successful auth, normal API calls, scheduled task completions. Severity 2 (Low) captures minor anomalies that do not require action: retry succeeded, deprecated endpoint usage. Severity 3 (Medium) captures events requiring attention within business hours: rate limiting triggered, configuration drift detected. Severity 4 (High) captures events requiring prompt response: authentication failures exceeding threshold, unauthorized access attempts, service degradation. Severity 5 (Critical) captures events requiring immediate response: service outage, data breach indicators, security control failures.

## Application Logging Implementation

### Python

Python services use `structlog` configured to output JSON with OCSF-compatible field names. A shared logging configuration module standardizes the output format across all Python services.

```python
import structlog
from datetime import datetime, timezone

def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="time"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

# Usage: emit an OCSF-structured authentication event
logger.info(
    "authentication_attempt",
    class_uid=3001,
    class_name="Authentication",
    category_uid=3,
    activity_id=1,
    activity_name="Logon",
    status_id=1,
    status="Success",
    actor={"user": {"name": username, "uid": user_id}},
    src_endpoint={"ip": request.client.host},
    auth_protocol="jwt",
)
```

### Rust

Rust services use the `tracing` crate with a JSON subscriber configured to emit OCSF-compatible fields. The `tracing-subscriber` crate with `fmt::layer().json()` provides the JSON output.

### Logging Rules

Never log secrets, credentials, tokens, passwords, API keys, or encryption keys. Never log PII (names, emails, SSNs, phone numbers) in fields that are not explicitly designated for actor identification in the OCSF schema. Never use `print()` or `println!()` for production output. Use static message templates with structured data fields (not string interpolation) to enable log aggregation and indexing. Include the `request_id` in every log entry for a request lifecycle to enable correlation.

## Log Collection and Aggregation

Logs are collected from application containers using Fluent Bit (FOSS, lightweight log forwarder). Fluent Bit runs as a sidecar or DaemonSet and forwards logs to OpenSearch (FOSS fork of Elasticsearch) for storage, indexing, and search. OpenSearch Dashboards (FOSS fork of Kibana) provides the log exploration interface.

For environments integrated with Microsoft Sentinel, Fluent Bit is also configured to forward OCSF-formatted events to a Log Analytics Workspace via the Azure Monitor HTTP Data Collector API. The OCSF schema fields map to Sentinel custom log tables, enabling correlation with other Sentinel data sources.

### Log Retention

Application logs are retained for 90 days in the hot tier (OpenSearch, searchable). Security-relevant audit logs (OCSF classes 3001, 3003, 3005, 5002) are retained for 1 year in the warm tier (compressed storage, queryable with delay). Compliance requires a minimum of 1 year retention for all audit-relevant events per NIST 800-171 3.3.1.

## Metrics Collection

Application metrics are collected using Prometheus (FOSS) with client libraries for Python (`prometheus-client`) and Rust (`prometheus` crate). Metrics are exposed on a `/metrics` endpoint (internal network only, not exposed to external consumers).

### Required Metrics

Every service must expose: `http_requests_total` (counter, labeled by method, endpoint, status code), `http_request_duration_seconds` (histogram, labeled by method and endpoint), `http_requests_in_progress` (gauge), and service-specific business metrics relevant to SLOs.

### Dashboards and Alerting

Grafana (FOSS) visualizes metrics from Prometheus and logs from OpenSearch. Each service has a standard dashboard including: request rate, error rate, latency percentiles (p50, p95, p99), and resource utilization. Alerting rules are defined in Grafana and route notifications to the appropriate channel. Alert thresholds are derived from SLOs defined per-service.

## Distributed Tracing

For multi-service architectures, distributed tracing uses OpenTelemetry (FOSS) with Jaeger (FOSS) as the trace backend. The `request_id` generated at the API gateway propagates through all downstream service calls via the `X-Request-ID` header and the OpenTelemetry trace context (`traceparent` header). Every log entry, metric label, and trace span includes the `request_id` for full correlation.

## Compliance Notes

These standards satisfy FedRAMP AU-2 (Audit Events) through the defined OCSF event classes, AU-3 (Content of Audit Records) through the required OCSF fields, AU-6 (Audit Review, Analysis, and Reporting) through the OpenSearch/Grafana analysis capabilities, AU-8 (Time Stamps) through UTC timestamps on all events, AU-12 (Audit Generation) through mandatory structured logging in all services, and SI-4 (Information System Monitoring) through the metrics and alerting requirements. The OCSF schema ensures that audit events are normalized across all applications and directly ingestible by Sentinel or any other SIEM that supports OCSF.
