#!/usr/bin/env python3
"""
Load Test Script for Query API with Conversation Memory

Simulates 50 concurrent users making policy-related queries.
Shows actual responses and detailed timing statistics.

Usage:
    python scripts/load_test_query_api.py

Requirements:
    pip install aiohttp
"""

import asyncio
import aiohttp
import random
import time
import statistics
from dataclasses import dataclass
from typing import Optional
import json

# Configuration
BASE_URL = "http://localhost:7007"  # Adjust if needed
NOTEBOOK_ID = None  # Will be auto-detected
API_KEY = None  # Will be auto-fetched
CONCURRENT_USERS = 100
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"

# Policy-related queries for testing
POLICY_QUERIES = [
    # Travel Policy
    "What is the travel eligibility for L8?",
    "What are the travel benefits for Senior Manager?",
    "How many days of travel allowance do L7 employees get?",
    "What is the per diem rate for domestic travel?",
    "Can L6 employees travel business class?",
    "What is the hotel allowance for international travel?",
    "How do I submit travel expense claims?",
    "What is the advance travel booking policy?",

    # Leave Policy
    "How many vacation days do employees get?",
    "What is the sick leave policy?",
    "Can I carry forward unused leave?",
    "What is the maternity leave duration?",
    "How do I apply for paternity leave?",
    "What are the public holidays this year?",
    "Is work from home allowed?",
    "What is the bereavement leave policy?",

    # Compensation & Benefits
    "What are the compensation bands for L7?",
    "How is the annual bonus calculated?",
    "What health insurance options are available?",
    "Is there a retirement plan?",
    "What is the stock option policy?",
    "How often are salary reviews conducted?",
    "What benefits do Senior Managers receive?",
    "Is there a fitness center benefit?",

    # General HR Policies
    "What is the dress code policy?",
    "What is the work from home policy?",
    "How do I report workplace harassment?",
    "What is the code of conduct?",
    "What is the whistleblower policy?",
    "How do I request a transfer?",
    "What is the performance review process?",
    "What training programs are available?",

    # Follow-up style queries (conversational)
    "Tell me more about that",
    "What about for L6?",
    "How does this compare to L8?",
    "Can you explain further?",
    "What are the eligibility criteria?",
    "Who should I contact for more details?",
]


@dataclass
class QueryResult:
    """Result of a single query."""
    user_id: int
    query: str
    success: bool
    response_preview: str
    response_time_ms: float
    history_messages_used: int
    error: Optional[str] = None


async def get_api_key(session: aiohttp.ClientSession) -> str:
    """Fetch API key for the default user."""
    url = f"{BASE_URL}/api/user/api-key?user_id={DEFAULT_USER_ID}"
    async with session.get(url) as resp:
        data = await resp.json()
        if data.get("success"):
            return data["api_key"]
        raise Exception(f"Failed to get API key: {data.get('error')}")


async def get_notebook_id(session: aiohttp.ClientSession, api_key: str) -> str:
    """Get the first available notebook (Policies notebook)."""
    url = f"{BASE_URL}/api/query/notebooks"
    headers = {"X-API-Key": api_key}
    async with session.get(url, headers=headers) as resp:
        data = await resp.json()
        if data.get("success") and data.get("notebooks"):
            # Prefer "Policies" notebook if available
            for nb in data["notebooks"]:
                if "polic" in nb["name"].lower():
                    return nb["id"]
            # Otherwise return first notebook
            return data["notebooks"][0]["id"]
        raise Exception(f"No notebooks found: {data.get('error')}")


