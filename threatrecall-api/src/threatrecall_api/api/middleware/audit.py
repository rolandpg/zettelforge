"""OCSF audit logging for API activity per GOV-012.

OCSF class 6002: API Activity
OCSF class 3001: Authentication
OCSF class 3003: Authorization
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from threatrecall_api.core.logging import get_logger

logger = get_logger("threatrecall_api.audit")


def log_api_activity(
    request_id: str,
    tenant_id: str,
    method: str,
    path: str,
    status_code: int,
    latency_ms: float,
    user_agent: str | None = None,
    src_ip: str | None = None,
) -> None:
    """Log an API request as OCSF class 6002 API Activity."""
    # Determine severity and status_id from HTTP status code
    if status_code < 400:
        severity_id = 1
        status_id = 1  # Success
    elif status_code == 401 or status_code == 403:
        severity_id = 4
        status_id = 2  # Failure
    elif status_code == 429:
        severity_id = 3
        status_id = 2  # Failure
    elif status_code >= 500:
        severity_id = 5
        status_id = 2
    else:
        severity_id = 3
        status_id = 2

    logger.info(
        "api_activity",
        class_uid=6002,
        class_name="API Activity",
        category_uid=3,
        category_name="Identity & Access Management",
        severity_id=severity_id,
        activity_id=1,
        activity_name="Activity",
        status_id=status_id,
        status="Success" if status_id == 1 else "Failure",
        time=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        tenant_id=tenant_id,
        api={
            "operation": {"method": method, "path": path, "version": "v1"},
        },
        http_request={
            "method": method,
            "url": path,
            "user_agent": user_agent,
            "src_endpoint": {"ip": src_ip} if src_ip else None,
        },
        http_response={"code": status_code, "latency_ms": latency_ms},
        metadata={
            "version": "1.3.0",
            "product": {"name": "threatrecall-api", "vendor_name": "Roland Fleet", "version": "1.0.0"},
            "log_name": "api",
            "log_provider": "structlog",
        },
    )


def log_auth_attempt(
    request_id: str,
    tenant_id: str,
    success: bool,
    reason: str | None = None,
    src_ip: str | None = None,
) -> None:
    """Log an authentication event as OCSF class 3001 Authentication."""
    logger.info(
        "authentication_attempt",
        class_uid=3001,
        class_name="Authentication",
        category_uid=3,
        category_name="Identity & Access Management",
        severity_id=4 if not success else 1,
        activity_id=1,
        activity_name="Logon",
        status_id=1 if success else 2,
        status="Success" if success else "Failure",
        time=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        tenant_id=tenant_id,
        actor={"user": {"name": tenant_id, "uid": tenant_id}},
        src_endpoint={"ip": src_ip} if src_ip else None,
        auth_protocol="bearer",
        reason=reason,
        metadata={
            "version": "1.3.0",
            "product": {"name": "threatrecall-api", "vendor_name": "Roland Fleet", "version": "1.0.0"},
            "log_name": "auth",
            "log_provider": "structlog",
        },
    )
