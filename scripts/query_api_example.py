#!/usr/bin/env python3
"""
Simple DBNotebook Query API Example

This script demonstrates how to use the DBNotebook Query API for:
1. Listing available notebooks
2. Making stateless queries (no memory)
3. Making conversational queries (with memory)

Usage Examples:
    # List available models
    python scripts/query_api_example.py --list-models

    # Query with a specific model
    python scripts/query_api_example.py --model gpt-4.1-mini --query "What is the policy?"

    # Use Groq model
    python scripts/query_api_example.py -m meta-llama/llama-4-maverick-17b-128e-instruct -q "Summarize"

    # Full demo with specific model
    python scripts/query_api_example.py --model gpt-4o

    # Single query only (no demo)
    python scripts/query_api_example.py -m gpt-4.1-mini -q "What is the leave policy?" --no-demo

    # Specify notebook and model
    python scripts/query_api_example.py -n <notebook-uuid> -m llama3.1:latest

Available Options:
    --model, -m        LLM model (e.g., gpt-4.1-mini, llama3.1:latest)
    --notebook, -n     Notebook UUID to query
    --query, -q        Custom query to run
    --url              API base URL (default: http://localhost:7860)
    --api-key, -k      API key for authentication
    --list-models      List available models and exit
    --list-notebooks   List available notebooks and exit
    --no-demo          Skip demo queries (use with --query for single query)

Available Models:
    OpenAI:    gpt-4.1-mini, gpt-4.1, gpt-4o, gpt-4o-mini
    Groq:      meta-llama/llama-4-maverick-17b-128e-instruct, llama-3.3-70b-versatile
    Ollama:    llama3.1:latest, mistral:latest
    Anthropic: claude-sonnet-4-20250514, claude-3-5-haiku-latest
    Gemini:    gemini-2.0-flash, gemini-1.5-pro

Environment Variables:
    DBNOTEBOOK_API_URL      API base URL (default: http://localhost:7860)
    DBNOTEBOOK_API_KEY      Your API key (default: admin key)
    DBNOTEBOOK_NOTEBOOK_ID  Notebook UUID to query
"""

import os
import sys
import uuid
import json
import argparse
import requests
from typing import Optional

# Configuration - Override via environment variables
BASE_URL = os.getenv("DBNOTEBOOK_API_URL", "http://localhost:7860")
API_KEY = os.getenv("DBNOTEBOOK_API_KEY", "dbn_00000000000000000000000000000001")
# Default notebook ID - set via env or replace with your notebook's UUID
NOTEBOOK_ID = os.getenv("DBNOTEBOOK_NOTEBOOK_ID", "18ee0c23-a2ce-4eb2-a56c-62a12dee964a")

# Available models by provider
AVAILABLE_MODELS = {
    "openai": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini"],
    "groq": ["meta-llama/llama-4-maverick-17b-128e-instruct", "llama-3.3-70b-versatile"],
    "ollama": ["llama3.1:latest", "mistral:latest", "qwen2.5:latest"],
    "anthropic": ["claude-sonnet-4-20250514", "claude-3-5-haiku-latest"],
    "gemini": ["gemini-2.0-flash", "gemini-1.5-pro"],
}

# Headers for all requests
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def list_models():
    """Print available models."""
    print("\n" + "=" * 60)
    print("Available Models")
    print("=" * 60)
    for provider, models in AVAILABLE_MODELS.items():
        print(f"\n{provider.upper()}:")
        for model in models:
            print(f"  - {model}")
    print()


