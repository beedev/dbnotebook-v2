#!/usr/bin/env python3
"""Download reranker models for local use.

Downloads MixedBread reranker models to a local directory so they can be
used at runtime without network access.

Usage:
    python scripts/download_reranker_models.py [--models base,large,xsmall] [--output-dir models/rerankers]

Models:
    - base: mxbai-rerank-base-v1 (~500MB) - balanced quality/speed
    - large: mxbai-rerank-large-v1 (~3GB) - best quality, slower
    - xsmall: mxbai-rerank-xsmall-v1 (~100MB) - fastest, lower quality
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_model(model_id: str, output_dir: Path) -> Path:
    """Download a HuggingFace model to local directory.

    Args:
        model_id: HuggingFace model ID (e.g., "mixedbread-ai/mxbai-rerank-base-v1")
        output_dir: Directory to save the model

    Returns:
        Path to the downloaded model directory
    """
    from huggingface_hub import snapshot_download

    # Create model-specific subdirectory
    model_name = model_id.split("/")[-1]
    model_path = output_dir / model_name

    print(f"Downloading {model_id} to {model_path}...")

    # Download the model
    snapshot_download(
        repo_id=model_id,
        local_dir=str(model_path),
        local_dir_use_symlinks=False,  # Copy files instead of symlinking
        ignore_patterns=["*.md", "*.txt", ".gitattributes"]  # Skip non-essential files
    )

    print(f"  Downloaded to: {model_path}")
    return model_path


def verify_model(model_path: Path) -> bool:
    """Verify a downloaded model works correctly.

    Args:
        model_path: Path to the model directory

    Returns:
        True if model loads and runs correctly
    """
    print(f"Verifying {model_path.name}...")

    try:
        from sentence_transformers import CrossEncoder

        # Load the model
        model = CrossEncoder(str(model_path))

        # Test with sample query/document pairs
        pairs = [
            ["What is the capital of France?", "Paris is the capital of France."],
            ["What is the capital of France?", "The Eiffel Tower is in Paris."],
        ]

        scores = model.predict(pairs)
        print(f"  Test scores: {scores}")
        print(f"  Verified successfully")
        return True

    except Exception as e:
        print(f"  Verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download reranker models for local use")
    parser.add_argument(
        "--models",
        type=str,
        default="base",
        help="Comma-separated list of models to download: base, large, xsmall (default: base)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/rerankers",
        help="Directory to save models (default: models/rerankers)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify models after download"
    )
    args = parser.parse_args()

    # Model mapping
    MODEL_MAP = {
        "base": "mixedbread-ai/mxbai-rerank-base-v1",
        "large": "mixedbread-ai/mxbai-rerank-large-v1",
        "xsmall": "mixedbread-ai/mxbai-rerank-xsmall-v1",
    }

    # Parse models to download
    models_to_download = [m.strip() for m in args.models.split(",")]

    # Validate model names
    for model in models_to_download:
        if model not in MODEL_MAP:
            print(f"Error: Unknown model '{model}'. Available: {list(MODEL_MAP.keys())}")
            sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir.absolute()}")
    print(f"Models to download: {models_to_download}")
    print()

    # Download each model
    downloaded = []
    for model_key in models_to_download:
        model_id = MODEL_MAP[model_key]
        try:
            model_path = download_model(model_id, output_dir)
            downloaded.append((model_key, model_path))
        except Exception as e:
            print(f"Error downloading {model_key}: {e}")
            continue

    print()

    # Verify if requested
    if args.verify:
        print("=== Verification ===")
        for model_key, model_path in downloaded:
            verify_model(model_path)
        print()

    # Print usage instructions
    print("=== Usage ===")
    print("Set the model path in your code or environment:")
    print()
    for model_key, model_path in downloaded:
        print(f"  {model_key}: {model_path.absolute()}")
    print()
    print("In API calls, use the local path as the model parameter:")
    print('  {"reranker_model": "models/rerankers/mxbai-rerank-base-v1"}')
    print()
    print("Or set via settings API:")
    print('  curl -X POST localhost:7860/api/settings/reranker -d \'{"model": "models/rerankers/mxbai-rerank-base-v1"}\'')


if __name__ == "__main__":
    main()
