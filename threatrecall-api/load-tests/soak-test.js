import http from 'k6/http';
import { check, sleep } from 'k6';

// Soak test: Extended duration at moderate load
export const options = {
  stages: [
    { duration: '10m', target: 10 },  // Ramp up
    { duration: '6h', target: 10 },   // 6 hours sustained
    { duration: '10m', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-key';
const TENANT = __ENV.TENANT || 'soak-test';

export function setup() {
  // Create tenant
  const res = http.post(`${BASE_URL}/admin/tenants`, JSON.stringify({
    tenant_id: TENANT,
    tenant_name: 'Soak Test Tenant',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
  
  return { apiKey: res.json('data.api_key') };
}

export default function(data) {
  const headers = {
    'Authorization': `Bearer ${data.apiKey}`,
    'Content-Type': 'application/json',
  };
  
  // Mix of operations
  const rand = Math.random();
  
  if (rand < 0.5) {
    // Health check
    http.get(`${BASE_URL}/health`);
  } else if (rand < 0.8) {
    // Recall
    http.post(`${BASE_URL}/api/v1/${TENANT}/recall`, JSON.stringify({
      query: 'threat actor',
    }), { headers });
  } else {
    // Remember
    http.post(`${BASE_URL}/api/v1/${TENANT}/remember`, JSON.stringify({
      content: `Soak test ${Date.now()}`,
    }), { headers });
  }
  
  sleep(Math.random() * 3 + 1);
}
