import http from 'k6/http';
import { check } from 'k6';

// Laptop + Docker: keep VUs modest so all 3 app replicas stay healthy (~99% pass).
// Default 30 VUs; use STRESS=1 on EC2 for 200 VUs.
const stress = __ENV.STRESS === '1';
const targetVUs = stress ? 200 : 30;

export const options = {
  stages: [
    { duration: '5s', target: 10 },
    { duration: '20s', target: targetVUs },
  ],
};

export default function () {
  const base = __ENV.BASE_URL || 'http://localhost';
  const res = http.get(`${base}/products/85048`);
  check(res, {
    'is status 200': (r) => r.status === 200,
  });
}
