# ThreatRecall API Azure Deployment Plan

**Date:** 2026-04-06  
**Status:** Draft (Pending Approval)  
**Application:** ThreatRecall API  
**Type:** Python FastAPI Application with LanceDB  

---

## Executive Summary

Deploy ThreatRecall API to Azure with the following architecture:
- **Azure Container Apps** (or **Azure App Service** if preferred)
- **Azure Database for PostgreSQL** (optional - LanceDB uses local files)
- **Azure Key Vault** for secrets
- **Azure Application Insights** for monitoring
- **Cloudflare** for DNS and SSL (existing setup)

---

## 1. Application Analysis

### Components
| Component | Technology | Azure Service |
|-----------|-----------|---------------|
| API | Python 3.12 + FastAPI | Container Apps / App Service |
| Memory Engine | ZettelForge (Python) | Same container |
| Vector DB | LanceDB (file-based) | Azure Files (persistent storage) |
| Secrets | HashiCorp Vault → Azure Key Vault | Key Vault |
| Monitoring | structlog | Application Insights |

### Requirements
- **Compute:** ARM64 support (DGX Spark) or x86_64
- **Storage:** Persistent volume for LanceDB data
- **Memory:** 2-4 GB RAM minimum
- **Secrets:** API keys, database credentials
- **Networking:** HTTPS endpoint exposed

---

## 2. Architecture Decisions

### Option A: Azure Container Apps (Recommended)
- **Pros:** Serverless containers, auto-scaling, persistent storage support, cost-effective
- **Cons:** Less control than VMs
- **Best for:** API workloads with variable traffic

### Option B: Azure App Service
- **Pros:** Easy deployment, built-in CI/CD, managed platform
- **Cons:** Less flexibility with custom containers
- **Best for:** Simple web apps

### Option C: Azure VM (DGX Spark equivalent)
- **Pros:** Full control, ARM64 support, GPU access
- **Cons:** Higher cost, more management
- **Best for:** Development matching production hardware

**Recommendation:** Start with **Azure Container Apps** for cost-effectiveness and scalability.

---

## 3. Infrastructure Components

| Resource | Purpose | Estimated Cost |
|----------|---------|---------------|
| Container Apps Environment | Host ThreatRecall API | ~$15-50/month |
| Azure Files (Premium) | LanceDB persistent storage | ~$10-30/month |
| Key Vault | Secrets management | ~$0.03/10k operations |
| Application Insights | Monitoring/logging | ~$2.30/GB |
| Container Registry | Store Docker images | ~$5/month |

**Estimated Total:** $30-100/month (depends on usage)

---

## 4. Deployment Steps

### Phase 1: Infrastructure (Bicep)
1. Create Resource Group
2. Deploy Container Apps Environment
3. Create Azure Files share for LanceDB
4. Deploy Key Vault with secrets
5. Create Application Insights
6. Deploy Container Registry

### Phase 2: Application
1. Build Docker image with ZettelForge
2. Push to Azure Container Registry
3. Deploy to Container Apps
4. Configure environment variables
5. Mount persistent storage

### Phase 3: DNS & SSL
1. Point `threatrecall.ai` to Azure endpoint
2. Configure Cloudflare SSL/TLS
3. Set up WAF rules

---

## 5. Configuration

### Environment Variables (Key Vault)
```
TR_SECRETS_BACKEND=azure
TR_DATA_DIR=/data/threatrecall
TR_LOG_LEVEL=INFO
TR_AZURE_KEYVAULT_URL=https://<vault>.vault.azure.net/
```

### Secrets to Store
- Cloudflare API token
- Ollama endpoint credentials (if external)
- Database credentials (if using PostgreSQL)

---

## 6. Security Considerations

- **Managed Identity** for Key Vault access
- **Private Container Registry**
- **HTTPS only** (enforced)
- **WAF rules** via Cloudflare
- **Network isolation** (private subnet optional)

---

## 7. Rollback Plan

- Container Apps supports immediate rollback to previous revision
- Azure Files snapshots for data backup
- Key Vault secret versioning

---

## Approval Required

**Ready to proceed?** Reply with:
- **"Approve"** - Use Container Apps (recommended)
- **"Approve App Service"** - Use Azure App Service instead
- **"Approve VM"** - Use Azure VM for full control
- **"Modify"** - Change specific aspects

---

*Plan created by Nexus using azure-prepare skill*
