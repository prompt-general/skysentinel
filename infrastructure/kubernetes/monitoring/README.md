# SkySentinel Monitoring Stack

Complete monitoring and observability for SkySentinel production.

## Components

- **Prometheus**: Metrics collection with 100Gi storage
- **Grafana**: Visualization with dashboards
- **Alertmanager**: Slack alert routing
- **Loki**: Log aggregation (50Gi)
- **Jaeger**: Distributed tracing
- **Service Monitors**: SkySentinel service metrics

## Deployment

1. Set environment variables:
```bash
export GRAFANA_ADMIN_PASSWORD="your-password"
export SLACK_WEBHOOK_URL="your-slack-webhook"
export ELASTIC_PASSWORD="your-elastic-password"
```

2. Create namespace:
```bash
kubectl create namespace monitoring
```

3. Deploy in order:
```bash
kubectl apply -f 01-prometheus-stack.yaml
kubectl apply -f 02-skysentinel-rules.yaml
kubectl apply -f 03-loki-stack.yaml
kubectl apply -f 04-jaeger.yaml
kubectl apply -f 05-service-monitors.yaml
kubectl apply -f 06-grafana-dashboards.yaml
```

## Access

- **Grafana**: `kubectl port-forward -n monitoring svc/prometheus-stack-grafana 3000:80`
- **Prometheus**: `kubectl port-forward -n monitoring svc/prometheus-stack-prometheus 9090:9090`
- **Jaeger**: `kubectl port-forward -n monitoring svc/skysentinel-jaeger-query 16686:16686`

## Alerts

Configured for:
- High violation rates
- Critical violations
- API Gateway errors
- Policy engine latency
- Database resource usage
- ML model drift

## Dashboards

- SkySentinel Overview
- Security monitoring
- Infrastructure metrics
