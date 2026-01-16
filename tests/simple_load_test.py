#!/usr/bin/env python3
"""Simple load test - 100 concurrent users, 1 request each."""

import asyncio
import aiohttp
import time
import sys

API_URL = "http://localhost:7860/api/query"
API_KEY = "dbnotebook-secure-api-key-2026"
NOTEBOOK_ID = "18ee0c23-a2ce-4eb2-a56c-62a12dee964a"

QUERIES = [
    "What is the work from home policy?",
    "Explain the code of conduct",
    "What are the travel policies?",
    "Tell me about retirement benefits",
    "What is the dress code policy?",
]

async def make_request(session, user_id):
    """Make a single request."""
    query = QUERIES[user_id % len(QUERIES)]
    payload = {
        "notebook_id": NOTEBOOK_ID,
        "query": query
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    start = time.time()
    try:
        async with session.post(API_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=180)) as resp:
            elapsed = time.time() - start
            if resp.status == 200:
                data = await resp.json()
                return {"user": user_id, "status": "success", "time": elapsed, "response_len": len(str(data.get("response", "")))}
            else:
                return {"user": user_id, "status": "error", "time": elapsed, "code": resp.status}
    except asyncio.TimeoutError:
        return {"user": user_id, "status": "timeout", "time": time.time() - start}
    except Exception as e:
        return {"user": user_id, "status": "exception", "time": time.time() - start, "error": str(e)}

async def run_load_test(num_users=100):
    """Run load test with specified number of concurrent users."""
    print(f"\n{'='*60}")
    print(f"LOAD TEST: {num_users} concurrent users, 1 request each")
    print(f"{'='*60}\n")

    connector = aiohttp.TCPConnector(limit=num_users, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        start = time.time()
        tasks = [make_request(session, i) for i in range(num_users)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start

    # Analyze results
    successes = [r for r in results if r["status"] == "success"]
    failures = [r for r in results if r["status"] != "success"]

    print(f"Results Summary:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Successes: {len(successes)}/{num_users} ({100*len(successes)/num_users:.1f}%)")
    print(f"  Failures: {len(failures)}")

    if successes:
        times = [r["time"] for r in successes]
        print(f"\nLatency (successful requests):")
        print(f"  Min: {min(times):.2f}s")
        print(f"  Max: {max(times):.2f}s")
        print(f"  Avg: {sum(times)/len(times):.2f}s")
        sorted_times = sorted(times)
        p95_idx = int(len(sorted_times) * 0.95)
        print(f"  P95: {sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]:.2f}s")

    if failures:
        print(f"\nFailure breakdown:")
        by_status = {}
        for f in failures:
            status = f["status"]
            by_status[status] = by_status.get(status, 0) + 1
        for status, count in by_status.items():
            print(f"  {status}: {count}")

    print(f"\nThroughput: {len(successes)/total_time:.2f} req/s")

    return results

if __name__ == "__main__":
    num_users = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(run_load_test(num_users))
