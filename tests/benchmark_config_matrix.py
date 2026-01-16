#!/usr/bin/env python3
"""
Configuration Matrix Accuracy Benchmark

Tests RAG accuracy across different model configurations:
- Models: gpt-4.1-nano, gpt-4.1-mini, gpt-4.1
- Top-K: 6, 3

Ground truth based on HTC Global Travel Policy document.

Usage:
    python tests/benchmark_config_matrix.py --notebook-id <id> --output results.json
    python tests/benchmark_config_matrix.py --quick  # Fast test with one model
"""

import argparse
import json
import re
import time
from datetime import datetime
import requests

# =============================================================================
# GROUND TRUTH DATA - Travel Policy
# =============================================================================

GROUND_TRUTH = {
    "L11 & L12": {
        "mode_of_travel": "Air",
        "hotel": "Actuals",
        "private_arrangement": "NA",
        "per_diem": "Actuals",
        "local_conveyance": "NA",
    },
    "L8 to L10": {
        "mode_of_travel": "Air (Economy)",
        "hotel": "Actuals",
        "private_arrangement": "400",
        "per_diem": "Actuals",
        "local_conveyance": "300",
    },
    "L4 to L7": {
        "mode_of_travel": "Air/Train AC",
        "hotel": "Actuals",
        "private_arrangement": "300",
        "per_diem": "500",
        "local_conveyance": "250",
    },
    "L1 to L3": {
        "mode_of_travel": "Air/Train AC",
        "hotel": "Actuals",
        "private_arrangement": "200",
        "per_diem": "500",
        "local_conveyance": "150",
    },
}

TEST_QUERIES = [
    {"query": "What is the travel policy for L11 employees?", "designation": "L11 & L12", "expected_fields": ["mode_of_travel", "hotel", "per_diem"]},
    {"query": "What lodging charges can L12 employees claim?", "designation": "L11 & L12", "expected_fields": ["hotel"]},
    {"query": "What is the per diem for L8 level?", "designation": "L8 to L10", "expected_fields": ["per_diem"]},
    {"query": "What is local conveyance for L9?", "designation": "L8 to L10", "expected_fields": ["local_conveyance"]},
    {"query": "Can L5 employees travel by air?", "designation": "L4 to L7", "expected_fields": ["mode_of_travel"]},
    {"query": "What is the private arrangement allowance for L6?", "designation": "L4 to L7", "expected_fields": ["private_arrangement"]},
    {"query": "What is the food allowance for L2 employees?", "designation": "L1 to L3", "expected_fields": ["per_diem"]},
    {"query": "What is the local conveyance limit for L1?", "designation": "L1 to L3", "expected_fields": ["local_conveyance"]},
]

MODELS = [
    {"name": "gpt-4.1-nano", "provider": "openai"},
    {"name": "gpt-4.1-mini", "provider": "openai"},
    {"name": "gpt-4.1", "provider": "openai"},
    {"name": "meta-llama/llama-4-maverick-17b-128e-instruct", "provider": "groq"},
    {"name": "meta-llama/llama-4-scout-17b-16e-instruct", "provider": "groq"},
]

TOP_K_VALUES = [6, 3]

def extract_numbers(text):
    """Extract all numbers from text."""
    return re.findall(r'\b\d+\b', text.replace(',', ''))

