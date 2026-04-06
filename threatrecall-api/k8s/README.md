# Kubernetes Deployment

Production-ready Kubernetes manifests using Kustomize.

## Structure

```
k8s/
├── base/                    # Base manifests
│   ├── deployment.yaml      # API deployment
│   ├── service.yaml         # ClusterIP service
│   ├── pvc.yaml             # Persistent volume for data
│   ├── ingress.yaml         # NGINX ingress with TLS
│   ├── configmap.yaml       # Non-sensitive configuration
│   └── kustomization.yaml
├── overlays/
│   ├── staging/             # Staging environment
│   │   └── kustomization.yaml
│   └── production/          # Production environment
│       ├── kustomization.yaml
│       ├── hpa.yaml         # Horizontal pod autoscaling
│       └── pdb.yaml         # Pod disruption budget
```

## Deploy to Staging

```bash
# Create namespace
kubectl create namespace threatrecall-staging

# Deploy
kubectl apply -k k8s/overlays/staging/

# Verify
kubectl get pods -n threatrecall-staging
kubectl get svc -n threatrecall-staging
```

## Deploy to Production

```bash
# Create namespace
kubectl create namespace threatrecall-production

# Deploy
kubectl apply -k k8s/overlays/production/

# Verify
kubectl get pods -n threatrecall-production
kubectl get hpa -n threatrecall-production
```

## Requirements

- Kubernetes 1.24+
- NGINX Ingress Controller
- cert-manager (for TLS)
- Storage class `standard` (or modify PVC)

## Secrets

Create secrets for production:

```bash
kubectl create secret generic threatrecall-secrets \
  --from-literal=VAULT_TOKEN=your-token \
  --namespace threatrecall-production
```

## Monitoring

The deployment includes:
- **Liveness probe**: `/health` endpoint
- **Readiness probe**: `/health` endpoint
- **HPA**: Auto-scaling 3-10 pods based on CPU/memory
- **PDB**: Ensures minimum 2 pods during disruptions
- **Pod anti-affinity**: Spreads pods across nodes

## Troubleshooting

```bash
# Check pod status
kubectl describe pod -l app=threatrecall-api -n threatrecall-production

# View logs
kubectl logs -l app=threatrecall-api -n threatrecall-production --tail=100

# Shell into pod
kubectl exec -it deployment/threatrecall-api -n threatrecall-production -- /bin/sh
```
