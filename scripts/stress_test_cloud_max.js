/**
 * Push GCP/cloud VM to max throughput.
 * Use on the VM: k6 run -o experimental-prometheus-rw \
 *   --env K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write \
 *   scripts/stress_test_cloud_max.js
 */
import http from 'k6/http';
import { check } from 'k6';

const base = __ENV.BASE_URL || 'http://localhost';

export const options = {
  stages: [
    { duration: '15s', target: 30 },   // warm-up: fill cache
    { duration: '30s', target: 100 },  // ramp up
    { duration: '60s', target: 100 },  // hold at 100 VUs — sustained max
    { duration: '20s', target: 0 },    // ramp down
  ],
};

export default function () {
  const res = http.get(`${base}/products/85048`);
  check(res, {
    'is status 200': (r) => r.status === 200,
  });
}
