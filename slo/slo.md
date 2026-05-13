# SLI & SLO Definitions — Shop Catalog API

## Service Overview

The Shop Catalog API is a FastAPI backend serving product listings and checkout operations,
backed by PostgreSQL. Load test baseline: 50 concurrent users, 1 minute, ~24 RPS.

---

## SLIs (Service Level Indicators)

| SLI | Description | Prometheus Query |
|-----|-------------|-----------------|
| **Availability** | Fraction of requests that succeed (non-5xx) | `sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| **Latency p95** | 95th percentile response time for /products | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint="/products"}[5m]))` |
| **Latency p50** | Median response time for /products | `histogram_quantile(0.50, rate(http_request_duration_seconds_bucket{endpoint="/products"}[5m]))` |
| **Error Rate** | Fraction of requests returning 5xx | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| **Throughput** | Requests per second across all endpoints | `sum(rate(http_requests_total[5m]))` |

---

## SLOs (Service Level Objectives)

| SLO | Target | Rationale |
|-----|--------|-----------|
| **Availability** | ≥ 99.9% over 30 days | 0/1411 failures in load test; budget = 43 min/month downtime |
| **Latency p95 (/products)** | < 200 ms | Load test p95 = 29 ms; 200 ms gives 6× headroom for production traffic |
| **Latency p50 (/products)** | < 50 ms | Load test p50 = 18 ms |
| **Error Rate** | < 0.1% | Zero errors observed during 50-user load test |
| **Throughput** | ≥ 20 RPS sustained | Load test achieved 23.73 RPS with no degradation |

---

## Error Budget

```
Availability SLO = 99.9%
Monthly error budget = 100% - 99.9% = 0.1%
= 0.001 × 30 days × 24h × 60min = 43.2 minutes per month
```

If the error budget is consumed, new feature deployments are frozen until budget recovers.

---

## Load Test Results (Baseline — 13.05.2026)

| Endpoint | Requests | Failures | Avg (ms) | p50 (ms) | p95 (ms) | RPS |
|----------|----------|----------|----------|----------|----------|-----|
| GET /health | 358 | 0 | 63 | 6 | 11 | 6.02 |
| GET /products | 1053 | 0 | 96 | 18 | 29 | 17.71 |
| **Aggregated** | **1411** | **0** | **88** | **16** | **28** | **23.73** |

All SLOs were met during the baseline load test.

---

## Alert Thresholds (linked to alert_rules.yml)

| Alert | Condition | Severity |
|-------|-----------|----------|
| BackendDown | `up{job="backend"} == 0` for 30s | critical |
| HighCPUUsage | CPU > 70% for 1 min | warning |
| CriticalCPUUsage | CPU > 90% for 1 min | critical |
| HighMemoryUsage | Memory > 80% for 2 min | warning |