async def run_user_session(
    user_id: int,
    session: aiohttp.ClientSession,
    notebook_id: str,
    api_key: str,
    num_queries: int = 3
) -> list[QueryResult]:
    """
    Simulate a user session with multiple queries.
    Each user gets their own session_id for conversation memory.
    """
    results = []
    session_id = None  # Will be generated on first query

    # Select random queries for this user
    queries = random.sample(POLICY_QUERIES, min(num_queries, len(POLICY_QUERIES)))

    for query in queries:
        start_time = time.time()

        try:
            # Build request
            request_body = {
                "notebook_id": notebook_id,
                "query": query,
                "include_sources": True,
                "max_sources": 3,
                "max_history": 10,
            }

            # Include session_id for conversation continuity
            if session_id:
                request_body["session_id"] = session_id

            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }

            async with session.post(
                f"{BASE_URL}/api/query",
                json=request_body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                data = await resp.json()
                elapsed_ms = (time.time() - start_time) * 1000

                if data.get("success"):
                    # Store session_id for next query
                    session_id = data.get("session_id")

                    response_text = data.get("response", "")
                    preview = response_text[:150] + "..." if len(response_text) > 150 else response_text

                    history_used = data.get("metadata", {}).get("history_messages_used", 0)

                    results.append(QueryResult(
                        user_id=user_id,
                        query=query,
                        success=True,
                        response_preview=preview,
                        response_time_ms=elapsed_ms,
                        history_messages_used=history_used,
                    ))
                else:
                    results.append(QueryResult(
                        user_id=user_id,
                        query=query,
                        success=False,
                        response_preview="",
                        response_time_ms=elapsed_ms,
                        history_messages_used=0,
                        error=data.get("error", "Unknown error")
                    ))

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            results.append(QueryResult(
                user_id=user_id,
                query=query,
                success=False,
                response_preview="",
                response_time_ms=elapsed_ms,
                history_messages_used=0,
                error="Timeout"
            ))
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            results.append(QueryResult(
                user_id=user_id,
                query=query,
                success=False,
                response_preview="",
                response_time_ms=elapsed_ms,
                history_messages_used=0,
                error=str(e)
            ))

        # Small delay between queries from same user
        await asyncio.sleep(random.uniform(0.1, 0.5))

    return results


async def main():
    """Run load test with concurrent users."""
    print("=" * 80)
    print("Query API Load Test - 50 Concurrent Users")
    print("=" * 80)

    connector = aiohttp.TCPConnector(limit=100)  # Connection pool
    timeout = aiohttp.ClientTimeout(total=180)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Setup: Get API key and notebook
        print("\n[Setup] Fetching API key and notebook...")
        try:
            api_key = await get_api_key(session)
            print(f"  ✓ API Key: {api_key[:12]}...{api_key[-4:]}")

            notebook_id = await get_notebook_id(session, api_key)
            print(f"  ✓ Notebook ID: {notebook_id}")
        except Exception as e:
            print(f"  ✗ Setup failed: {e}")
            return

        # Run concurrent user sessions
        print(f"\n[Test] Starting {CONCURRENT_USERS} concurrent users (3 queries each)...")
        print("-" * 80)

        start_time = time.time()

        # Create tasks for all users
        tasks = [
            run_user_session(
                user_id=i + 1,
                session=session,
                notebook_id=notebook_id,
                api_key=api_key,
                num_queries=3
            )
            for i in range(CONCURRENT_USERS)
        ]

        # Run all user sessions concurrently
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Flatten results
        results: list[QueryResult] = []
        for user_results in all_results:
            if isinstance(user_results, list):
                results.extend(user_results)
            else:
                print(f"  ✗ User session error: {user_results}")

        # Print sample responses
        print("\n" + "=" * 80)
        print("SAMPLE RESPONSES (First 10)")
        print("=" * 80)

        for i, result in enumerate(results[:10]):
            status = "✓" if result.success else "✗"
            history_info = f"[history: {result.history_messages_used}]" if result.history_messages_used > 0 else ""
            print(f"\nUser {result.user_id} {status} ({result.response_time_ms:.0f}ms) {history_info}")
            print(f"  Q: {result.query}")
            if result.success:
                print(f"  A: {result.response_preview}")
            else:
                print(f"  Error: {result.error}")

        # Calculate statistics
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        response_times = [r.response_time_ms for r in successful]

        print(f"\nTotal Queries: {len(results)}")
        print(f"  ✓ Successful: {len(successful)} ({100*len(successful)/len(results):.1f}%)")
        print(f"  ✗ Failed: {len(failed)} ({100*len(failed)/len(results):.1f}%)")

        if response_times:
            print(f"\nResponse Times (successful queries):")
            print(f"  Min:     {min(response_times):,.0f} ms")
            print(f"  Max:     {max(response_times):,.0f} ms")
            print(f"  Mean:    {statistics.mean(response_times):,.0f} ms")
            print(f"  Median:  {statistics.median(response_times):,.0f} ms")
            print(f"  Std Dev: {statistics.stdev(response_times):,.0f} ms" if len(response_times) > 1 else "")

            # Percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.50)]
            p90 = sorted_times[int(len(sorted_times) * 0.90)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[min(int(len(sorted_times) * 0.99), len(sorted_times) - 1)]

            print(f"\nPercentiles:")
            print(f"  P50:  {p50:,.0f} ms")
            print(f"  P90:  {p90:,.0f} ms")
            print(f"  P95:  {p95:,.0f} ms")
            print(f"  P99:  {p99:,.0f} ms")

        # Memory usage stats
        with_memory = [r for r in successful if r.history_messages_used > 0]
        print(f"\nConversation Memory:")
        print(f"  Queries with history context: {len(with_memory)} ({100*len(with_memory)/len(successful):.1f}%)" if successful else "  N/A")

        print(f"\nThroughput:")
        print(f"  Total test time: {total_time:.2f} seconds")
        print(f"  Queries/second:  {len(results)/total_time:.2f}")

        # Error breakdown
        if failed:
            print(f"\nErrors:")
            error_counts = {}
            for r in failed:
                error_counts[r.error] = error_counts.get(r.error, 0) + 1
            for error, count in sorted(error_counts.items(), key=lambda x: -x[1]):
                print(f"  {count}x: {error[:60]}...")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