def score_response(response, designation, expected_fields):
    """Score a response against ground truth."""
    ground_truth = GROUND_TRUTH.get(designation, {})
    response_lower = response.lower()
    field_scores = {}
    explanations = []

    for field in expected_fields:
        expected_value = ground_truth.get(field, "")

        if expected_value == "NA":
            if any(x in response_lower for x in ["not applicable", "n/a", "na", "not eligible"]):
                field_scores[field] = 1.0
                explanations.append(f"{field}: Found NA")
            else:
                field_scores[field] = 0.0
                explanations.append(f"{field}: Expected NA")

        elif expected_value == "Actuals":
            if any(x in response_lower for x in ["actual", "actuals", "reimbursed at actual"]):
                field_scores[field] = 1.0
                explanations.append(f"{field}: Found actuals")
            else:
                field_scores[field] = 0.0
                explanations.append(f"{field}: Expected actuals")

        elif expected_value.isdigit():
            numbers = extract_numbers(response)
            if expected_value in numbers:
                field_scores[field] = 1.0
                explanations.append(f"{field}: Found {expected_value}")
            elif any(abs(int(n) - int(expected_value)) <= 50 for n in numbers if n.isdigit()):
                field_scores[field] = 0.5
                explanations.append(f"{field}: Close to {expected_value}")
            else:
                field_scores[field] = 0.0
                explanations.append(f"{field}: Missing {expected_value}")

        else:
            if expected_value.lower() in response_lower:
                field_scores[field] = 1.0
                explanations.append(f"{field}: Found '{expected_value}'")
            elif "air" in response_lower and "air" in expected_value.lower():
                field_scores[field] = 0.7
                explanations.append(f"{field}: Partial match")
            else:
                field_scores[field] = 0.0
                explanations.append(f"{field}: Missing '{expected_value}'")

    overall = sum(field_scores.values()) / len(field_scores) if field_scores else 0.0
    return {"score": overall, "field_scores": field_scores, "explanation": "; ".join(explanations)}

def run_query(base_url, notebook_id, api_key, query, model, provider, top_k=6, reranker_enabled=True, skip_raptor=None):
    """Execute a query against the RAG API."""
    url = f"{base_url}/api/query"
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    payload = {
        "notebook_id": notebook_id, "query": query,
        "model": model, "provider": provider,
        "include_sources": True, "max_sources": top_k,
        "reranker_enabled": reranker_enabled,
    }
    # Only include skip_raptor if explicitly set (None = use server default)
    if skip_raptor is not None:
        payload["skip_raptor"] = skip_raptor

    try:
        start = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            return {"success": True, "response": data.get("response", ""),
                    "metadata": data.get("metadata", {}), "latency_ms": latency}
        return {"success": False, "error": f"HTTP {response.status_code}", "latency_ms": latency}
    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": 0}

def run_benchmark(base_url, notebook_id, api_key, models=None, top_k_values=None, verbose=False, reranker_enabled=True, skip_raptor=None):
    """Run the full benchmark across all configurations."""
    models = models or MODELS
    top_k_values = top_k_values or TOP_K_VALUES

    reranker_status = "enabled" if reranker_enabled else "DISABLED"
    # None = server default (skip_raptor=True), True = explicit skip, False = explicit include
    raptor_status = "SKIPPED" if skip_raptor else ("enabled" if skip_raptor is False else "server-default")
    results = {
        "timestamp": datetime.now().isoformat(),
        "config": {"models": [m["name"] for m in models], "top_k_values": top_k_values, "num_queries": len(TEST_QUERIES), "reranker_enabled": reranker_enabled, "skip_raptor": skip_raptor},
        "results_by_config": [],
        "summary": {},
    }

    total = len(models) * len(top_k_values) * len(TEST_QUERIES)
    test_num = 0

    print(f"\n{'='*60}")
    print(f"ACCURACY BENCHMARK - {total} tests (reranker: {reranker_status}, raptor: {raptor_status})")
    print(f"{'='*60}\n")

    for model_cfg in models:
        model, provider = model_cfg["name"], model_cfg["provider"]

        for top_k in top_k_values:
            config_key = f"{model}_topk{top_k}"
            cfg_results = {"config": {"model": model, "provider": provider, "top_k": top_k, "reranker_enabled": reranker_enabled, "skip_raptor": skip_raptor},
                          "scores": [], "latencies": [], "details": []}

            for q in TEST_QUERIES:
                test_num += 1
                print(f"\r[{test_num}/{total}] {model} topk={top_k}...", end="", flush=True)

                result = run_query(base_url, notebook_id, api_key, q["query"], model, provider, top_k, reranker_enabled, skip_raptor)

                if result["success"]:
                    score_result = score_response(result["response"], q["designation"], q["expected_fields"])
                    cfg_results["scores"].append(score_result["score"])
                    cfg_results["latencies"].append(result["latency_ms"])
                    cfg_results["details"].append({
                        "query": q["query"], "score": score_result["score"],
                        "explanation": score_result["explanation"],
                        "llm_ms": result["metadata"].get("timings", {}).get("8_llm_completion_ms", 0),
                    })
                    if verbose:
                        print(f" Score: {score_result['score']:.2f}")
                else:
                    cfg_results["scores"].append(0.0)
                    cfg_results["details"].append({"query": q["query"], "error": result["error"]})

                time.sleep(0.5)

            scores, lats = cfg_results["scores"], [l for l in cfg_results["latencies"] if l > 0]
            cfg_results["accuracy"] = (sum(scores) / len(scores) * 100) if scores else 0
            cfg_results["avg_latency_ms"] = sum(lats) / len(lats) if lats else 0

            results["results_by_config"].append(cfg_results)
            print(f"\n  {config_key}: Accuracy={cfg_results['accuracy']:.1f}%, Latency={cfg_results['avg_latency_ms']:.0f}ms")

    # Summary
    all_cfgs = results["results_by_config"]
    if all_cfgs:
        best = max(all_cfgs, key=lambda x: x["accuracy"])
        model_accs = {}
        for c in all_cfgs:
            m = c["config"]["model"]
            model_accs.setdefault(m, []).append(c["accuracy"])

        results["summary"] = {
            "total_tests": total,
            "best_config": {"model": best["config"]["model"], "top_k": best["config"]["top_k"],
                           "accuracy": best["accuracy"], "avg_latency_ms": best["avg_latency_ms"]},
            "model_comparison": {m: {"avg": sum(a)/len(a), "max": max(a)} for m, a in model_accs.items()},
        }

    return results

