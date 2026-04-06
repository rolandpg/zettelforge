# Load Testing with k6

## Prerequisites

```bash
# Install k6
brew install k6  # macOS
# or
sudo apt-get install k6  # Ubuntu/Debian
```

## Test Types

### 1. Load Test (Default)

Tests expected load with gradual ramp-up.

```bash
cd load-tests

# Run against local instance
k6 run load-test.js

# Run against staging
BASE_URL=https://api-staging.threatrecall.local \
API_KEY=tr_live_xxx \
k6 run load-test.js
```

**Scenario:**
- Ramp to 10 VUs over 2 minutes
- Hold at 10 VUs for 5 minutes
- Ramp to 20 VUs over 2 minutes
- Hold at 20 VUs for 5 minutes
- Ramp down

**Metrics:**
- p95 latency < 2s
- Error rate < 10%
- Recall latency < 1s
- Remember latency < 5s

### 2. Stress Test

Finds the breaking point by overwhelming the system.

```bash
k6 run stress-test.js
```

**Scenario:**
- Ramp to 50, 100, 200, 400 VUs
- Identifies at what load the system fails
- Observes recovery after ramp-down

### 3. Soak Test

Validates stability over extended duration.

```bash
k6 run soak-test.js
```

**Scenario:**
- 10 VUs sustained for 6 hours
- Detects memory leaks, connection pool exhaustion
- Validates no degradation over time

## Analyzing Results

### CLI Output

```
     data_received..................: 15 MB  50 kB/s
     data_sent......................: 3.0 MB 10 kB/s
     http_req_blocked...............: avg=1.23ms  min=0s     med=1µs    max=100ms
     http_req_connecting............: avg=0.98ms  min=0s     med=0s     max=50ms
     http_req_duration..............: avg=456ms   min=12ms   med=234ms  max=5s
     http_req_failed................: 0.50%   ✓ 1990  ✗ 10
     http_req_receiving.............: avg=0.12ms  min=0s     med=0.1ms  max=5ms
     http_req_sending...............: avg=0.05ms  min=0s     med=0.05ms max=2ms
     http_req_waiting...............: avg=455ms   min=12ms   med=233ms  max=5s
     http_reqs......................: 2000   6.67/s
     iteration_duration.............: avg=1.45s   min=1.01s  med=1.23s  max=6s
     iterations.....................: 2000   6.67/s
     vus............................: 10     min=10 max=10
     vus_max........................: 10     min=10 max=10
```

### Cloud Results

For CI/CD integration:

```bash
# Run in k6 Cloud (requires API token)
k6 cloud load-test.js

# Or stream to Grafana Cloud
k6 run --out influxdb=http://localhost:8086/k6 load-test.js
```

## CI/CD Integration

Add to GitHub Actions:

```yaml
- name: Load Test
  run: |
    docker run --rm -v $(pwd)/load-tests:/tests \
      -e BASE_URL=http://localhost:8000 \
      grafana/k6 run /tests/load-test.js
```

## Interpreting Failures

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| High latency, low CPU | Ollama bottleneck | Scale Ollama replicas |
| Connection timeouts | Connection pool | Increase pool size |
| Memory growth | Memory leak | Check for unclosed resources |
| 500 errors | Application crash | Check logs, fix bugs |
| Slow recall | LanceDB index | Optimize index, add caching |

## Recommended Schedule

- **Load test**: Before each release
- **Stress test**: Monthly or before major events
- **Soak test**: Quarterly or after infrastructure changes
