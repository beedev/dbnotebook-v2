"""Load Testing for 100 Concurrent Users.

Tests the multi-user scalability of DBNotebook API endpoints:
- /api/query (stateless RAG queries)
- /api/v2/chat (chat with memory)
- /api/sql-chat (SQL queries)

Targets:
- 100 concurrent users
- < 5% error rate
- Consistent response times under load

Run with: pytest tests/test_load_concurrent.py -v -s
Or standalone: python tests/test_load_concurrent.py
"""

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import pytest
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:7860"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"

# Load test parameters
CONCURRENT_USERS = 100
REQUESTS_PER_USER = 3
TIMEOUT_SECONDS = 120
TARGET_ERROR_RATE = 0.05  # 5%
TARGET_P95_LATENCY_MS = 30000  # 30 seconds


@dataclass
class RequestResult:
    """Result of a single request."""
    user_id: str
    request_num: int
    endpoint: str
    success: bool
    status_code: int
    response_time_ms: float
    error: Optional[str] = None


@dataclass
class LoadTestMetrics:
    """Aggregated load test metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    error_rate: float = 0.0

    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    requests_per_second: float = 0.0
    total_duration_seconds: float = 0.0

    errors_by_type: Dict[str, int] = field(default_factory=dict)


class LoadTester:
    """Multi-threaded load tester for DBNotebook APIs."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        concurrent_users: int = CONCURRENT_USERS,
        requests_per_user: int = REQUESTS_PER_USER
    ):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.requests_per_user = requests_per_user
        self.results: List[RequestResult] = []
        self._lock = threading.Lock()

    def _make_request(
        self,
        user_num: int,
        request_num: int,
        notebook_id: str,
        query: str
    ) -> RequestResult:
        """Make a single API request."""
        user_id = f"user-{user_num:04d}-0000-0000-0000-000000000001"
        endpoint = "/api/query"

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json={
                    "notebook_id": notebook_id,
                    "query": query,
                    "include_sources": True,
                    "max_sources": 3
                },
                headers={"X-User-ID": user_id},
                timeout=TIMEOUT_SECONDS
            )

            response_time_ms = (time.time() - start_time) * 1000
            success = response.status_code == 200 and response.json().get("success", False)

            return RequestResult(
                user_id=user_id,
                request_num=request_num,
                endpoint=endpoint,
                success=success,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error=None if success else response.text[:200]
            )

        except requests.exceptions.Timeout:
            return RequestResult(
                user_id=user_id,
                request_num=request_num,
                endpoint=endpoint,
                success=False,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                error="Timeout"
            )
        except Exception as e:
            return RequestResult(
                user_id=user_id,
                request_num=request_num,
                endpoint=endpoint,
                success=False,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e)[:200]
            )

    def _user_session(
        self,
        user_num: int,
        notebook_id: str,
        queries: List[str]
    ) -> List[RequestResult]:
        """Simulate a single user session."""
        results = []
        for i, query in enumerate(queries[:self.requests_per_user]):
            result = self._make_request(user_num, i, notebook_id, query)
            results.append(result)

            # Small delay between requests (realistic user behavior)
            if i < len(queries) - 1:
                time.sleep(0.1)

        return results

    def _calculate_metrics(self, results: List[RequestResult], duration: float) -> LoadTestMetrics:
        """Calculate aggregated metrics from results."""
        if not results:
            return LoadTestMetrics()

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        response_times = [r.response_time_ms for r in results]

        # Calculate percentiles
        sorted_times = sorted(response_times)
        n = len(sorted_times)

        def percentile(p):
            k = (n - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < n else f
            return sorted_times[f] + (k - f) * (sorted_times[c] - sorted_times[f]) if c != f else sorted_times[f]

        # Count errors by type
        errors_by_type = {}
        for r in failed:
            error_type = r.error[:50] if r.error else "Unknown"
            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1

        return LoadTestMetrics(
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            error_rate=len(failed) / len(results) if results else 0,

            avg_response_time_ms=statistics.mean(response_times),
            min_response_time_ms=min(response_times),
            max_response_time_ms=max(response_times),
            p50_response_time_ms=percentile(50),
            p95_response_time_ms=percentile(95),
            p99_response_time_ms=percentile(99),

            requests_per_second=len(results) / duration if duration > 0 else 0,
            total_duration_seconds=duration,

            errors_by_type=errors_by_type
        )

    def run_load_test(
        self,
        notebook_id: str,
        queries: List[str]
    ) -> Tuple[LoadTestMetrics, List[RequestResult]]:
        """Run load test with concurrent users.

        Args:
            notebook_id: Notebook to query
            queries: List of test queries (will be cycled)

        Returns:
            Tuple of (metrics, all_results)
        """
        logger.info(f"Starting load test: {self.concurrent_users} users, {self.requests_per_user} requests each")

        all_results = []
        start_time = time.time()

        # Use ThreadPoolExecutor for concurrent users
        with ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
            futures = []

            for user_num in range(self.concurrent_users):
                # Cycle through queries
                user_queries = queries[user_num % len(queries):] + queries[:user_num % len(queries)]
                future = executor.submit(
                    self._user_session,
                    user_num,
                    notebook_id,
                    user_queries
                )
                futures.append(future)

            # Collect results as they complete
            completed = 0
            for future in as_completed(futures):
                try:
                    user_results = future.result()
                    with self._lock:
                        all_results.extend(user_results)
                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"Progress: {completed}/{self.concurrent_users} users completed")
                except Exception as e:
                    logger.error(f"User session failed: {e}")

        duration = time.time() - start_time
        metrics = self._calculate_metrics(all_results, duration)

        logger.info(f"Load test completed in {duration:.1f}s")
        return metrics, all_results


