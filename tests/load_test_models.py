#!/usr/bin/env python3
"""
Load Test for DBNotebook Query API - Multi-Model Comparison with Scalability Analysis

Features:
- Multi-model comparison (gpt-4.1-mini, groq)
- Concurrency scaling analysis (tests multiple user counts)
- Detailed performance recommendations
- Bottleneck identification logic
- Per-concurrency analysis
- Response validation (character counts)

Usage:
    python tests/load_test_models.py
"""

import asyncio
import aiohttp
import time
import statistics
import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:7860"
API_KEY = "dbn_00000000000000000000000000000001"
NOTEBOOK_ID = "18ee0c23-a2ce-4eb2-a56c-62a12dee964a"

# Models to test
MODELS = [
    {"name": "gpt-4.1-mini", "provider": "openai"},
    # {"name": "meta-llama/llama-4-maverick-17b-128e-instruct", "provider": "groq"},
]

# Test parameters - Concurrency scaling
CONCURRENCY_LEVELS = [50, 75, 100, 125, 150]  # Test up to 150 concurrent users
REQUESTS_PER_LEVEL = 30  # Requests per concurrency level
TIMEOUT_SECONDS = 180

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
    "What is the whistle blower policy?",
    "How do I report violations?",
]


@dataclass
class RequestResult:
    """Result of a single request"""
    success: bool
    latency_ms: float
    status_code: int
    error: Optional[str] = None
    timings: Optional[Dict[str, int]] = None
    response_chars: int = 0


@dataclass
class ConcurrencyResult:
    """Aggregated results for a concurrency level"""
    concurrency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    latencies: List[float] = field(default_factory=list)
    response_chars: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0
    timing_breakdown: Dict[str, List[int]] = field(default_factory=dict)

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

    @property
    def avg_response_chars(self) -> float:
        return statistics.mean(self.response_chars) if self.response_chars else 0

    @property
    def min_response_chars(self) -> int:
        return min(self.response_chars) if self.response_chars else 0

    @property
    def max_response_chars(self) -> int:
        return max(self.response_chars) if self.response_chars else 0


@dataclass
class ModelResult:
    """Aggregated results for a model across all concurrency levels"""
    model: str
    provider: str
    concurrency_results: List[ConcurrencyResult] = field(default_factory=list)

    @property
    def total_requests(self) -> int:
        return sum(r.total_requests for r in self.concurrency_results)

    @property
    def successful_requests(self) -> int:
        return sum(r.successful_requests for r in self.concurrency_results)

    @property
    def overall_success_rate(self) -> float:
        total = self.total_requests
        return (self.successful_requests / total * 100) if total > 0 else 0

    @property
    def all_latencies(self) -> List[float]:
        return [l for r in self.concurrency_results for l in r.latencies]

    @property
    def avg_latency(self) -> float:
        latencies = self.all_latencies
        return statistics.mean(latencies) if latencies else 0

    @property
    def all_timing_breakdown(self) -> Dict[str, List[int]]:
        """Aggregate timing breakdown across all concurrency levels"""
        all_timings: Dict[str, List[int]] = {}
        for r in self.concurrency_results:
            for key, values in r.timing_breakdown.items():
                if key not in all_timings:
                    all_timings[key] = []
                all_timings[key].extend(values)
        return all_timings

    @property
    def avg_response_chars(self) -> float:
        all_chars = [c for r in self.concurrency_results for c in r.response_chars]
        return statistics.mean(all_chars) if all_chars else 0


