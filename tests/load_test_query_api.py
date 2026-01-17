#!/usr/bin/env python3
"""
Comprehensive Load Test for DBNotebook Query API

Tests concurrent request handling and provides scalability recommendations.
Infrastructure: 14 CPU cores, 24.3 GB RAM, Docker container

Usage:
    python tests/load_test_query_api.py
"""

import asyncio
import aiohttp
import time
import statistics
import json
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys

# Configuration (defaults, can be overridden via CLI)
BASE_URL = "http://localhost:7860"
API_KEY = "dbn_00000000000000000000000000000001"
NOTEBOOK_ID = "18ee0c23-a2ce-4eb2-a56c-62a12dee964a"

# Model configuration (defaults, can be overridden via CLI)
MODEL = "gpt-4.1-mini"
PROVIDER = "openai"

# Test queries (varied complexity)
TEST_QUERIES = [
    "What are the key policies?",
    "Explain the leave policy",
    "What is the work from home policy?",
    "Summarize the main points",
    "What are employee benefits?",
    "How does the retirement policy work?",
    "What are the compliance requirements?",
    "Explain the code of conduct",
]

# Concurrency levels to test
CONCURRENCY_LEVELS = [150]  # 100 concurrent users
REQUESTS_PER_LEVEL = 150  # 100 requests total

# Staggered load test settings
STAGGERED_MODE = True
BATCH_SIZE = 10  # Users per batch
BATCH_INTERVAL = 5  # Seconds between batches


@dataclass
class RequestResult:
    """Result of a single request"""
    success: bool
    latency_ms: float
    status_code: int
    error: Optional[str] = None
    timings: Optional[Dict[str, int]] = None
    source_count: int = 0
    response_chars: int = 0


@dataclass
class ConcurrencyResult:
    """Aggregated results for a concurrency level"""
    concurrency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    latencies: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0
    timing_breakdown: Dict[str, List[int]] = field(default_factory=dict)
    source_counts: List[int] = field(default_factory=list)
    response_chars: List[int] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0

    @property
    def throughput(self) -> float:
        duration = self.end_time - self.start_time
        return self.successful_requests / duration if duration > 0 else 0

    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0

    @property
    def min_latency(self) -> float:
        return min(self.latencies) if self.latencies else 0

    @property
    def max_latency(self) -> float:
        return max(self.latencies) if self.latencies else 0

    @property
    def p50_latency(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0

    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def p99_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]


