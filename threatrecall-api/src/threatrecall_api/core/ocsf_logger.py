"""OCSF-compliant audit logging for ThreatRecall API.

Implements OCSF class 6002 (API Activity), 3001 (Authentication), and 3003 (Authorization)
events per GOV-012. All events are structured for direct ingestion by Microsoft Sentinel
and other OCSF-compatible SIEMs.

GOV-012 Compliance: All API activity must be logged as OCSF events with proper
class_uid, activity_id, severity_id, and metadata.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

from threatrecall_api.core.config import settings
from threatrecall_api.core.logging import get_logger

logger = get_logger("ocsf")


class OCSFEvent:
    """Base class for OCSF events."""

    def __init__(self, class_uid: int, activity_id: int, severity_id: int = 1):
        self.class_uid = class_uid
        self.activity_id = activity_id
        self.severity_id = severity_id
        self.time = int(datetime.now(timezone.utc).timestamp() * 1000)
        self.request_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to OCSF-compliant dictionary."""
        return {
            "class_uid": self.class_uid,
            "activity_id": self.activity_id,
            "severity_id": self.severity_id,
            "time": self.time,
            "request_id": self.request_id,
        }


class APIActivityEvent(OCSFEvent):
    """OCSF Class 6002 - API Activity."""

    def __init__(self,
                 method: str,
                 path: str,
                 status_code: int,
                 latency_ms: float,
                 tenant_id: str = "unknown",
                 user_agent: Optional[str] = None,
                 src_ip: Optional[str] = None):
        super().__init__(class_uid=6002, activity_id=1, severity_id=1 if status_code < 400 else 5)

        self.method = method
        self.path = path
        self.status_code = status_code
        self.latency_ms = round(latency_ms, 2)
        self.tenant_id = tenant_id
        self.user_agent = user_agent
        self.src_ip = src_ip

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "class_name": "API Activity",
            "category_uid": 3,
            "category_name": "Identity & Access Management",
            "activity_name": "Activity",
            "status_id": 1 if self.status_code < 400 else 2,
            "status": "Success" if self.status_code < 400 else "Failure",
            "tenant_id": self.tenant_id,
            "api": {
                "operation": {
                    "method": self.method,
                    "path": self.path,
                    "version": "v1"
                }
            },
            "http_request": {
                "method": self.method,
                "url": self.path,
                "user_agent": self.user_agent,
                "src_endpoint": {
                    "ip": self.src_ip
                } if self.src_ip else {}
            },
            "http_response": {
                "code": self.status_code,
                "latency_ms": self.latency_ms
            },
            "metadata": {
                "version": "1.3.0",
                "product": {
                    "name": "threatrecall-api",
                    "vendor_name": "Roland Fleet",
                    "version": "1.0.0"
                },
                "log_name": "api",
                "log_provider": "structlog"
            },
            "event": "api_activity",
            "level": "info" if self.status_code < 400 else "warning"
        })
        return base


class AuthenticationEvent(OCSFEvent):
    """OCSF Class 3001 - Authentication."""

    def __init__(self, success: bool, tenant_id: str = "unknown", reason: str = None):
        super().__init__(class_uid=3001, activity_id=1, severity_id=1 if success else 5)
        self.success = success
        self.tenant_id = tenant_id
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "class_name": "Authentication",
            "category_uid": 3,
            "category_name": "Identity & Access Management",
            "activity_name": "Logon" if self.success else "Logon Failure",
            "status_id": 1 if self.success else 2,
            "status": "Success" if self.success else "Failure",
            "tenant_id": self.tenant_id,
            "auth": {
                "method": "bearer",
                "success": self.success
            },
            "metadata": {
                "version": "1.3.0",
                "product": {
                    "name": "threatrecall-api",
                    "vendor_name": "Roland Fleet",
                    "version": "1.0.0"
                },
                "log_name": "auth",
                "log_provider": "structlog"
            }
        })
        if self.reason:
            base["auth"]["reason"] = self.reason
        return base


class OCSFLogger:
    """Centralized OCSF logging service."""

    def __init__(self):
        self.logger = logger

    def log_api_activity(self,
                        request_id: str,
                        tenant_id: str,
                        method: str,
                        path: str,
                        status_code: int,
                        latency_ms: float,
                        user_agent: Optional[str] = None,
                        src_ip: Optional[str] = None):
        """Log API activity as OCSF class 6002 event."""
        event = APIActivityEvent(
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=latency_ms,
            tenant_id=tenant_id,
            user_agent=user_agent,
            src_ip=src_ip
        )

        # Add request_id to the base event if not already present
        event_dict = event.to_dict()
        event_dict["request_id"] = request_id

        self.logger.info("API Activity", extra={"ocsf": event_dict})

    def log_auth_attempt(self, success: bool, tenant_id: str = "unknown", reason: str = None):
        """Log authentication attempt as OCSF class 3001 event."""
        event = AuthenticationEvent(success=success, tenant_id=tenant_id, reason=reason)
        self.logger.info("Authentication", extra={"ocsf": event.to_dict()})

    def log_api_error(self, error_code: str, message: str, request_id: str, tenant_id: str = "unknown"):
        """Log API errors with OCSF metadata."""
        self.logger.error("API Error", extra={
            "error_code": error_code,
            "message": message,
            "request_id": request_id,
            "tenant_id": tenant_id,
            "ocsf": {
                "class_uid": 4002,  # Security Finding
                "severity_id": 5,   # High
                "activity_id": 1,
                "time": int(datetime.now(timezone.utc).timestamp() * 1000),
                "request_id": request_id,
                "tenant_id": tenant_id,
                "finding": {
                    "type_id": 1,  # Policy violation
                    "name": error_code,
                    "desc": message
                }
            }
        })


# Global logger instance
ocsf_logger = OCSFLogger()


def log_api_activity(request_id: str, tenant_id: str, method: str, path: str,
                    status_code: int, latency_ms: float, user_agent: Optional[str] = None,
                    src_ip: Optional[str] = None):
    """Convenience function for logging API activity."""
    ocsf_logger.log_api_activity(
        request_id=request_id,
        tenant_id=tenant_id,
        method=method,
        path=path,
        status_code=status_code,
        latency_ms=latency_ms,
        user_agent=user_agent,
        src_ip=src_ip
    )


def log_auth_attempt(success: bool, tenant_id: str = "unknown", reason: str = None):
    """Convenience function for logging authentication attempts."""
    ocsf_logger.log_auth_attempt(success=success, tenant_id=tenant_id, reason=reason)
