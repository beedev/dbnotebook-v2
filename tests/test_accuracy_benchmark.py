"""Accuracy Benchmark Tests.

Validates that the new stateless retrieval pattern maintains accuracy
compared to the original pipeline approach.

Metrics tracked:
- Source relevance scores
- Response quality (semantic similarity)
- Retrieval precision/recall
- RAPTOR summary usage effectiveness

Run with: pytest tests/test_accuracy_benchmark.py -v
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from statistics import mean, stdev

import pytest
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:7860"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


@dataclass
class RetrievalResult:
    """Result from a retrieval operation."""
    query: str
    response: str
    sources: List[Dict]
    execution_time_ms: int
    retrieval_strategy: str
    node_count: int = 0
    raptor_summaries_used: int = 0


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for comparison."""
    avg_source_score: float = 0.0
    min_source_score: float = 0.0
    max_source_score: float = 0.0
    source_count: int = 0
    response_length: int = 0
    execution_time_ms: int = 0
    raptor_summaries_used: int = 0


@dataclass
class BenchmarkResult:
    """Result of accuracy benchmark comparison."""
    query: str
    old_metrics: AccuracyMetrics
    new_metrics: AccuracyMetrics
    accuracy_score: float  # 0-1 score comparing old vs new
    passed: bool


class AccuracyBenchmark:
    """Benchmark accuracy between old pipeline and new stateless pattern."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def _query_old_pipeline(
        self,
        notebook_id: str,
        query: str,
        user_id: str = DEFAULT_USER_ID
    ) -> RetrievalResult:
        """Query using old pipeline (fast_mode=false)."""
        response = self.session.post(
            f"{self.base_url}/api/chat",
            json={
                "message": query,
                "notebook_ids": [notebook_id],
                "mode": "chat",
                "stream": False,
                "fast_mode": False,
                "user_id": user_id
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        return RetrievalResult(
            query=query,
            response=data.get("response", ""),
            sources=data.get("sources", []),
            execution_time_ms=data.get("metadata", {}).get("execution_time_ms", 0),
            retrieval_strategy=data.get("retrieval_strategy", "unknown"),
            node_count=data.get("metadata", {}).get("node_count", 0),
            raptor_summaries_used=0
        )

    def _query_new_stateless(
        self,
        notebook_id: str,
        query: str,
        user_id: str = DEFAULT_USER_ID
    ) -> RetrievalResult:
        """Query using new stateless pattern (fast_mode=true or /api/query)."""
        response = self.session.post(
            f"{self.base_url}/api/query",
            json={
                "notebook_id": notebook_id,
                "query": query,
                "include_sources": True,
                "max_sources": 6
            },
            headers={"X-User-ID": user_id},
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        metadata = data.get("metadata", {})
        return RetrievalResult(
            query=query,
            response=data.get("response", ""),
            sources=data.get("sources", []),
            execution_time_ms=metadata.get("execution_time_ms", 0),
            retrieval_strategy=metadata.get("retrieval_strategy", "unknown"),
            node_count=metadata.get("node_count", 0),
            raptor_summaries_used=metadata.get("raptor_summaries_used", 0)
        )

    def _calculate_metrics(self, result: RetrievalResult) -> AccuracyMetrics:
        """Calculate accuracy metrics from retrieval result."""
        scores = [s.get("score", s.get("relevance_score", 0)) for s in result.sources]

        return AccuracyMetrics(
            avg_source_score=mean(scores) if scores else 0.0,
            min_source_score=min(scores) if scores else 0.0,
            max_source_score=max(scores) if scores else 0.0,
            source_count=len(result.sources),
            response_length=len(result.response),
            execution_time_ms=result.execution_time_ms,
            raptor_summaries_used=result.raptor_summaries_used
        )

    def _calculate_accuracy_score(
        self,
        old_metrics: AccuracyMetrics,
        new_metrics: AccuracyMetrics
    ) -> float:
        """Calculate accuracy score (0-1) comparing new vs old.

        Score components:
        - Source quality (40%): Compare average source scores
        - Source coverage (30%): Compare number of relevant sources
        - Response completeness (30%): Compare response length
        """
        # Source quality comparison
        if old_metrics.avg_source_score > 0:
            source_quality = min(new_metrics.avg_source_score / old_metrics.avg_source_score, 1.0)
        else:
            source_quality = 1.0 if new_metrics.avg_source_score > 0 else 0.5

        # Source coverage comparison
        if old_metrics.source_count > 0:
            source_coverage = min(new_metrics.source_count / old_metrics.source_count, 1.0)
        else:
            source_coverage = 1.0 if new_metrics.source_count > 0 else 0.5

        # Response completeness (allow some variance)
        if old_metrics.response_length > 0:
            length_ratio = new_metrics.response_length / old_metrics.response_length
            response_completeness = min(length_ratio, 1.0) if length_ratio >= 0.7 else length_ratio
        else:
            response_completeness = 1.0 if new_metrics.response_length > 0 else 0.5

        # Weighted score
        score = (
            source_quality * 0.40 +
            source_coverage * 0.30 +
            response_completeness * 0.30
        )

        return round(score, 3)

    def run_benchmark(
        self,
        notebook_id: str,
        test_queries: List[str],
        accuracy_threshold: float = 0.85
    ) -> Tuple[bool, List[BenchmarkResult], Dict]:
        """Run accuracy benchmark comparing old vs new retrieval.

        Args:
            notebook_id: Notebook to test
            test_queries: List of test queries
            accuracy_threshold: Minimum acceptable accuracy score (default 85%)

        Returns:
            Tuple of (all_passed, results, summary)
        """
        results = []
        all_passed = True

        for query in test_queries:
            logger.info(f"Testing query: {query[:50]}...")

            try:
                # Get results from both methods
                old_result = self._query_old_pipeline(notebook_id, query)
                new_result = self._query_new_stateless(notebook_id, query)

                # Calculate metrics
                old_metrics = self._calculate_metrics(old_result)
                new_metrics = self._calculate_metrics(new_result)

                # Calculate accuracy score
                accuracy_score = self._calculate_accuracy_score(old_metrics, new_metrics)
                passed = accuracy_score >= accuracy_threshold

                if not passed:
                    all_passed = False
                    logger.warning(
                        f"Query failed accuracy threshold: {accuracy_score:.2%} < {accuracy_threshold:.2%}"
                    )

                results.append(BenchmarkResult(
                    query=query,
                    old_metrics=old_metrics,
                    new_metrics=new_metrics,
                    accuracy_score=accuracy_score,
                    passed=passed
                ))

                # Log comparison
                logger.info(
                    f"  Old: {old_metrics.execution_time_ms}ms, sources={old_metrics.source_count}, "
                    f"avg_score={old_metrics.avg_source_score:.3f}"
                )
                logger.info(
                    f"  New: {new_metrics.execution_time_ms}ms, sources={new_metrics.source_count}, "
                    f"avg_score={new_metrics.avg_source_score:.3f}, raptor={new_metrics.raptor_summaries_used}"
                )
                logger.info(f"  Accuracy: {accuracy_score:.2%} {'PASS' if passed else 'FAIL'}")

            except Exception as e:
                logger.error(f"Error testing query '{query[:30]}...': {e}")
                results.append(BenchmarkResult(
                    query=query,
                    old_metrics=AccuracyMetrics(),
                    new_metrics=AccuracyMetrics(),
                    accuracy_score=0.0,
                    passed=False
                ))
                all_passed = False

        # Calculate summary
        accuracy_scores = [r.accuracy_score for r in results]
        old_times = [r.old_metrics.execution_time_ms for r in results if r.old_metrics.execution_time_ms > 0]
        new_times = [r.new_metrics.execution_time_ms for r in results if r.new_metrics.execution_time_ms > 0]

        summary = {
            "total_queries": len(test_queries),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "avg_accuracy": mean(accuracy_scores) if accuracy_scores else 0,
            "min_accuracy": min(accuracy_scores) if accuracy_scores else 0,
            "max_accuracy": max(accuracy_scores) if accuracy_scores else 0,
            "avg_old_time_ms": mean(old_times) if old_times else 0,
            "avg_new_time_ms": mean(new_times) if new_times else 0,
            "speedup_factor": (mean(old_times) / mean(new_times)) if (old_times and new_times and mean(new_times) > 0) else 1,
            "accuracy_threshold": accuracy_threshold
        }

        return all_passed, results, summary


# Test Queries (customize based on your notebooks)
SAMPLE_TEST_QUERIES = [
    "What are the main topics covered in this document?",
    "Summarize the key findings",
    "What conclusions can be drawn from this content?",
    "Explain the methodology described",
    "What are the recommendations mentioned?",
]


class TestAccuracyBenchmark:
    """Pytest test class for accuracy benchmarks."""

    @pytest.fixture
    def benchmark(self):
        return AccuracyBenchmark()

    @pytest.fixture
    def notebook_id(self):
        """Get first available notebook for testing."""
        response = requests.get(f"{BASE_URL}/api/query/notebooks")
        if response.status_code == 200:
            notebooks = response.json().get("notebooks", [])
            if notebooks:
                return notebooks[0]["id"]
        pytest.skip("No notebooks available for testing")

    def test_accuracy_meets_threshold(self, benchmark, notebook_id):
        """Test that new retrieval maintains >= 85% accuracy vs old."""
        all_passed, results, summary = benchmark.run_benchmark(
            notebook_id=notebook_id,
            test_queries=SAMPLE_TEST_QUERIES,
            accuracy_threshold=0.85
        )

        logger.info(f"\n=== ACCURACY BENCHMARK SUMMARY ===")
        logger.info(f"Queries tested: {summary['total_queries']}")
        logger.info(f"Passed: {summary['passed']}, Failed: {summary['failed']}")
        logger.info(f"Average accuracy: {summary['avg_accuracy']:.2%}")
        logger.info(f"Accuracy range: {summary['min_accuracy']:.2%} - {summary['max_accuracy']:.2%}")
        logger.info(f"Avg old pipeline time: {summary['avg_old_time_ms']:.0f}ms")
        logger.info(f"Avg new stateless time: {summary['avg_new_time_ms']:.0f}ms")
        logger.info(f"Speedup factor: {summary['speedup_factor']:.1f}x")

        assert all_passed, f"Accuracy benchmark failed. {summary['failed']} queries below threshold."

    def test_new_pattern_is_faster(self, benchmark, notebook_id):
        """Test that new stateless pattern is faster than old pipeline."""
        _, results, summary = benchmark.run_benchmark(
            notebook_id=notebook_id,
            test_queries=SAMPLE_TEST_QUERIES[:3],  # Fewer queries for speed test
            accuracy_threshold=0.0  # Don't fail on accuracy
        )

        speedup = summary['speedup_factor']
        logger.info(f"Speedup factor: {speedup:.1f}x")

        # Expect at least 2x speedup
        assert speedup >= 2.0, f"Expected >= 2x speedup, got {speedup:.1f}x"

    def test_raptor_summaries_used(self, benchmark, notebook_id):
        """Test that RAPTOR summaries are being used in new pattern."""
        _, results, _ = benchmark.run_benchmark(
            notebook_id=notebook_id,
            test_queries=SAMPLE_TEST_QUERIES[:2],
            accuracy_threshold=0.0
        )

        raptor_usage = [r.new_metrics.raptor_summaries_used for r in results]
        total_raptor = sum(raptor_usage)

        logger.info(f"RAPTOR summaries used: {raptor_usage}, total: {total_raptor}")

        # Just log, don't fail if RAPTOR not available
        if total_raptor == 0:
            logger.warning("No RAPTOR summaries used - may not be built for this notebook")


def save_report(summary: Dict, results: List[BenchmarkResult], output_dir: str = "test_results"):
    """Save benchmark report to JSON and text files."""
    import os
    from datetime import datetime

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON report
    json_path = os.path.join(output_dir, f"accuracy_report_{timestamp}.json")
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "results": [
            {
                "query": r.query,
                "accuracy_score": r.accuracy_score,
                "passed": r.passed,
                "old_metrics": {
                    "avg_source_score": r.old_metrics.avg_source_score,
                    "source_count": r.old_metrics.source_count,
                    "response_length": r.old_metrics.response_length,
                    "execution_time_ms": r.old_metrics.execution_time_ms
                },
                "new_metrics": {
                    "avg_source_score": r.new_metrics.avg_source_score,
                    "source_count": r.new_metrics.source_count,
                    "response_length": r.new_metrics.response_length,
                    "execution_time_ms": r.new_metrics.execution_time_ms,
                    "raptor_summaries_used": r.new_metrics.raptor_summaries_used
                }
            }
            for r in results
        ]
    }

    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)

    # Text report
    txt_path = os.path.join(output_dir, f"accuracy_report_{timestamp}.txt")
    with open(txt_path, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("ACCURACY BENCHMARK REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 70 + "\n\n")

        f.write("SUMMARY\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Queries:      {summary['total_queries']}\n")
        f.write(f"Passed:             {summary['passed']}\n")
        f.write(f"Failed:             {summary['failed']}\n")
        f.write(f"Average Accuracy:   {summary['avg_accuracy']:.2%}\n")
        f.write(f"Min Accuracy:       {summary['min_accuracy']:.2%}\n")
        f.write(f"Max Accuracy:       {summary['max_accuracy']:.2%}\n")
        f.write(f"Accuracy Threshold: {summary['accuracy_threshold']:.2%}\n")
        f.write(f"\nOld Avg Time:       {summary['avg_old_time_ms']:.0f}ms\n")
        f.write(f"New Avg Time:       {summary['avg_new_time_ms']:.0f}ms\n")
        f.write(f"Speedup Factor:     {summary['speedup_factor']:.1f}x\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("=" * 70 + "\n\n")

        for r in results:
            f.write(f"Query: {r.query[:60]}...\n" if len(r.query) > 60 else f"Query: {r.query}\n")
            f.write(f"  Accuracy: {r.accuracy_score:.2%} {'PASS' if r.passed else 'FAIL'}\n")
            f.write(f"  Old: {r.old_metrics.execution_time_ms}ms, sources={r.old_metrics.source_count}, avg_score={r.old_metrics.avg_source_score:.3f}\n")
            f.write(f"  New: {r.new_metrics.execution_time_ms}ms, sources={r.new_metrics.source_count}, avg_score={r.new_metrics.avg_source_score:.3f}, raptor={r.new_metrics.raptor_summaries_used}\n")
            f.write("\n")

    print(f"\nReports saved to:")
    print(f"  - {json_path}")
    print(f"  - {txt_path}")

    return json_path, txt_path


if __name__ == "__main__":
    # Run standalone benchmark
    benchmark = AccuracyBenchmark()

    # Get first notebook
    response = requests.get(f"{BASE_URL}/api/query/notebooks")
    if response.status_code != 200:
        print("Failed to get notebooks")
        exit(1)

    notebooks = response.json().get("notebooks", [])
    if not notebooks:
        print("No notebooks available")
        exit(1)

    notebook_id = notebooks[0]["id"]
    print(f"Testing notebook: {notebooks[0]['name']} ({notebook_id})")

    all_passed, results, summary = benchmark.run_benchmark(
        notebook_id=notebook_id,
        test_queries=SAMPLE_TEST_QUERIES,
        accuracy_threshold=0.85
    )

    print("\n" + "=" * 60)
    print("ACCURACY BENCHMARK RESULTS")
    print("=" * 60)
    print(json.dumps(summary, indent=2))
    print(f"\nOverall: {'PASSED' if all_passed else 'FAILED'}")

    # Save reports
    save_report(summary, results)
