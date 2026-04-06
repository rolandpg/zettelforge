import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const recallLatency = new Trend('recall_latency');
const rememberLatency = new Trend('remember_latency');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up
    { duration: '5m', target: 10 },   // Steady state
    { duration: '2m', target: 20 },   // Ramp up
    { duration: '5m', target: 20 },   // Steady state
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% under 2s
    errors: ['rate<0.1'],              // Error rate under 10%
    recall_latency: ['p(95)<1000'],    // Recall under 1s
    remember_latency: ['p(95)<5000'],  // Remember under 5s
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-key';
const TENANT = __ENV.TENANT || 'load-test';

export function setup() {
  // Create tenant
  const tenantRes = http.post(`${BASE_URL}/admin/tenants`, JSON.stringify({
    tenant_id: TENANT,
    tenant_name: 'Load Test Tenant',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
  
  check(tenantRes, {
    'tenant created': (r) => r.status === 201,
  });
  
  const apiKey = tenantRes.json('data.api_key');
  
  // Seed some data
  for (let i = 0; i < 50; i++) {
    http.post(`${BASE_URL}/api/v1/${TENANT}/remember`, JSON.stringify({
      content: `Test memory ${i}: CVE-2024-${1000 + i} exploited by threat actor targeting critical infrastructure`,
      metadata: { source: 'load-test', tlp: 'TLP:GREEN' },
    }), {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
    });
  }
  
  return { apiKey };
}

export default function(data) {
  const headers = {
    'Authorization': `Bearer ${data.apiKey}`,
    'Content-Type': 'application/json',
  };
  
  // 70% recall, 30% remember
  const operation = Math.random() < 0.7 ? 'recall' : 'remember';
  
  if (operation === 'recall') {
    const start = Date.now();
    const res = http.post(`${BASE_URL}/api/v1/${TENANT}/recall`, JSON.stringify({
      query: 'threat actor exploiting CVE',
      options: { limit: 10 },
    }), { headers });
    
    recallLatency.add(Date.now() - start);
    
    const success = check(res, {
      'recall status 200': (r) => r.status === 200,
      'recall has results': (r) => r.json('data') && r.json('data').length > 0,
    });
    
    errorRate.add(!success);
    
  } else {
    const start = Date.now();
    const res = http.post(`${BASE_URL}/api/v1/${TENANT}/remember`, JSON.stringify({
      content: `Load test memory at ${Date.now()}: APT${Math.floor(Math.random() * 50)} activity`,
      metadata: { source: 'k6-load-test' },
    }), { headers });
    
    rememberLatency.add(Date.now() - start);
    
    const success = check(res, {
      'remember status 201': (r) => r.status === 201,
      'remember has note_id': (r) => r.json('data.note_id') !== undefined,
    });
    
    errorRate.add(!success);
  }
  
  sleep(1);
}

export function teardown(data) {
  // Cleanup if needed
  console.log('Load test complete');
}
