---
document_id: GOV-018
title: Azure Cloud Configuration Guide
version: 1.0.0
last_updated: 2026-04-02
owner: "[CTO/CIO Name]"
classification: Internal
rag_tags: [azure, cloud, gcc-high, dod, endpoints, commercial, government, entra-id, resource-manager, key-vault, storage, multi-cloud]
compliance_mapping: [FedRAMP-SC-7, FedRAMP-SC-8, NIST-800-171-3.13.1]
---

# Azure Cloud Configuration Guide

## Purpose

This document provides the definitive endpoint reference for Azure services across three cloud environments: Azure Commercial (public), Azure Government GCC-High, and Azure Government DoD (IL5). All services built by the organization must support environment selection through configuration rather than hardcoded endpoints. This enables a single codebase to deploy across multiple Azure sovereignty boundaries without code changes.

## Scope

This guide covers Azure service endpoints that the organization's software interacts with. It is the authoritative reference for developers building Azure integrations and for LLM agents generating code that targets Azure services. When in doubt, this document supersedes any AI-generated endpoint assumptions.

## Cloud Environment Selection

The target Azure cloud is determined by the `AZURE_CLOUD` environment variable, which accepts three values: `commercial`, `gcc-high`, or `dod`. Application code reads this value at startup and resolves all Azure endpoints accordingly. The default value is `commercial` for the homelab environment.

### Configuration Pattern

```python
# Python: Azure cloud endpoint resolver
from dataclasses import dataclass
from enum import Enum

class AzureCloud(str, Enum):
    COMMERCIAL = "commercial"
    GCC_HIGH = "gcc-high"
    DOD = "dod"

@dataclass(frozen=True)
class AzureEndpoints:
    """Resolved endpoints for a specific Azure cloud environment."""
    entra_authority: str
    entra_graph: str
    resource_manager: str
    key_vault_suffix: str
    storage_suffix: str
    sql_suffix: str
    log_analytics: str
    service_bus_suffix: str
    cosmos_db_suffix: str
    container_registry_suffix: str

ENDPOINTS: dict[AzureCloud, AzureEndpoints] = {
    AzureCloud.COMMERCIAL: AzureEndpoints(
        entra_authority="https://login.microsoftonline.com",
        entra_graph="https://graph.microsoft.com",
        resource_manager="https://management.azure.com",
        key_vault_suffix="vault.azure.net",
        storage_suffix="core.windows.net",
        sql_suffix="database.windows.net",
        log_analytics="https://api.loganalytics.io",
        service_bus_suffix="servicebus.windows.net",
        cosmos_db_suffix="documents.azure.com",
        container_registry_suffix="azurecr.io",
    ),
    AzureCloud.GCC_HIGH: AzureEndpoints(
        entra_authority="https://login.microsoftonline.us",
        entra_graph="https://graph.microsoft.us",
        resource_manager="https://management.usgovcloudapi.net",
        key_vault_suffix="vault.usgovcloudapi.net",
        storage_suffix="core.usgovcloudapi.net",
        sql_suffix="database.usgovcloudapi.net",
        log_analytics="https://api.loganalytics.us",
        service_bus_suffix="servicebus.usgovcloudapi.net",
        cosmos_db_suffix="documents.azure.us",
        container_registry_suffix="azurecr.us",
    ),
    AzureCloud.DOD: AzureEndpoints(
        entra_authority="https://login.microsoftonline.us",
        entra_graph="https://dod-graph.microsoft.us",
        resource_manager="https://management.usgovcloudapi.net",
        key_vault_suffix="vault.usgovcloudapi.net",
        storage_suffix="core.usgovcloudapi.net",
        sql_suffix="database.usgovcloudapi.net",
        log_analytics="https://api.loganalytics.us",
        service_bus_suffix="servicebus.usgovcloudapi.net",
        cosmos_db_suffix="documents.azure.us",
        container_registry_suffix="azurecr.us",
    ),
}

def get_endpoints(cloud: AzureCloud | None = None) -> AzureEndpoints:
    """Resolve Azure endpoints for the configured cloud environment."""
    if cloud is None:
        cloud = AzureCloud(os.environ.get("AZURE_CLOUD", "commercial"))
    return ENDPOINTS[cloud]
```

