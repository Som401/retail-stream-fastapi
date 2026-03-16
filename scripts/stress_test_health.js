/**
 * k6 test that hammers ONLY /health — no DB, no Redis.
 * This measures your pure Nginx → FastAPI throughput ceiling.
 *
 * Usage:
 *   TARGET_RPS=50000 k6 run --env BASE_URL=http://APP_VM_IP \
 *     scripts/stress_test_health.js
 */
import http from 'k6/http';
import { check } from 'k6';

const targetRPS = parseInt(__ENV.TARGET_RPS || '50000');
const base = __ENV.BASE_URL || 'http://localhost';

export const options = {
  scenarios: {
    constant_load: {
      executor: 'constant-arrival-rate',
      rate: targetRPS,
      timeUnit: '1s',
      duration: '30s',
      preAllocatedVUs: 500,
      maxVUs: 5000,
    },
  },
};

export default function () {
  const res = http.get(`${base}/health`);
  check(res, {
    'status 200': (r) => r.status === 200,
  });
}
