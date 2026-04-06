# Monitoring Setup

## Prometheus + Grafana

### Prerequisites

```bash
# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --set grafana.enabled=true \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
```

### Deploy Monitoring Resources

```bash
# Apply ServiceMonitor and Grafana dashboard
kubectl apply -f k8s/overlays/production/servicemonitor.yaml
kubectl apply -f k8s/overlays/production/grafana-dashboard.yaml
```

### Access Grafana

```bash
# Port forward
kubectl port-forward svc/prometheus-grafana 3000:80

# Open http://localhost:3000
# Default: admin/prom-operator
```

## Metrics Exposed

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `threatrecall_active_connections` | Gauge | Active connections |
| `threatrecall_notes_created_total` | Counter | Notes created |
| `threatrecall_recalls_total` | Counter | Recall operations |

## Alerts

Example PrometheusRule:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: threatrecall-alerts
spec:
  groups:
    - name: threatrecall
      rules:
        - alert: ThreatRecallHighErrorRate
          expr: sum(rate(http_requests_total{job="threatrecall-api",status=~"5.."}[5m])) / sum(rate(http_requests_total{job="threatrecall-api"}[5m])) > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "ThreatRecall API high error rate"
        - alert: ThreatRecallHighLatency
          expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="threatrecall-api"}[5m])) > 2
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "ThreatRecall API high latency"
```