```rust
// Rust: Azure cloud endpoint resolver
use std::env;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AzureCloud {
    Commercial,
    GccHigh,
    Dod,
}

pub struct AzureEndpoints {
    pub entra_authority: &'static str,
    pub entra_graph: &'static str,
    pub resource_manager: &'static str,
    pub key_vault_suffix: &'static str,
    pub storage_suffix: &'static str,
    pub sql_suffix: &'static str,
    pub log_analytics: &'static str,
}

impl AzureCloud {
    pub fn from_env() -> Self {
        match env::var("AZURE_CLOUD").as_deref() {
            Ok("gcc-high") => Self::GccHigh,
            Ok("dod") => Self::Dod,
            _ => Self::Commercial,
        }
    }

    pub fn endpoints(&self) -> AzureEndpoints {
        match self {
            Self::Commercial => AzureEndpoints {
                entra_authority: "https://login.microsoftonline.com",
                entra_graph: "https://graph.microsoft.com",
                resource_manager: "https://management.azure.com",
                key_vault_suffix: "vault.azure.net",
                storage_suffix: "core.windows.net",
                sql_suffix: "database.windows.net",
                log_analytics: "https://api.loganalytics.io",
            },
            Self::GccHigh => AzureEndpoints {
                entra_authority: "https://login.microsoftonline.us",
                entra_graph: "https://graph.microsoft.us",
                resource_manager: "https://management.usgovcloudapi.net",
                key_vault_suffix: "vault.usgovcloudapi.net",
                storage_suffix: "core.usgovcloudapi.net",
                sql_suffix: "database.usgovcloudapi.net",
                log_analytics: "https://api.loganalytics.us",
            },
            Self::Dod => AzureEndpoints {
                entra_authority: "https://login.microsoftonline.us",
                entra_graph: "https://dod-graph.microsoft.us",
                resource_manager: "https://management.usgovcloudapi.net",
                key_vault_suffix: "vault.usgovcloudapi.net",
                storage_suffix: "core.usgovcloudapi.net",
                sql_suffix: "database.usgovcloudapi.net",
                log_analytics: "https://api.loganalytics.us",
            },
        }
    }
}
```

## Endpoint Reference Tables

### Identity and Access (Entra ID)

| Service | Commercial | GCC-High | DoD |
|---------|-----------|----------|-----|
| Entra ID Authority | login.microsoftonline.com | login.microsoftonline.us | login.microsoftonline.us |
| Microsoft Graph API | graph.microsoft.com | graph.microsoft.us | dod-graph.microsoft.us |
| Entra ID Graph (legacy) | graph.windows.net | graph.windows.net | graph.windows.net |
| OAuth2 Token Endpoint | login.microsoftonline.com/{tenant}/oauth2/v2.0/token | login.microsoftonline.us/{tenant}/oauth2/v2.0/token | login.microsoftonline.us/{tenant}/oauth2/v2.0/token |

### Management and Compute

| Service | Commercial | GCC-High | DoD |
|---------|-----------|----------|-----|
| Azure Resource Manager | management.azure.com | management.usgovcloudapi.net | management.usgovcloudapi.net |
| Azure Portal | portal.azure.com | portal.azure.us | portal.azure.us |
| Azure Service Management (classic) | management.core.windows.net | management.core.usgovcloudapi.net | management.core.usgovcloudapi.net |

### Data Services

| Service | Commercial Suffix | GCC-High Suffix | DoD Suffix |
|---------|------------------|-----------------|------------|
| Azure Storage (Blob/Queue/Table/File) | .core.windows.net | .core.usgovcloudapi.net | .core.usgovcloudapi.net |
| Azure SQL Database | .database.windows.net | .database.usgovcloudapi.net | .database.usgovcloudapi.net |
| Azure Cosmos DB | .documents.azure.com | .documents.azure.us | .documents.azure.us |
| Azure Cache for Redis | .redis.cache.windows.net | .redis.cache.usgovcloudapi.net | .redis.cache.usgovcloudapi.net |

### Security and Secrets

