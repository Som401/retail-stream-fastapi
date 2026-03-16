/**
 * Ramps request rate from 1k to 10k to find sustained max throughput.
 * Watch for the point where error rate jumps above 1% — that's your ceiling.
 *
 * Usage:
 *   k6 run --env BASE_URL=http://10.162.0.2 scripts/stress_test_find_max.js
 */
import http from 'k6/http';
import { check } from 'k6';

const base = __ENV.BASE_URL || 'http://localhost';
const endpoint = __ENV.ENDPOINT || '/products/85048';

export const options = {
  scenarios: {
    ramping_load: {
      executor: 'ramping-arrival-rate',
      startRate: 500,
      timeUnit: '1s',
      preAllocatedVUs: 500,
      maxVUs: 5000,
      stages: [
        { target: 2000,  duration: '20s' },
        { target: 4000,  duration: '20s' },
        { target: 6000,  duration: '20s' },
        { target: 8000,  duration: '20s' },
        { target: 10000, duration: '20s' },
        { target: 10000, duration: '20s' },
      ],
    },
  },
};

export default function () {
  const res = http.get(`${base}${endpoint}`);
  check(res, { 'status 200': (r) => r.status === 200 });
}
