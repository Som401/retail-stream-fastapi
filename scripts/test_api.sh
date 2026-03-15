#!/usr/bin/env bash
# Smoke test for Retail Stream API (via Nginx LB on port 80)
set -e
BASE="${BASE_URL:-http://localhost:80}"
PASS=0
FAIL=0

check() {
  local label="$1" url="$2" expect="$3"
  CODE=$(curl -s -o /tmp/_body.json -w "%{http_code}" "$url")
  if [ "$CODE" = "$expect" ]; then
    echo "  PASS  $label ($CODE)"
    PASS=$((PASS+1))
  else
    echo "  FAIL  $label (expected $expect, got $CODE)"
    cat /tmp/_body.json 2>/dev/null; echo
    FAIL=$((FAIL+1))
  fi
}

echo "=== Retail Stream API — smoke test ==="
echo "Base: $BASE"
echo ""

echo "-- Health & Readiness --"
check "GET /health"  "$BASE/health"  200
check "GET /ready"   "$BASE/ready"   200

echo ""
echo "-- Products (cache-aside via LB) --"
check "GET /products/85048  (valid)"      "$BASE/products/85048"       200
check "GET /products/79323P (valid)"      "$BASE/products/79323P"      200
check "GET /products/DOESNOTEXIST (404)"  "$BASE/products/DOESNOTEXIST" 404

echo ""
echo "-- Top products --"
check "GET /products/top/5"  "$BASE/products/top/5"  200

echo ""
echo "-- POST /orders (Kafka async) --"
CODE=$(curl -s -o /tmp/_body.json -w "%{http_code}" -X POST "$BASE/orders" \
  -H "Content-Type: application/json" \
  -d '{"invoice":"TEST001","stock_code":"85048","quantity":2,"price":6.95,"country":"France"}')
if [ "$CODE" = "202" ]; then
  echo "  PASS  POST /orders (202 Accepted)"
  cat /tmp/_body.json; echo
  PASS=$((PASS+1))
else
  echo "  FAIL  POST /orders (expected 202, got $CODE)"
  cat /tmp/_body.json 2>/dev/null; echo
  FAIL=$((FAIL+1))
fi

echo ""
echo "-- Orders by invoice --"
check "GET /orders/invoice/489434  (valid)"   "$BASE/orders/invoice/489434"   200
check "GET /orders/invoice/C489449 (cancel)"  "$BASE/orders/invoice/C489449"  200
check "GET /orders/invoice/0000000 (404)"     "$BASE/orders/invoice/0000000"  404

echo ""
echo "-- Orders by customer --"
check "GET /orders/customer/13085"         "$BASE/orders/customer/13085"          200
check "GET /orders/customer/9999999 (404)" "$BASE/orders/customer/9999999"        404

echo ""
echo "-- Orders by country --"
check "GET /orders/country/France"             "$BASE/orders/country/France"              200
check "GET /orders/country/United%20Kingdom"   "$BASE/orders/country/United%20Kingdom"    200

echo ""
echo "-- Cache verification (second call faster) --"
echo "  First call:"
curl -s -o /dev/null -w "    %{time_total}s\n" "$BASE/products/85048"
echo "  Second call (cached):"
curl -s -o /dev/null -w "    %{time_total}s\n" "$BASE/products/85048"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && echo "All tests passed." || echo "Some tests failed!"
