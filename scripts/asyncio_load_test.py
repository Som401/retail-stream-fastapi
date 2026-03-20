import asyncio
import math
import os
import time
from collections import Counter

import aiohttp

URL = os.getenv("URL", "http://34.95.108.94/products/85048")
TOTAL_REQUESTS = int(os.getenv("TOTAL_REQUESTS", "1000"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "1000"))
TIMEOUT_SECONDS = float(os.getenv("TIMEOUT_SECONDS", "10"))
HEADERS = {}
PARAMS = {}


def percentile(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    k = math.ceil((p / 100) * len(values)) - 1
    k = max(0, min(k, len(values) - 1))
    return values[k]


async def make_request(session, request_id, semaphore):
    async with semaphore:
        start = time.perf_counter()
        try:
            async with session.get(URL, headers=HEADERS, params=PARAMS) as response:
                await response.read()
                latency_ms = (time.perf_counter() - start) * 1000
                return {
                    "id": request_id,
                    "ok": 200 <= response.status < 300,
                    "status": response.status,
                    "latency_ms": latency_ms,
                    "error": None,
                }
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return {
                "id": request_id,
                "ok": False,
                "status": None,
                "latency_ms": latency_ms,
                "error": str(e),
            }


async def main():
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, limit_per_host=CONCURRENCY)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    start_total = time.perf_counter()
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [make_request(session, i + 1, semaphore) for i in range(TOTAL_REQUESTS)]
        results = await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start_total

    success_count = sum(1 for r in results if r["ok"])
    fail_count = TOTAL_REQUESTS - success_count
    status_counter = Counter(r["status"] for r in results if r["status"] is not None)
    error_counter = Counter(r["error"] for r in results if r["error"] is not None)

    latencies = [r["latency_ms"] for r in results]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    min_latency = min(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)

    rps = TOTAL_REQUESTS / total_time if total_time > 0 else 0.0

    print("=" * 60)
    print("TEST RESULT")
    print("=" * 60)
    print(f"URL: {URL}")
    print(f"TOTAL REQUESTS: {TOTAL_REQUESTS}")
    print(f"CONCURRENCY: {CONCURRENCY}")
    print(f"SUCCESS: {success_count}")
    print(f"FAIL: {fail_count}")
    print(f"TOTAL TIME: {total_time:.3f}s")
    print(f"RPS: {rps:.2f}")
    print(f"AVG LATENCY: {avg_latency:.2f} ms")
    print(f"MIN LATENCY: {min_latency:.2f} ms")
    print(f"MAX LATENCY: {max_latency:.2f} ms")
    print(f"P50: {p50:.2f} ms")
    print(f"P95: {p95:.2f} ms")
    print(f"P99: {p99:.2f} ms")
    print("\nStatus codes:")
    for status, count in sorted(status_counter.items()):
        print(f"  {status}: {count}")
    print("\nErrors:")
    if error_counter:
        for err, count in error_counter.items():
            print(f"  {err}: {count}")
    else:
        print("  None")


if __name__ == "__main__":
    asyncio.run(main())