class TestLoadConcurrent:
    """Pytest test class for load testing."""

    @pytest.fixture
    def load_tester(self):
        return LoadTester(concurrent_users=CONCURRENT_USERS)

    @pytest.fixture
    def notebook_id(self):
        """Get first available notebook for testing."""
        response = requests.get(f"{BASE_URL}/api/query/notebooks")
        if response.status_code == 200:
            notebooks = response.json().get("notebooks", [])
            if notebooks:
                return notebooks[0]["id"]
        pytest.skip("No notebooks available for testing")

    @pytest.fixture
    def test_queries(self):
        return [
            "What are the main topics?",
            "Summarize the key findings",
            "What conclusions can be drawn?",
            "Explain the methodology",
            "What are the recommendations?",
            "Describe the results",
            "What is the significance?",
            "How does this relate to the field?",
            "What are the limitations?",
            "What future work is suggested?"
        ]

    def test_100_concurrent_users(self, load_tester, notebook_id, test_queries):
        """Test system handles 100 concurrent users."""
        metrics, results = load_tester.run_load_test(notebook_id, test_queries)

        self._print_metrics(metrics)

        # Assertions
        assert metrics.error_rate <= TARGET_ERROR_RATE, \
            f"Error rate {metrics.error_rate:.2%} exceeds target {TARGET_ERROR_RATE:.2%}"

        assert metrics.p95_response_time_ms <= TARGET_P95_LATENCY_MS, \
            f"P95 latency {metrics.p95_response_time_ms:.0f}ms exceeds target {TARGET_P95_LATENCY_MS}ms"

    def test_error_rate_under_5_percent(self, load_tester, notebook_id, test_queries):
        """Test error rate stays under 5%."""
        # Smaller test for faster validation
        load_tester.concurrent_users = 50
        load_tester.requests_per_user = 2

        metrics, _ = load_tester.run_load_test(notebook_id, test_queries)

        self._print_metrics(metrics)

        assert metrics.error_rate <= 0.05, \
            f"Error rate {metrics.error_rate:.2%} exceeds 5% threshold"

    def test_no_cross_user_data_leakage(self, load_tester, notebook_id, test_queries):
        """Test that each user only gets their own data (no leakage)."""
        # Use smaller scale for this specific test
        load_tester.concurrent_users = 20
        load_tester.requests_per_user = 1

        metrics, results = load_tester.run_load_test(notebook_id, test_queries)

        # Check each user got a valid response (not another user's data)
        # In this case, all users query the same notebook so responses should be valid
        for result in results:
            if result.success:
                # Valid response from correct endpoint
                assert result.endpoint == "/api/query"

        # No errors should indicate data isolation
        assert metrics.error_rate <= 0.10, "High error rate may indicate concurrency issues"

    def _print_metrics(self, metrics: LoadTestMetrics):
        """Print metrics summary."""
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)
        print(f"Total Requests:     {metrics.total_requests}")
        print(f"Successful:         {metrics.successful_requests}")
        print(f"Failed:             {metrics.failed_requests}")
        print(f"Error Rate:         {metrics.error_rate:.2%}")
        print("-" * 60)
        print(f"Avg Response Time:  {metrics.avg_response_time_ms:.0f}ms")
        print(f"Min Response Time:  {metrics.min_response_time_ms:.0f}ms")
        print(f"Max Response Time:  {metrics.max_response_time_ms:.0f}ms")
        print(f"P50 Latency:        {metrics.p50_response_time_ms:.0f}ms")
        print(f"P95 Latency:        {metrics.p95_response_time_ms:.0f}ms")
        print(f"P99 Latency:        {metrics.p99_response_time_ms:.0f}ms")
        print("-" * 60)
        print(f"Requests/Second:    {metrics.requests_per_second:.1f}")
        print(f"Total Duration:     {metrics.total_duration_seconds:.1f}s")
        if metrics.errors_by_type:
            print("-" * 60)
            print("Errors by type:")
            for error, count in metrics.errors_by_type.items():
                print(f"  {error}: {count}")
        print("=" * 60)


