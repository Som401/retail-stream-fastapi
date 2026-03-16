/**
 * Gradually ramps request rate to find sustained max throughput.
 *
 * Usage:
 *   k6 run --env BASE_URL=http://10.162.0.2 scripts/stress_test_find_max.js
 */
import http from 'k6/http';
import { check } from 'k6';

const base = __ENV.BASE_URL || 'http://localhost';

export const options = {
  scenarios: {
    ramping_load: {
      executor: 'ramping-arrival-rate',
      startRate: 500,
      timeUnit: '1s',
      preAllocatedVUs: 1000,
      maxVUs: 10000,
      stages: [
        { target: 1000, duration: '30s' },
        { target: 1500, duration: '30s' },
        { target: 2000, duration: '30s' },
        { target: 2500, duration: '30s' },
        { target: 3000, duration: '30s' },
      ],
    },
  },
};

export default function () {
  const res = http.get(`${base}/products/85048`);
  check(res, { 'status 200': (r) => r.status === 200 });
}