def print_summary(results):
    """Print formatted summary."""
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)

    s = results.get("summary", {})
    if s:
        print(f"\nTotal Tests: {s['total_tests']}")
        b = s.get("best_config", {})
        print(f"\n🏆 BEST: {b.get('model')} topk={b.get('top_k')} → {b.get('accuracy', 0):.1f}% accuracy")
        print(f"   Latency: {b.get('avg_latency_ms', 0):.0f}ms")

        print("\n📊 MODEL COMPARISON:")
        for m, stats in s.get("model_comparison", {}).items():
            print(f"   {m}: Avg={stats['avg']:.1f}%, Max={stats['max']:.1f}%")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description="RAG Configuration Matrix Benchmark")
    parser.add_argument("--base-url", default="http://localhost:7860")
    parser.add_argument("--notebook-id", default="18ee0c23-a2ce-4eb2-a56c-62a12dee964a")
    parser.add_argument("--api-key", default="dbn_00000000000000000000000000000001")
    parser.add_argument("--output", default="test_results/config_matrix_benchmark.json")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--quick", action="store_true", help="Quick test with one model")
    parser.add_argument("--no-reranker", action="store_true", help="Disable reranker for testing")
    parser.add_argument("--skip-raptor", action="store_true", help="Skip RAPTOR summaries (explicit)")
    parser.add_argument("--enable-raptor", action="store_true", help="Enable RAPTOR summaries (explicit)")
    parser.add_argument("--model", type=str, help="Test specific model only (e.g., gpt-4.1-mini)")
    args = parser.parse_args()

    # Model selection
    if args.model:
        # Find the model in MODELS list
        model_cfg = next((m for m in MODELS if m["name"] == args.model), None)
        if not model_cfg:
            print(f"Model '{args.model}' not found. Available: {[m['name'] for m in MODELS]}")
            return
        models = [model_cfg]
    elif args.quick:
        models = [{"name": "gpt-4.1-nano", "provider": "openai"}]
    else:
        models = MODELS

    top_k_values = [6] if args.quick else TOP_K_VALUES
    reranker_enabled = not args.no_reranker
    # --skip-raptor = True, --enable-raptor = False, neither = None (server default)
    skip_raptor = True if args.skip_raptor else (False if args.enable_raptor else None)

    results = run_benchmark(args.base_url, args.notebook_id, args.api_key, models, top_k_values, args.verbose, reranker_enabled, skip_raptor)
    print_summary(results)

    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📄 Results saved to: {args.output}")

if __name__ == "__main__":
    main()