async def make_query_request(
    session: aiohttp.ClientSession,
    query: str,
    model: str,
    provider: str,
    semaphore: asyncio.Semaphore,
    request_num: int,
    concurrency: int
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
                    "model": model,
                    "provider": provider,
                },
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY,
                },
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                data = await response.json()

                if response.status == 200 and data.get("success"):
                    response_text = data.get("response", "")
                    response_chars = len(response_text)
                    print(f"  [C{concurrency:02d}][{request_num:02d}] {model[:25]:25s} - {latency_ms:,.0f}ms OK ({response_chars:,} chars)")
                    return RequestResult(
                        success=True,
                        latency_ms=latency_ms,
                        status_code=response.status,
                        timings=data.get("metadata", {}).get("timings"),
                        response_chars=response_chars
                    )
                else:
                    error_msg = data.get("error", f"HTTP {response.status}")
                    print(f"  [C{concurrency:02d}][{request_num:02d}] {model[:25]:25s} - FAILED: {error_msg}")
                    return RequestResult(
                        success=False,
                        latency_ms=latency_ms,
                        status_code=response.status,
                        error=error_msg
                    )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            print(f"  [C{concurrency:02d}][{request_num:02d}] {model[:25]:25s} - TIMEOUT ({TIMEOUT_SECONDS}s)")
            return RequestResult(
                success=False,
                latency_ms=latency_ms,
                status_code=0,
                error=f"Request timeout ({TIMEOUT_SECONDS}s)"
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            print(f"  [C{concurrency:02d}][{request_num:02d}] {model[:25]:25s} - ERROR: {e}")
            return RequestResult(
                success=False,
                latency_ms=latency_ms,
                status_code=0,
                error=str(e)
            )


async def run_concurrency_test(
    model: str,
    provider: str,
    concurrency: int,
    total_requests: int
) -> ConcurrencyResult:
    """Run load test at a specific concurrency level for a model"""
    print(f"\n  --- Concurrency: {concurrency} users, {total_requests} requests ---")

    result = ConcurrencyResult(
        concurrency=concurrency,
        total_requests=total_requests,
        successful_requests=0,
        failed_requests=0
    )

    semaphore = asyncio.Semaphore(concurrency)

    connector = aiohttp.TCPConnector(
        limit=concurrency,
        limit_per_host=concurrency,
        keepalive_timeout=30
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(total_requests):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            tasks.append(make_query_request(
                session, query, model, provider, semaphore, i + 1, concurrency
            ))

        result.start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        result.end_time = time.time()

        for r in results:
            if isinstance(r, Exception):
                result.failed_requests += 1
                result.errors.append(str(r))
            elif isinstance(r, RequestResult):
                result.latencies.append(r.latency_ms)
                if r.success:
                    result.successful_requests += 1
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

    duration = result.end_time - result.start_time
    print(f"  Results: {result.success_rate:.1f}% success, {result.throughput:.2f} req/s, "
          f"Avg: {result.avg_latency:,.0f}ms, P95: {result.p95_latency:,.0f}ms, "
          f"Chars: {result.avg_response_chars:,.0f} avg")

    return result


async def run_model_test(model_config: Dict) -> ModelResult:
    """Run load test for a specific model across all concurrency levels"""
    model = model_config["name"]
    provider = model_config["provider"]

    print(f"\n{'='*80}")
    print(f"Testing: {model} ({provider})")
    print(f"Concurrency levels: {CONCURRENCY_LEVELS}")
    print(f"Requests per level: {REQUESTS_PER_LEVEL}")
    print(f"{'='*80}")

    result = ModelResult(model=model, provider=provider)

    for concurrency in CONCURRENCY_LEVELS:
        concurrency_result = await run_concurrency_test(
            model, provider, concurrency, REQUESTS_PER_LEVEL
        )
        result.concurrency_results.append(concurrency_result)

        # Brief pause between concurrency levels
        if concurrency != CONCURRENCY_LEVELS[-1]:
            print("  Stabilizing (2s)...")
            await asyncio.sleep(2)

    return result


def analyze_bottlenecks(model_result: ModelResult) -> List[tuple]:
    """Identify bottlenecks for a model"""
    bottlenecks = []
    all_timings = model_result.all_timing_breakdown

    # Check for LLM bottleneck
    if "8_llm_completion_ms" in all_timings:
        llm_avg = statistics.mean(all_timings["8_llm_completion_ms"])
        total_avg = sum(statistics.mean(v) for v in all_timings.values())
        llm_pct = (llm_avg / total_avg * 100) if total_avg > 0 else 0
        if llm_pct > 50:
            bottlenecks.append(("LLM Completion", f"{llm_pct:.1f}% of total time", "CRITICAL"))

    # Check for retrieval bottleneck
    retrieval_keys = ["3_create_retriever_ms", "4_chunk_retrieval_ms", "3_retrieval_ms"]
    for key in retrieval_keys:
        if key in all_timings:
            retrieval_avg = statistics.mean(all_timings[key])
            if retrieval_avg > 500:
                bottlenecks.append(("Retrieval", f"{retrieval_avg:.0f}ms avg", "HIGH"))
                break

    # Check for success rate degradation at higher concurrency
    for r in model_result.concurrency_results:
        if r.success_rate < 95:
            bottlenecks.append((f"Success Rate at {r.concurrency} users", f"{r.success_rate:.1f}%", "CRITICAL"))

    # Check for latency degradation
    if len(model_result.concurrency_results) >= 2:
        base_latency = model_result.concurrency_results[0].avg_latency
        for r in model_result.concurrency_results[1:]:
            if r.avg_latency > base_latency * 3:
                bottlenecks.append((f"Latency Spike at {r.concurrency} users", f"{r.avg_latency:.0f}ms", "HIGH"))

    return bottlenecks


def print_comparison_report(results: List[ModelResult]):
    """Print comprehensive comparison report with recommendations"""
    print("\n" + "="*90)
    print("LOAD TEST COMPARISON REPORT - MULTI-MODEL SCALABILITY ANALYSIS")
    print("="*90)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}/api/query")
    print(f"Notebook ID: {NOTEBOOK_ID}")
    print(f"Concurrency Levels: {CONCURRENCY_LEVELS}")
    print(f"Requests per Level: {REQUESTS_PER_LEVEL}")
    print(f"Total Requests per Model: {REQUESTS_PER_LEVEL * len(CONCURRENCY_LEVELS)}")
    print("="*90)

    # Per-model scalability table
    for model_result in results:
        print(f"\n{'─'*90}")
        print(f"MODEL: {model_result.model} ({model_result.provider})")
        print(f"{'─'*90}")
        print(f"{'Concurrency':<12} {'Success%':>10} {'Throughput':>12} {'Avg(ms)':>10} {'P95(ms)':>10} {'P99(ms)':>10} {'Avg Chars':>12}")
        print(f"{'─'*90}")

        for r in model_result.concurrency_results:
            print(f"{r.concurrency:<12} {r.success_rate:>9.1f}% {r.throughput:>10.2f}/s {r.avg_latency:>10,.0f} {r.p95_latency:>10,.0f} {r.p99_latency:>10,.0f} {r.avg_response_chars:>12,.0f}")

        print(f"{'─'*90}")
        print(f"{'TOTAL':<12} {model_result.overall_success_rate:>9.1f}% {'-':>12} {model_result.avg_latency:>10,.0f} {'-':>10} {'-':>10} {model_result.avg_response_chars:>12,.0f}")

    # Cross-model comparison at highest concurrency
    print("\n" + "="*90)
    print(f"CROSS-MODEL COMPARISON AT {CONCURRENCY_LEVELS[-1]} CONCURRENT USERS")
    print("="*90)
    print(f"{'Model':<45} {'Success%':>10} {'Throughput':>12} {'Avg(ms)':>10} {'P95(ms)':>10}")
    print(f"{'─'*90}")

    for model_result in results:
        highest_concurrency = model_result.concurrency_results[-1]
        model_short = model_result.model[:42] + "..." if len(model_result.model) > 45 else model_result.model
        print(f"{model_short:<45} {highest_concurrency.success_rate:>9.1f}% {highest_concurrency.throughput:>10.2f}/s {highest_concurrency.avg_latency:>10,.0f} {highest_concurrency.p95_latency:>10,.0f}")

    # Timing breakdown comparison
    print("\n" + "="*90)
    print("TIMING BREAKDOWN (LLM Completion Time)")
    print("="*90)

    for model_result in results:
        all_timings = model_result.all_timing_breakdown
        if "8_llm_completion_ms" in all_timings:
            llm_avg = statistics.mean(all_timings["8_llm_completion_ms"])
            model_short = model_result.model[:50] if len(model_result.model) <= 50 else model_result.model[:47] + "..."
            print(f"  {model_short:<50}: {llm_avg:>10,.0f}ms avg")

    # Bottleneck Analysis
    print("\n" + "="*90)
    print("BOTTLENECK ANALYSIS")
    print("="*90)

    for model_result in results:
        print(f"\n  {model_result.model}:")
        bottlenecks = analyze_bottlenecks(model_result)
        if bottlenecks:
            for name, value, severity in bottlenecks:
                print(f"    [{severity}] {name}: {value}")
        else:
            print("    No critical bottlenecks detected")

    # Scalability Assessment
    print("\n" + "="*90)
    print("SCALABILITY ASSESSMENT")
    print("="*90)

    for model_result in results:
        print(f"\n  {model_result.model}:")

        # Find breaking point
        breaking_point = None
        for r in model_result.concurrency_results:
            if r.success_rate < 95 or r.p99_latency > 60000:
                breaking_point = r.concurrency
                break

        if breaking_point:
            print(f"    ⚠️  Breaking point detected at {breaking_point} concurrent users")
        else:
            max_tested = max(r.concurrency for r in model_result.concurrency_results)
            print(f"    ✅ System handled {max_tested} concurrent users successfully")

        # Calculate scaling efficiency
        if len(model_result.concurrency_results) >= 2:
            base = model_result.concurrency_results[0]
            final = model_result.concurrency_results[-1]
            if base.throughput > 0:
                efficiency = (final.throughput / base.throughput) / (final.concurrency / base.concurrency) * 100
                print(f"    📊 Scaling efficiency: {efficiency:.1f}%")
                if efficiency < 50:
                    print(f"       (Linear scaling would be 100%, current is sublinear)")

    # Winner determination
    print("\n" + "="*90)
    print("ANALYSIS SUMMARY")
    print("="*90)

    successful_results = [r for r in results if r.overall_success_rate > 0]
    if successful_results:
        # Best at highest concurrency
        highest_level_results = [(r, r.concurrency_results[-1]) for r in successful_results]

        fastest = min(highest_level_results, key=lambda x: x[1].avg_latency)
        highest_throughput = max(highest_level_results, key=lambda x: x[1].throughput)
        most_reliable = max(highest_level_results, key=lambda x: x[1].success_rate)

        print(f"\n  At {CONCURRENCY_LEVELS[-1]} concurrent users:")
        print(f"    Fastest (lowest avg latency): {fastest[0].model} ({fastest[1].avg_latency:,.0f}ms)")
        print(f"    Highest Throughput: {highest_throughput[0].model} ({highest_throughput[1].throughput:.2f} req/s)")
        print(f"    Most Reliable: {most_reliable[0].model} ({most_reliable[1].success_rate:.1f}%)")

    # Recommendations
    print("\n" + "="*90)
    print("RECOMMENDATIONS FOR SCALING")
    print("="*90)

    recommendations = [
        {
            "priority": "CRITICAL",
            "category": "LLM Optimization",
            "solutions": [
                "Use faster LLM model (GPT-4o-mini is 2x faster than GPT-4)",
                "Deploy local LLM with GPU acceleration (Ollama with CUDA)",
                "Implement LLM response caching for repeated queries",
                "Use streaming responses to improve perceived latency"
            ]
        },
        {
            "priority": "HIGH",
            "category": "Web Server Scaling",
            "solutions": [
                "Use Gunicorn with multiple workers: gunicorn -w 8 -k gevent",
                "Configure worker count: (2 * CPU cores) + 1",
                "Add nginx as reverse proxy for connection handling"
            ]
        },
        {
            "priority": "HIGH",
            "category": "Database Connection Pooling",
            "solutions": [
                "Implement SQLAlchemy connection pooling: pool_size=20, max_overflow=30",
                "Use PgBouncer for PostgreSQL connection pooling",
                "Optimize pgvector indexes for faster similarity search"
            ]
        },
        {
            "priority": "HIGH",
            "category": "Caching Strategy",
            "solutions": [
                "Add Redis for LLM response caching (cache by query hash)",
                "Cache embedding results for frequently queried notebooks",
                "Implement RAPTOR summary caching per notebook"
            ]
        },
        {
            "priority": "MEDIUM",
            "category": "Architecture Improvements",
            "solutions": [
                "Separate API server from LLM inference",
                "Use async task queue (Celery/RQ) for LLM calls",
                "Deploy multiple API container replicas behind load balancer"
            ]
        }
    ]

    for i, rec in enumerate(recommendations, 1):
        print(f"\n  {i}. [{rec['priority']}] {rec['category']}")
        for j, sol in enumerate(rec['solutions'], 1):
            print(f"      {j}. {sol}")

    # Target metrics
    print("\n" + "="*90)
    print("TARGET METRICS FOR 100 CONCURRENT USERS")
    print("="*90)
    print("""
    ┌────────────────────────────────────────────────────────────┐
    │ Metric              │ Target                               │
    ├────────────────────────────────────────────────────────────┤
    │ Success Rate        │ > 99%                                │
    │ P95 Latency         │ < 15,000ms                           │
    │ P99 Latency         │ < 30,000ms                           │
    │ Throughput          │ > 5 req/s                            │
    │ Error Rate          │ < 1%                                 │
    └────────────────────────────────────────────────────────────┘
    """)

    print("\n" + "="*90)
    print("END OF REPORT")
    print("="*90)


async def main():
    """Main entry point"""
    print("="*90)
    print("DBNotebook Query API - Multi-Model Load Test with Scalability Analysis")
    print("="*90)
    print(f"Target: {BASE_URL}/api/query")
    print(f"Models: {[m['name'] for m in MODELS]}")
    print(f"Concurrency levels: {CONCURRENCY_LEVELS}")
    print(f"Requests per level: {REQUESTS_PER_LEVEL}")
    print(f"Total requests per model: {REQUESTS_PER_LEVEL * len(CONCURRENCY_LEVELS)}")
    print("="*90)

    # Warm-up
    print("\nWarm-up request...")
    connector = aiohttp.TCPConnector(limit=1)
    async with aiohttp.ClientSession(connector=connector) as session:
        semaphore = asyncio.Semaphore(1)
        result = await make_query_request(
            session, "test query", MODELS[0]["name"], MODELS[0]["provider"], semaphore, 0, 1
        )
        if result.success:
            print(f"Warm-up successful: {result.latency_ms:,.0f}ms")
        else:
            print(f"Warm-up failed: {result.error}")
            print("Continuing anyway...")

    # Run tests for each model
    results = []
    for model_config in MODELS:
        result = await run_model_test(model_config)
        results.append(result)
        print("\nCooling down between models (5s)...")
        await asyncio.sleep(5)

    # Print comparison report
    print_comparison_report(results)

    # Save results
    os.makedirs("test_results", exist_ok=True)
    output_file = f"test_results/load_test_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {
                "base_url": BASE_URL,
                "notebook_id": NOTEBOOK_ID,
                "concurrency_levels": CONCURRENCY_LEVELS,
                "requests_per_level": REQUESTS_PER_LEVEL,
                "total_requests_per_model": REQUESTS_PER_LEVEL * len(CONCURRENCY_LEVELS),
                "models": MODELS,
            },
            "results": [
                {
                    "model": mr.model,
                    "provider": mr.provider,
                    "total_requests": mr.total_requests,
                    "successful_requests": mr.successful_requests,
                    "overall_success_rate": mr.overall_success_rate,
                    "avg_latency": mr.avg_latency,
                    "avg_response_chars": mr.avg_response_chars,
                    "concurrency_results": [
                        {
                            "concurrency": cr.concurrency,
                            "total_requests": cr.total_requests,
                            "successful_requests": cr.successful_requests,
                            "failed_requests": cr.failed_requests,
                            "success_rate": cr.success_rate,
                            "throughput": cr.throughput,
                            "latency": {
                                "avg": cr.avg_latency,
                                "min": cr.min_latency,
                                "max": cr.max_latency,
                                "p50": cr.p50_latency,
                                "p95": cr.p95_latency,
                                "p99": cr.p99_latency,
                            },
                            "response_chars": {
                                "avg": cr.avg_response_chars,
                                "min": cr.min_response_chars,
                                "max": cr.max_response_chars,
                            },
                            "timing_breakdown": {k: statistics.mean(v) for k, v in cr.timing_breakdown.items()} if cr.timing_breakdown else {},
                        }
                        for cr in mr.concurrency_results
                    ],
                    "timing_breakdown": {k: statistics.mean(v) for k, v in mr.all_timing_breakdown.items()} if mr.all_timing_breakdown else {},
                }
                for mr in results
            ]
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