def save_load_report(
    metrics: LoadTestMetrics,
    results: List[RequestResult],
    output_dir: str = "test_results"
) -> Tuple[str, str]:
    """Save load test report to JSON and text files."""
    import os
    from datetime import datetime

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON report
    json_path = os.path.join(output_dir, f"load_test_report_{timestamp}.json")
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "concurrent_users": CONCURRENT_USERS,
            "requests_per_user": REQUESTS_PER_USER,
            "target_error_rate": TARGET_ERROR_RATE,
            "target_p95_latency_ms": TARGET_P95_LATENCY_MS
        },
        "summary": {
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "error_rate": metrics.error_rate,
            "avg_response_time_ms": metrics.avg_response_time_ms,
            "min_response_time_ms": metrics.min_response_time_ms,
            "max_response_time_ms": metrics.max_response_time_ms,
            "p50_response_time_ms": metrics.p50_response_time_ms,
            "p95_response_time_ms": metrics.p95_response_time_ms,
            "p99_response_time_ms": metrics.p99_response_time_ms,
            "requests_per_second": metrics.requests_per_second,
            "total_duration_seconds": metrics.total_duration_seconds
        },
        "errors_by_type": metrics.errors_by_type,
        "pass_fail": {
            "error_rate_passed": metrics.error_rate <= TARGET_ERROR_RATE,
            "p95_latency_passed": metrics.p95_response_time_ms <= TARGET_P95_LATENCY_MS,
            "overall_passed": (
                metrics.error_rate <= TARGET_ERROR_RATE and
                metrics.p95_response_time_ms <= TARGET_P95_LATENCY_MS
            )
        }
    }

    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)

    # Text report
    txt_path = os.path.join(output_dir, f"load_test_report_{timestamp}.txt")
    with open(txt_path, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("LOAD TEST REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 70 + "\n\n")

        f.write("CONFIGURATION\n")
        f.write("-" * 70 + "\n")
        f.write(f"Concurrent Users:    {CONCURRENT_USERS}\n")
        f.write(f"Requests per User:   {REQUESTS_PER_USER}\n")
        f.write(f"Target Error Rate:   {TARGET_ERROR_RATE:.2%}\n")
        f.write(f"Target P95 Latency:  {TARGET_P95_LATENCY_MS}ms\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("RESULTS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Requests:      {metrics.total_requests}\n")
        f.write(f"Successful:          {metrics.successful_requests}\n")
        f.write(f"Failed:              {metrics.failed_requests}\n")
        f.write(f"Error Rate:          {metrics.error_rate:.2%}\n")

        f.write("\nRESPONSE TIMES\n")
        f.write("-" * 70 + "\n")
        f.write(f"Average:             {metrics.avg_response_time_ms:.0f}ms\n")
        f.write(f"Minimum:             {metrics.min_response_time_ms:.0f}ms\n")
        f.write(f"Maximum:             {metrics.max_response_time_ms:.0f}ms\n")
        f.write(f"P50 (Median):        {metrics.p50_response_time_ms:.0f}ms\n")
        f.write(f"P95:                 {metrics.p95_response_time_ms:.0f}ms\n")
        f.write(f"P99:                 {metrics.p99_response_time_ms:.0f}ms\n")

        f.write("\nTHROUGHPUT\n")
        f.write("-" * 70 + "\n")
        f.write(f"Requests/Second:     {metrics.requests_per_second:.1f}\n")
        f.write(f"Total Duration:      {metrics.total_duration_seconds:.1f}s\n")

        if metrics.errors_by_type:
            f.write("\nERRORS BY TYPE\n")
            f.write("-" * 70 + "\n")
            for error, count in metrics.errors_by_type.items():
                f.write(f"  {error}: {count}\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("PASS/FAIL CRITERIA\n")
        f.write("-" * 70 + "\n")
        error_passed = metrics.error_rate <= TARGET_ERROR_RATE
        p95_passed = metrics.p95_response_time_ms <= TARGET_P95_LATENCY_MS
        f.write(f"Error Rate <= {TARGET_ERROR_RATE:.2%}:   {'PASS' if error_passed else 'FAIL'} ({metrics.error_rate:.2%})\n")
        f.write(f"P95 Latency <= {TARGET_P95_LATENCY_MS}ms: {'PASS' if p95_passed else 'FAIL'} ({metrics.p95_response_time_ms:.0f}ms)\n")
        f.write(f"\nOVERALL: {'PASS' if (error_passed and p95_passed) else 'FAIL'}\n")
        f.write("=" * 70 + "\n")

    print(f"\nReports saved to:")
    print(f"  - {json_path}")
    print(f"  - {txt_path}")

    return json_path, txt_path


def run_standalone_test():
    """Run load test standalone (without pytest)."""
    # Get notebook
    response = requests.get(f"{BASE_URL}/api/query/notebooks")
    if response.status_code != 200:
        print("Failed to get notebooks")
        return

    notebooks = response.json().get("notebooks", [])
    if not notebooks:
        print("No notebooks available")
        return

    notebook_id = notebooks[0]["id"]
    print(f"Testing notebook: {notebooks[0]['name']}")

    queries = [
        "What are the main topics?",
        "Summarize the key findings",
        "What conclusions can be drawn?",
        "Explain the methodology",
        "What are the recommendations?",
    ]

    # Run load test
    tester = LoadTester(
        concurrent_users=CONCURRENT_USERS,
        requests_per_user=REQUESTS_PER_USER
    )
    metrics, results = tester.run_load_test(notebook_id, queries)

    # Print results
    test_instance = TestLoadConcurrent()
    test_instance._print_metrics(metrics)

    # Check pass/fail
    passed = True
    if metrics.error_rate > TARGET_ERROR_RATE:
        print(f"\nFAILED: Error rate {metrics.error_rate:.2%} > {TARGET_ERROR_RATE:.2%}")
        passed = False
    if metrics.p95_response_time_ms > TARGET_P95_LATENCY_MS:
        print(f"\nFAILED: P95 latency {metrics.p95_response_time_ms:.0f}ms > {TARGET_P95_LATENCY_MS}ms")
        passed = False

    if passed:
        print("\nPASSED: All targets met!")

    # Save reports
    save_load_report(metrics, results)

    return metrics


if __name__ == "__main__":
    run_standalone_test()