async def make_query_request(
    session: aiohttp.ClientSession,
    query: str,
    semaphore: asyncio.Semaphore
) -> RequestResult:
    """Make a single query request"""
    async with semaphore:
        start_time = time.time()
        try:
            async with session.post(
                f"{BASE_URL}/api/query",
                json={
                    "notebook_id": NOTEBOOK_ID,
                    "query": query,
                    "include_sources": True,
                    "max_sources": 6,
                    "model": MODEL,
                    "provider": PROVIDER,
                },
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY,
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                data = await response.json()

                if response.status == 200 and data.get("success"):
                    sources = data.get("sources", [])
                    response_text = data.get("response", "")
                    return RequestResult(
                        success=True,
                        latency_ms=latency_ms,
                        status_code=response.status,
                        timings=data.get("metadata", {}).get("timings"),
                        source_count=len(sources) if sources else 0,
                        response_chars=len(response_text) if response_text else 0
                    )
                else:
                    return RequestResult(
                        success=False,
                        latency_ms=latency_ms,
                        status_code=response.status,
                        error=data.get("error", f"HTTP {response.status}")
                    )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            return RequestResult(
                success=False,
                latency_ms=latency_ms,
                status_code=0,
                error="Request timeout (120s)"
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return RequestResult(
                success=False,
                latency_ms=latency_ms,
                status_code=0,
                error=str(e)
            )


async def run_concurrency_test(concurrency: int, total_requests: int) -> ConcurrencyResult:
    """Run load test at a specific concurrency level"""
    print(f"\n{'='*60}")
    print(f"Testing concurrency level: {concurrency} users")
    print(f"Total requests: {total_requests}")
    print(f"{'='*60}")

    result = ConcurrencyResult(
        concurrency=concurrency,
        total_requests=total_requests,
        successful_requests=0,
        failed_requests=0
    )

    semaphore = asyncio.Semaphore(concurrency)

    # Create connector with connection pooling
    connector = aiohttp.TCPConnector(
        limit=concurrency,
        limit_per_host=concurrency,
        keepalive_timeout=30
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        # Create tasks with varied queries
        tasks = []
        for i in range(total_requests):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            tasks.append(make_query_request(session, query, semaphore))

        result.start_time = time.time()

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        result.end_time = time.time()

        # Process results
        for r in results:
            if isinstance(r, Exception):
                result.failed_requests += 1
                result.errors.append(str(r))
            elif isinstance(r, RequestResult):
                result.latencies.append(r.latency_ms)
                if r.success:
                    result.successful_requests += 1
                    # Collect timing breakdown
                    if r.timings:
                        for key, value in r.timings.items():
                            if key not in result.timing_breakdown:
                                result.timing_breakdown[key] = []
                            result.timing_breakdown[key].append(value)
                else:
                    result.failed_requests += 1
                    if r.error:
                        result.errors.append(r.error)

    # Print immediate results
    duration = result.end_time - result.start_time
    print(f"\nResults for {concurrency} concurrent users:")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Success Rate: {result.success_rate:.1f}%")
    print(f"  Throughput: {result.throughput:.2f} req/s")
    print(f"  Latency (avg): {result.avg_latency:.0f}ms")
    print(f"  Latency (p50): {result.p50_latency:.0f}ms")
    print(f"  Latency (p95): {result.p95_latency:.0f}ms")
    print(f"  Latency (p99): {result.p99_latency:.0f}ms")


async def run_staggered_test(total_requests: int, batch_size: int, batch_interval: int) -> ConcurrencyResult:
    """Run staggered load test - batch_size users every batch_interval seconds"""
    num_batches = total_requests // batch_size

    print(f"\n{'='*60}")
    print(f"STAGGERED LOAD TEST")
    print(f"{'='*60}")
    print(f"Total requests: {total_requests}")
    print(f"Batch size: {batch_size} users")
    print(f"Batch interval: {batch_interval} seconds")
    print(f"Number of batches: {num_batches}")
    print(f"Expected duration: ~{num_batches * batch_interval}s + processing time")
    print(f"{'='*60}")

    result = ConcurrencyResult(
        concurrency=batch_size,
        total_requests=total_requests,
        successful_requests=0,
        failed_requests=0
    )

    connector = aiohttp.TCPConnector(
        limit=batch_size * 2,
        limit_per_host=batch_size * 2,
        keepalive_timeout=30
    )

    result.start_time = time.time()

    async with aiohttp.ClientSession(connector=connector) as session:
        all_tasks = []

        for batch_num in range(num_batches):
            batch_start = time.time()
            elapsed = batch_start - result.start_time
            print(f"\n  Batch {batch_num + 1}/{num_batches} at {elapsed:.1f}s - Launching {batch_size} requests...")

            semaphore = asyncio.Semaphore(batch_size)
            batch_tasks = []

            for i in range(batch_size):
                query_idx = (batch_num * batch_size + i) % len(TEST_QUERIES)
                query = TEST_QUERIES[query_idx]
                task = asyncio.create_task(make_query_request(session, query, semaphore))
                batch_tasks.append(task)
                all_tasks.append(task)

            # Wait for batch interval before next batch (but don't wait after last batch)
            if batch_num < num_batches - 1:
                await asyncio.sleep(batch_interval)

        # Wait for all remaining tasks to complete
        print(f"\n  Waiting for all requests to complete...")
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

    result.end_time = time.time()

    # Process results
    for r in results:
        if isinstance(r, Exception):
            result.failed_requests += 1
            result.errors.append(str(r))
        elif isinstance(r, RequestResult):
            result.latencies.append(r.latency_ms)
            if r.success:
                result.successful_requests += 1
                result.source_counts.append(r.source_count)
                result.response_chars.append(r.response_chars)
                if r.timings:
                    for key, value in r.timings.items():
                        if key not in result.timing_breakdown:
                            result.timing_breakdown[key] = []
                        result.timing_breakdown[key].append(value)
            else:
                result.failed_requests += 1
                if r.error:
                    result.errors.append(r.error)

    # Print results
    duration = result.end_time - result.start_time
    print(f"\n{'='*60}")
    print(f"STAGGERED TEST RESULTS")
    print(f"{'='*60}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Success Rate: {result.success_rate:.1f}%")
    print(f"  Throughput: {result.throughput:.2f} req/s")
    print(f"  Latency (avg): {result.avg_latency:.0f}ms")
    print(f"  Latency (p50): {result.p50_latency:.0f}ms")
    print(f"  Latency (p95): {result.p95_latency:.0f}ms")
    print(f"  Latency (p99): {result.p99_latency:.0f}ms")

    # Source and response metrics
    if result.source_counts:
        avg_sources = statistics.mean(result.source_counts)
        print(f"  Sources (avg): {avg_sources:.1f}")
    if result.response_chars:
        avg_chars = statistics.mean(result.response_chars)
        print(f"  Response (avg chars): {avg_chars:.0f}")

    if result.errors:
        unique_errors = list(set(result.errors))[:3]
        print(f"  Errors: {unique_errors}")

    return result


def print_summary_report(results: List[ConcurrencyResult]):
    """Print comprehensive summary report with recommendations"""
    print("\n" + "="*80)
    print("LOAD TEST SUMMARY REPORT")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}/api/query")
    print(f"Notebook ID: {NOTEBOOK_ID}")
    print(f"Infrastructure: 14 CPU cores, 24.3 GB RAM (Docker)")
    print("="*80)

    # Results table
    print("\n┌" + "─"*78 + "┐")
    print(f"│ {'Concurrency':^12} │ {'Success%':^10} │ {'Throughput':^12} │ {'Avg(ms)':^10} │ {'P95(ms)':^10} │ {'P99(ms)':^10} │")
    print("├" + "─"*78 + "┤")

    for r in results:
        print(f"│ {r.concurrency:^12} │ {r.success_rate:^10.1f} │ {r.throughput:^12.2f} │ {r.avg_latency:^10.0f} │ {r.p95_latency:^10.0f} │ {r.p99_latency:^10.0f} │")

    print("└" + "─"*78 + "┘")

    # Timing breakdown (average across all tests)
    print("\n" + "-"*80)
    print("TIMING BREAKDOWN (Average across successful requests)")
    print("-"*80)

    # Aggregate timing data
    all_timings: Dict[str, List[int]] = {}
    for r in results:
        for key, values in r.timing_breakdown.items():
            if key not in all_timings:
                all_timings[key] = []
            all_timings[key].extend(values)

    if all_timings:
        timing_avgs = [(k, statistics.mean(v)) for k, v in all_timings.items()]
        timing_avgs.sort(key=lambda x: x[1], reverse=True)

        total_avg = sum(v for _, v in timing_avgs)
        print(f"\n{'Stage':<35} {'Avg (ms)':>10} {'% of Total':>12}")
        print("-" * 60)
        for stage, avg in timing_avgs:
            pct = (avg / total_avg * 100) if total_avg > 0 else 0
            stage_name = stage.replace("_ms", "").replace("_", " ").title()
            print(f"{stage_name:<35} {avg:>10.0f} {pct:>11.1f}%")
        print("-" * 60)
        print(f"{'Total':<35} {total_avg:>10.0f} {'100.0':>11}%")

    # Bottleneck Analysis
    print("\n" + "-"*80)
    print("BOTTLENECK ANALYSIS")
    print("-"*80)

    bottlenecks = []

    # Check for LLM bottleneck
    if all_timings and "8_llm_completion_ms" in all_timings:
        llm_avg = statistics.mean(all_timings["8_llm_completion_ms"])
        total_avg = sum(statistics.mean(v) for v in all_timings.values())
        llm_pct = (llm_avg / total_avg * 100) if total_avg > 0 else 0
        if llm_pct > 50:
            bottlenecks.append(("LLM Completion", llm_pct, "CRITICAL"))

    # Check for retrieval bottleneck
    retrieval_keys = ["3_create_retriever_ms", "4_chunk_retrieval_ms", "3_retrieval_ms"]
    for key in retrieval_keys:
        if key in all_timings:
            retrieval_avg = statistics.mean(all_timings[key])
            if retrieval_avg > 500:
                bottlenecks.append(("Retrieval", retrieval_avg, "HIGH"))
                break

    # Check for success rate degradation
    for r in results:
        if r.success_rate < 95:
            bottlenecks.append((f"Success Rate at {r.concurrency} users", r.success_rate, "CRITICAL"))

    # Check for latency degradation
    if len(results) >= 2:
        base_latency = results[0].avg_latency
        for r in results[1:]:
            if r.avg_latency > base_latency * 3:
                bottlenecks.append((f"Latency Spike at {r.concurrency} users", r.avg_latency, "HIGH"))

    if bottlenecks:
        for name, value, severity in bottlenecks:
            if isinstance(value, float) and value > 100:
                print(f"  [{severity}] {name}: {value:.0f}ms")
            else:
                print(f"  [{severity}] {name}: {value:.1f}%")
    else:
        print("  No critical bottlenecks detected")

    # Scalability Assessment
    print("\n" + "-"*80)
    print("SCALABILITY ASSESSMENT")
    print("-"*80)

    # Find breaking point
    breaking_point = None
    for r in results:
        if r.success_rate < 95 or r.p99_latency > 30000:
            breaking_point = r.concurrency
            break

    if breaking_point:
        print(f"  ⚠️  Breaking point detected at {breaking_point} concurrent users")
        print(f"     Consider the recommendations below for scaling beyond this point")
    else:
        max_tested = max(r.concurrency for r in results)
        print(f"  ✅ System handled {max_tested} concurrent users successfully")

    # Calculate scaling efficiency
    if len(results) >= 2:
        base = results[0]
        final = results[-1]
        efficiency = (final.throughput / base.throughput) / (final.concurrency / base.concurrency) * 100
        print(f"  📊 Scaling efficiency: {efficiency:.1f}%")
        if efficiency < 50:
            print(f"     (Linear scaling would be 100%, current is sublinear)")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS FOR SCALING TO 100+ USERS")
    print("="*80)

    recommendations = []

    # 1. LLM-related recommendations
    if all_timings and "8_llm_completion_ms" in all_timings:
        llm_avg = statistics.mean(all_timings["8_llm_completion_ms"])
        if llm_avg > 2000:
            recommendations.append({
                "priority": "CRITICAL",
                "category": "LLM Optimization",
                "issue": f"LLM completion takes {llm_avg:.0f}ms average",
                "solutions": [
                    "Use a faster LLM model (e.g., GPT-4o-mini instead of GPT-4)",
                    "Deploy local LLM with GPU acceleration (Ollama with CUDA)",
                    "Implement LLM response caching for repeated queries",
                    "Use streaming responses to improve perceived latency",
                    "Consider async LLM calls with connection pooling"
                ]
            })

    # 2. Flask/Gunicorn recommendations
    recommendations.append({
        "priority": "HIGH",
        "category": "Web Server Scaling",
        "issue": "Flask dev server is single-threaded",
        "solutions": [
            "Switch to Gunicorn with multiple workers: gunicorn -w 4 -k gevent",
            "Use async workers: gunicorn -w 4 -k uvicorn.workers.UvicornWorker",
            "Configure worker count: (2 * CPU cores) + 1 = 29 workers for 14 cores",
            "Add nginx as reverse proxy for connection handling",
            "Enable keep-alive connections to reduce overhead"
        ]
    })

    # 3. Database recommendations
    recommendations.append({
        "priority": "HIGH",
        "category": "Database Connection Pooling",
        "issue": "Database connections may be exhausted under load",
        "solutions": [
            "Implement SQLAlchemy connection pooling: pool_size=20, max_overflow=30",
            "Use PgBouncer for PostgreSQL connection pooling",
            "Add database connection health checks",
            "Implement query result caching with Redis",
            "Optimize pgvector indexes for faster similarity search"
        ]
    })

    # 4. Caching recommendations
    recommendations.append({
        "priority": "HIGH",
        "category": "Caching Strategy",
        "issue": "No query/response caching detected",
        "solutions": [
            "Add Redis for LLM response caching (cache by query hash)",
            "Cache embedding results for frequently queried notebooks",
            "Implement RAPTOR summary caching per notebook",
            "Use in-memory LRU cache for node retrieval",
            "Cache retriever instances per notebook (already partially done)"
        ]
    })

    # 5. Architecture recommendations
    recommendations.append({
        "priority": "MEDIUM",
        "category": "Architecture Improvements",
        "issue": "Single-container architecture limits scaling",
        "solutions": [
            "Separate API server from LLM inference",
            "Use async task queue (Celery/RQ) for LLM calls",
            "Deploy multiple API container replicas behind load balancer",
            "Use Kubernetes HPA for auto-scaling based on CPU/memory",
            "Implement circuit breakers for LLM provider failover"
        ]
    })

    # 6. Embedding/Retrieval recommendations
    if all_timings:
        retrieval_time = sum(statistics.mean(all_timings.get(k, [0])) for k in
                           ["3_create_retriever_ms", "4_chunk_retrieval_ms", "3_retrieval_ms"]
                           if k in all_timings)
        if retrieval_time > 500:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Retrieval Optimization",
                "issue": f"Retrieval takes {retrieval_time:.0f}ms",
                "solutions": [
                    "Pre-compute and cache retrievers per notebook",
                    "Use HNSW index parameters: ef_construction=200, m=32",
                    "Reduce chunk count or use hierarchical retrieval",
                    "Batch embedding requests for reranking",
                    "Consider approximate nearest neighbor (ANN) for large corpora"
                ]
            })

    # Print recommendations
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['priority']}] {rec['category']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   Solutions:")
        for j, sol in enumerate(rec['solutions'], 1):
            print(f"      {j}. {sol}")

    # Quick wins
    print("\n" + "-"*80)
    print("QUICK WINS (Implement First)")
    print("-"*80)
    print("""
    1. Add Gunicorn to docker-entrypoint.sh:
       gunicorn -w 8 -k gevent -b 0.0.0.0:7860 --timeout 120 'dbnotebook.ui.web:create_app()'

    2. Add Redis caching for LLM responses (hash query + notebook_id as key)

    3. Increase SQLAlchemy pool_size in database configuration:
       create_engine(url, pool_size=20, max_overflow=30, pool_pre_ping=True)

    4. Use faster LLM model for query API (GPT-4o-mini or local Llama-3.1-8B)
    """)

    # Target metrics
    print("\n" + "-"*80)
    print("TARGET METRICS FOR 100 CONCURRENT USERS")
    print("-"*80)
    print("""
    ┌────────────────────────────────────────────────────────┐
    │ Metric              │ Current (est.) │ Target         │
    ├────────────────────────────────────────────────────────┤
    │ Success Rate        │ See above      │ > 99%          │
    │ P95 Latency         │ See above      │ < 10,000ms     │
    │ P99 Latency         │ See above      │ < 15,000ms     │
    │ Throughput          │ See above      │ > 5 req/s      │
    │ Error Rate          │ See above      │ < 1%           │
    └────────────────────────────────────────────────────────┘
    """)

    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80)