def list_notebooks():
    """List all available notebooks."""
    print("\n" + "=" * 60)
    print("Listing Available Notebooks")
    print("=" * 60)

    response = requests.get(
        f"{BASE_URL}/api/query/notebooks",
        headers=HEADERS
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return []

    data = response.json()
    notebooks = data.get("notebooks", [])

    print(f"\nFound {len(notebooks)} notebook(s):\n")
    for nb in notebooks:
        print(f"  ID: {nb['id']}")
        print(f"  Name: {nb['name']}")
        print(f"  Documents: {nb['document_count']}")
        print(f"  Created: {nb['created_at']}")
        print()

    return notebooks


def query_stateless(notebook_id: str, query: str, model: Optional[str] = None):
    """Make a stateless query (no conversation memory)."""
    print("\n" + "=" * 60)
    print("Stateless Query (No Memory)")
    print("=" * 60)
    print(f"Query: {query}")
    if model:
        print(f"Model: {model}")

    payload = {
        "notebook_id": notebook_id,
        "query": query,
        "include_sources": True,
        "max_sources": 3
    }

    if model:
        payload["model"] = model

    response = requests.post(
        f"{BASE_URL}/api/query",
        headers=HEADERS,
        json=payload
    )

    if response.status_code != 200:
        print(f"\nError: {response.status_code} - {response.text}")
        return None

    result = response.json()

    print(f"\n{'─' * 60}")
    print("Response:")
    print(f"{'─' * 60}")
    print(result.get("response", "No response"))

    # Print metadata
    metadata = result.get("metadata", {})
    print(f"\n{'─' * 60}")
    print("Metadata:")
    print(f"  Execution time: {metadata.get('execution_time_ms', 'N/A')}ms")
    print(f"  Model: {metadata.get('model', 'N/A')}")
    print(f"  Stateless: {metadata.get('stateless', 'N/A')}")
    print(f"  Node count: {metadata.get('node_count', 'N/A')}")

    # Print timing breakdown if available
    timings = metadata.get("timings", {})
    if timings:
        print(f"\n  Timing Breakdown:")
        for key, value in sorted(timings.items()):
            stage_name = key.replace("_ms", "").replace("_", " ").title()
            print(f"    {stage_name}: {value}ms")

    # Print sources
    sources = result.get("sources", [])
    if sources:
        print(f"\n{'─' * 60}")
        print(f"Sources ({len(sources)}):")
        for i, src in enumerate(sources, 1):
            print(f"\n  [{i}] {src.get('filename', 'Unknown')}")
            print(f"      Score: {src.get('score', 'N/A'):.3f}")
            snippet = src.get('snippet', '')[:200]
            print(f"      Snippet: {snippet}...")

    return result


def query_conversational(notebook_id: str, queries: list[str], model: Optional[str] = None):
    """Make conversational queries with memory."""
    print("\n" + "=" * 60)
    print("Conversational Queries (With Memory)")
    print("=" * 60)

    # Generate a session ID for this conversation
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")
    if model:
        print(f"Model: {model}")

    for i, query in enumerate(queries, 1):
        print(f"\n{'─' * 60}")
        print(f"Turn {i}: {query}")
        print(f"{'─' * 60}")

        payload = {
            "notebook_id": notebook_id,
            "query": query,
            "session_id": session_id,
            "include_sources": True,
            "max_sources": 2
        }

        if model:
            payload["model"] = model

        response = requests.post(
            f"{BASE_URL}/api/query",
            headers=HEADERS,
            json=payload
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            continue

        result = response.json()
        metadata = result.get("metadata", {})

        print(f"\nResponse: {result.get('response', 'No response')[:500]}...")
        print(f"\nHistory used: {metadata.get('history_messages_used', 0)} messages")
        print(f"Stateless: {metadata.get('stateless', 'N/A')}")
        print(f"Execution time: {metadata.get('execution_time_ms', 'N/A')}ms")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DBNotebook Query API Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query_api_example.py --model gpt-4.1-mini
  python query_api_example.py --model llama3.1:latest --query "What is the policy?"
  python query_api_example.py --notebook <uuid> --model gpt-4o --query "Summarize the documents"
  python query_api_example.py --list-models
  python query_api_example.py --list-notebooks
        """
    )

    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="LLM model to use (e.g., gpt-4.1-mini, llama3.1:latest)"
    )

    parser.add_argument(
        "--notebook", "-n",
        type=str,
        default=NOTEBOOK_ID,
        help=f"Notebook UUID to query (default: {NOTEBOOK_ID[:8]}...)"
    )

    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Custom query to run (single stateless query)"
    )

    parser.add_argument(
        "--url",
        type=str,
        default=BASE_URL,
        help=f"API base URL (default: {BASE_URL})"
    )

    parser.add_argument(
        "--api-key", "-k",
        type=str,
        default=API_KEY,
        help="API key for authentication"
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit"
    )

    parser.add_argument(
        "--list-notebooks",
        action="store_true",
        help="List available notebooks and exit"
    )

    parser.add_argument(
        "--no-demo",
        action="store_true",
        help="Skip demo queries (use with --query for single query)"
    )

    return parser.parse_args()


def main():
    """Run example queries."""
    args = parse_args()

    # Update globals from args
    global BASE_URL, API_KEY, HEADERS
    BASE_URL = args.url
    API_KEY = args.api_key
    HEADERS = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # Handle --list-models
    if args.list_models:
        list_models()
        return

    # Handle --list-notebooks
    if args.list_notebooks:
        list_notebooks()
        return

    print("=" * 60)
    print("DBNotebook Query API Example")
    print("=" * 60)
    print(f"API URL: {BASE_URL}")
    print(f"Notebook ID: {args.notebook}")
    if args.model:
        print(f"Model: {args.model}")

    # List notebooks to verify connection
    notebooks = list_notebooks()

    # Determine notebook ID
    notebook_id = args.notebook
    if not notebooks:
        print("\nNo notebooks found. Please create a notebook first.")
        return
    elif notebook_id not in [nb["id"] for nb in notebooks]:
        # Use first available notebook if specified not found
        notebook_id = notebooks[0]["id"]
        print(f"\nSpecified notebook not found, using: {notebook_id}")

    # If custom query provided, run it and exit
    if args.query:
        query_stateless(
            notebook_id=notebook_id,
            query=args.query,
            model=args.model
        )
        if args.no_demo:
            print("\n" + "=" * 60)
            print("Query Complete!")
            print("=" * 60)
            return

    # Run demo queries unless --no-demo
    if not args.no_demo:
        # Stateless query
        query_stateless(
            notebook_id=notebook_id,
            query="What are the key policies mentioned in the documents?",
            model=args.model
        )

        # Conversational queries (with memory)
        query_conversational(
            notebook_id=notebook_id,
            queries=[
                "What is the work from home policy?",
                "What are the eligibility requirements for it?",
                "Are there any exceptions to this policy?"
            ],
            model=args.model
        )

    print("\n" + "=" * 60)
    print("Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