| Service | Commercial Suffix | GCC-High Suffix | DoD Suffix |
|---------|------------------|-----------------|------------|
| Azure Key Vault | .vault.azure.net | .vault.usgovcloudapi.net | .vault.usgovcloudapi.net |
| Azure Key Vault (HSM) | .managedhsm.azure.net | .managedhsm.usgovcloudapi.net | .managedhsm.usgovcloudapi.net |

### Monitoring and Logging

| Service | Commercial | GCC-High | DoD |
|---------|-----------|----------|-----|
| Log Analytics API | api.loganalytics.io | api.loganalytics.us | api.loganalytics.us |
| Azure Monitor Ingestion | *.ingest.monitor.azure.com | *.ingest.monitor.azure.us | *.ingest.monitor.azure.us |
| Application Insights | dc.applicationinsights.azure.com | dc.applicationinsights.us | dc.applicationinsights.us |

### Messaging and Integration

| Service | Commercial Suffix | GCC-High Suffix | DoD Suffix |
|---------|------------------|-----------------|------------|
| Azure Service Bus | .servicebus.windows.net | .servicebus.usgovcloudapi.net | .servicebus.usgovcloudapi.net |
| Azure Event Hubs | .servicebus.windows.net | .servicebus.usgovcloudapi.net | .servicebus.usgovcloudapi.net |

### Container Services

| Service | Commercial Suffix | GCC-High Suffix | DoD Suffix |
|---------|------------------|-----------------|------------|
| Azure Container Registry | .azurecr.io | .azurecr.us | .azurecr.us |

## Service Availability Differences

Not all Azure services are available in all cloud environments. Before selecting an Azure service for a project, verify its availability in the target deployment environments. The canonical reference is Microsoft's documentation at https://azure.microsoft.com/en-us/explore/global-infrastructure/government/ for GCC-High and DoD availability.

Notable differences that affect architectural decisions: Azure Functions Flex Consumption plan is not available in Government clouds. Azure OpenAI Service has limited model availability in Government clouds. Azure Cosmos DB serverless capacity mode is not available in all Government regions. Azure Container Apps has limited feature parity in Government clouds. Always verify before committing to a service in your architecture design (GOV-016).

## Authentication Differences

The Microsoft Authentication Library (MSAL) handles cloud-specific authentication endpoints automatically when configured with the correct authority URL. For Python, use `msal.ConfidentialClientApplication` or `msal.PublicClientApplication` with the authority from the endpoint configuration. For Rust, the `azure_identity` crate supports cloud selection via environment configuration.

GCC-High and DoD environments use the same Entra ID authority (`login.microsoftonline.us`) but the Microsoft Graph endpoint differs: GCC-High uses `graph.microsoft.us` while DoD uses `dod-graph.microsoft.us`. This is the most commonly missed distinction and causes silent authentication failures or data leakage between tenants if configured incorrectly.

## Infrastructure as Code

OpenTofu (FOSS fork of Terraform) configurations must use the `azurerm` provider's `environment` argument to target the correct cloud:

```hcl
provider "azurerm" {
  features {}
  environment = var.azure_environment  # "public", "usgovernment"
}

variable "azure_environment" {
  type        = string
  default     = "public"
  description = "Azure cloud environment: public, usgovernment"
  validation {
    condition     = contains(["public", "usgovernment"], var.azure_environment)
    error_message = "Must be 'public' or 'usgovernment'."
  }
}
```

Note that the `azurerm` provider uses `usgovernment` for both GCC-High and DoD. The distinction between GCC-High and DoD is made at the tenant and subscription level, not the provider level.

## Testing Multi-Cloud Configurations

Integration tests must validate endpoint resolution for all three cloud environments. Unit tests mock the endpoint resolver and verify that the correct URLs are constructed. A CI pipeline stage specifically tests configuration resolution for each cloud target to prevent regressions where a code change breaks government endpoint compatibility.

## Compliance Notes

Correct cloud endpoint configuration is a foundational requirement for FedRAMP SC-7 (Boundary Protection) and SC-8 (Transmission Confidentiality and Integrity). Traffic intended for government clouds must never be routed through commercial endpoints, and vice versa. Endpoint misconfiguration can constitute a data residency violation. The configuration-driven approach in this document ensures that endpoint selection is auditable and testable.