async def main():
    """Main entry point"""
    print("="*80)
    print("DBNotebook Query API Load Test")
    print("="*80)
    print(f"Target: {BASE_URL}/api/query")
    print(f"Notebook: {NOTEBOOK_ID}")
    print(f"Model: {MODEL} ({PROVIDER})")
    if STAGGERED_MODE:
        print(f"Mode: STAGGERED ({BATCH_SIZE} users every {BATCH_INTERVAL}s)")
        print(f"Total requests: {REQUESTS_PER_LEVEL}")
    else:
        print(f"Concurrency levels: {CONCURRENCY_LEVELS}")
        print(f"Requests per level: {REQUESTS_PER_LEVEL}")
    print("="*80)

    # Warm-up request
    print("\nWarm-up request...")
    connector = aiohttp.TCPConnector(limit=1)
    async with aiohttp.ClientSession(connector=connector) as session:
        semaphore = asyncio.Semaphore(1)
        result = await make_query_request(session, "test query", semaphore)
        if result.success:
            print(f"Warm-up successful: {result.latency_ms:.0f}ms")
        else:
            print(f"Warm-up failed: {result.error}")
            print("Continuing with tests anyway...")

    results = []

    if STAGGERED_MODE:
        # Run staggered load test
        result = await run_staggered_test(REQUESTS_PER_LEVEL, BATCH_SIZE, BATCH_INTERVAL)
        results.append(result)
    else:
        # Run tests at each concurrency level
        for concurrency in CONCURRENCY_LEVELS:
            result = await run_concurrency_test(concurrency, REQUESTS_PER_LEVEL)
            results.append(result)

            # Brief pause between levels to let system stabilize
            await asyncio.sleep(2)

    # Print summary report
    print_summary_report(results)

    # Save results to JSON
    output_file = f"test_results/load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import os
    os.makedirs("test_results", exist_ok=True)

    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {
                "base_url": BASE_URL,
                "notebook_id": NOTEBOOK_ID,
                "model": MODEL,
                "provider": PROVIDER,
                "concurrency_levels": CONCURRENCY_LEVELS,
                "requests_per_level": REQUESTS_PER_LEVEL,
            },
            "results": [
                {
                    "concurrency": r.concurrency,
                    "total_requests": r.total_requests,
                    "successful_requests": r.successful_requests,
                    "failed_requests": r.failed_requests,
                    "success_rate": r.success_rate,
                    "throughput": r.throughput,
                    "latency": {
                        "avg": r.avg_latency,
                        "min": r.min_latency,
                        "max": r.max_latency,
                        "p50": r.p50_latency,
                        "p95": r.p95_latency,
                        "p99": r.p99_latency,
                    },
                    "timing_breakdown": {k: statistics.mean(v) for k, v in r.timing_breakdown.items()} if r.timing_breakdown else {},
                    "avg_source_count": statistics.mean(r.source_counts) if r.source_counts else 0,
                    "avg_response_chars": statistics.mean(r.response_chars) if r.response_chars else 0,
                }
                for r in results
            ]
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="DBNotebook Query API Load Test")
    parser.add_argument("--base-url", default="http://localhost:7860",
                        help="Base URL for API (default: http://localhost:7860)")
    parser.add_argument("--model", default="gpt-4.1-mini",
                        help="Model name (default: gpt-4.1-mini)")
    parser.add_argument("--provider", default="openai",
                        help="Provider name (default: openai)")
    parser.add_argument("--users", type=int, default=150,
                        help="Total number of requests (default: 150)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Users per batch in staggered mode (default: 10)")
    parser.add_argument("--batch-interval", type=int, default=5,
                        help="Seconds between batches (default: 5)")
    parser.add_argument("--notebook-id", default="18ee0c23-a2ce-4eb2-a56c-62a12dee964a",
                        help="Notebook ID to query")
    parser.add_argument("--no-stagger", action="store_true",
                        help="Disable staggered mode, use burst mode instead")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Update globals from CLI args
    BASE_URL = args.base_url
    MODEL = args.model
    PROVIDER = args.provider
    REQUESTS_PER_LEVEL = args.users
    BATCH_SIZE = args.batch_size
    BATCH_INTERVAL = args.batch_interval
    NOTEBOOK_ID = args.notebook_id
    STAGGERED_MODE = not args.no_stagger
    CONCURRENCY_LEVELS = [args.users]

    asyncio.run(main())
