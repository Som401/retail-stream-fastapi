/**
 * k6 constant-arrival-rate test — targets a FIXED number of requests/sec.
 *
 * Same VM (k6 + API together): use TARGET_RPS=2000 so you don't hit VU limit.
 *   k6 run --env TARGET_RPS=2000 -o experimental-prometheus-rw \
 *     --env K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write \
 *     scripts/stress_test_max_rps.js
 *
 * Separate k6 VM (recommended): use higher TARGET_RPS, more VUs available.
 *   TARGET_RPS=6000 ENDPOINT=/products-fast/85048 k6 run -o experimental-prometheus-rw \
 *     --env K6_PROMETHEUS_RW_SERVER_URL=http://APP_VM_IP:9090/api/v1/write \
 *     --env BASE_URL=http://APP_VM_IP \
 *     scripts/stress_test_max_rps.js
 *
 * Rule: maxVUs must be >= TARGET_RPS × avg response time (s). We set 12000 so
 * 6000+ req/s tests have headroom. Increase TARGET_RPS until errors appear.
 */
import http from 'k6/http';
import { check } from 'k6';

const targetRPS = parseInt(__ENV.TARGET_RPS || '6000');
const base = __ENV.BASE_URL || 'http://localhost';
const endpoint = __ENV.ENDPOINT || '/products/85048';

export const options = {
  scenarios: {
    constant_load: {
      executor: 'constant-arrival-rate',
      rate: targetRPS,
      timeUnit: '1s',
      duration: '60s',
      preAllocatedVUs: 2000,
      maxVUs: 12000,
    },
  },
};

export default function () {
  const res = http.get(`${base}${endpoint}`);
  check(res, {
    'status 200': (r) => r.status === 200,
  });
}
