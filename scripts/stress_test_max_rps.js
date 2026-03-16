/**
 * k6 constant-arrival-rate test — targets a FIXED number of requests/sec.
 *
 * Usage (on the k6 VM, NOT the app VM):
 *   TARGET_RPS=5000 k6 run -o experimental-prometheus-rw \
 *     --env K6_PROMETHEUS_RW_SERVER_URL=http://APP_VM_IP:9090/api/v1/write \
 *     --env BASE_URL=http://APP_VM_IP \
 *     scripts/stress_test_max_rps.js
 *
 * Increase TARGET_RPS until errors appear → that is your max sustained RPS.
 */
import http from 'k6/http';
import { check } from 'k6';

const targetRPS = parseInt(__ENV.TARGET_RPS || '5000');
const base = __ENV.BASE_URL || 'http://localhost';

export const options = {
  scenarios: {
    constant_load: {
      executor: 'constant-arrival-rate',
      rate: targetRPS,
      timeUnit: '1s',
      duration: '60s',
      preAllocatedVUs: 500,
      maxVUs: 2000,
    },
  },
};

export default function () {
  const res = http.get(`${base}/products/85048`);
  check(res, {
    'status 200': (r) => r.status === 200,
  });
}
