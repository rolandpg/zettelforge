import http from 'k6/http';
import { check } from 'k6';

// Stress test: Find breaking point
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Normal load
    { duration: '2m', target: 100 },  // 2x normal
    { duration: '2m', target: 200 },  // 4x normal
    { duration: '2m', target: 400 },  // 8x normal - expect failure
    { duration: '2m', target: 0 },    // Recovery
  ],
  thresholds: {
    http_req_failed: ['rate<0.5'], // Allow up to 50% errors at peak
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function() {
  // Simple health check stress
  const res = http.get(`${BASE_URL}/health`);
  
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
