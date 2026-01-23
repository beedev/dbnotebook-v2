"""Thread-safe Reranker Provider with smaller model.

This module provides a thread-safe shared reranker instance to avoid loading
the cross-encoder model multiple times and prevent ONNX Runtime concurrency issues.

The ThreadSafeReranker wrapper serializes access to the underlying ONNX model
using a threading.Lock, which prevents SIGSEGV crashes under concurrent load.

Supports both HuggingFace model IDs and local model paths:
- HuggingFace: "mixedbread-ai/mxbai-rerank-base-v1" (downloads on first use)
- Local path: "models/rerankers/mxbai-rerank-base-v1" (pre-downloaded)

Usage:
    from dbnotebook.core.providers.reranker_provider import get_shared_reranker

    # Using HuggingFace model ID (downloads if not cached)
    reranker = get_shared_reranker(
        model="mixedbread-ai/mxbai-rerank-base-v1",
        top_n=10
    )

    # Using local path (no download needed)
    reranker = get_shared_reranker(
        model="models/rerankers/mxbai-rerank-base-v1",
        top_n=10
    )

    reranked_nodes = reranker.postprocess_nodes(nodes, query_bundle)
"""

import logging
import os
import threading
from pathlib import Path
from typing import Optional, List

from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.schema import NodeWithScore, QueryBundle

logger = logging.getLogger(__name__)

# Thread-safe singleton with reentrant lock (RLock allows same thread to acquire multiple times)
_reranker_lock = threading.RLock()
_shared_reranker: Optional[SentenceTransformerRerank] = None
_reranker_config: dict = {}
_reranker_enabled: bool = True  # Runtime enable/disable flag

# Default local model directory (relative to project root)
DEFAULT_LOCAL_MODEL_DIR = "models/rerankers"

# Model aliases for convenience
MODEL_ALIASES = {
    "base": "mxbai-rerank-base-v1",
    "base-v1": "mxbai-rerank-base-v1",
    "large": "mxbai-rerank-large-v1",
    "large-v1": "mxbai-rerank-large-v1",
    "xsmall": "mxbai-rerank-xsmall-v1",
    "xsmall-v1": "mxbai-rerank-xsmall-v1",
    "disabled": None,  # Special alias to disable reranking
}


def _is_valid_local_model(path: Path) -> bool:
    """Check if a local model directory contains valid model files."""
    if not path.exists() or not path.is_dir():
        return False
    # Check for common model files
    model_files = ["pytorch_model.bin", "model.safetensors", "tf_model.h5", "model.ckpt.index", "flax_model.msgpack"]
    return any((path / f).exists() for f in model_files)


def resolve_model_path(model: str) -> Optional[str]:
    """Resolve model identifier to actual model path or HuggingFace ID.

    Priority:
    1. If model is "disabled", return None
    2. If model is an alias (e.g., "base", "large"), expand it
    3. If model is a local path with valid model files, use it
    4. Otherwise, assume it's a HuggingFace model ID

    Args:
        model: Model identifier (alias, local path, or HuggingFace ID)

    Returns:
        Resolved model path/ID, or None if disabled
    """
    # Handle disabled alias
    if model.lower() == "disabled":
        return None

    # Check for aliases
    if model.lower() in MODEL_ALIASES:
        alias_value = MODEL_ALIASES[model.lower()]
        if alias_value is None:
            return None
        # Try to find local model for alias (must have valid model files)
        local_path = Path(DEFAULT_LOCAL_MODEL_DIR) / alias_value
        if _is_valid_local_model(local_path):
            logger.info(f"Using local model for alias '{model}': {local_path}")
            return str(local_path)
        # Fall back to HuggingFace ID
        return f"mixedbread-ai/{alias_value}"

    # Check if it's a local path with valid model files
    local_path = Path(model)
    if _is_valid_local_model(local_path):
        logger.info(f"Using local model path: {model}")
        return model

    # Check in default local model directory
    local_path = Path(DEFAULT_LOCAL_MODEL_DIR) / model
    if _is_valid_local_model(local_path):
        logger.info(f"Found model in local directory: {local_path}")
        return str(local_path)

    # Assume it's a HuggingFace model ID
    return model


class ThreadSafeReranker:
    """Thread-safe wrapper for SentenceTransformerRerank.

    ONNX Runtime (used internally by SentenceTransformerRerank) is not thread-safe.
    This wrapper serializes access using a lock to prevent concurrent inference
    which would cause SIGSEGV crashes.
    """

    def __init__(
        self,
        reranker: SentenceTransformerRerank,
        lock: threading.Lock,
        top_n: int
    ):
        self._reranker = reranker
        self._lock = lock
        self._top_n = top_n

    def postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
        query_str: Optional[str] = None
    ) -> List[NodeWithScore]:
        """Thread-safe reranking with lock.

        Args:
            nodes: List of nodes with scores to rerank
            query_bundle: Query bundle for reranking (optional if query_str provided)
            query_str: Query string (optional if query_bundle provided)

        Returns:
            Reranked list of nodes, limited to top_n
        """
        if not nodes:
            return nodes

        with self._lock:
            # Temporarily set top_n for this call
            original_top_n = self._reranker.top_n
            self._reranker.top_n = self._top_n
            try:
                return self._reranker.postprocess_nodes(
                    nodes,
                    query_bundle=query_bundle,
                    query_str=query_str
                )
            finally:
                self._reranker.top_n = original_top_n

    @property
    def top_n(self) -> int:
        """Get the top_n value."""
        return self._top_n

    @top_n.setter
    def top_n(self, value: int) -> None:
        """Set the top_n value for subsequent calls."""
        self._top_n = value


def get_shared_reranker(
    model: str = "base",
    top_n: int = 10
) -> Optional[ThreadSafeReranker]:
    """Get or create thread-safe reranker instance.

    Uses singleton pattern with thread-safe wrapper to:
    1. Avoid loading the model (~500MB) multiple times
    2. Prevent ONNX Runtime concurrency crashes via serialized access

    Supports model aliases, local paths, and HuggingFace IDs:
    - Aliases: "base", "large", "xsmall", "disabled"
    - Local: "models/rerankers/mxbai-rerank-base-v1"
    - HuggingFace: "mixedbread-ai/mxbai-rerank-base-v1"

    Environment variables:
    - RERANKER_MODEL: Override model (xsmall, base, large, disabled)

    Args:
        model: Reranker model alias, path, or HuggingFace ID (default: "base")
        top_n: Default top_n for reranking (can be overridden via setter)

    Returns:
        Thread-safe reranker wrapper instance, or None if reranker is disabled
    """
    global _shared_reranker, _reranker_config, _reranker_enabled

    # RERANKER_MODEL env var overrides parameter default
    env_model = os.getenv("RERANKER_MODEL", "").strip()
    if env_model:
        model = env_model

    # Early return if reranker is disabled
    if not _reranker_enabled:
        return None

    with _reranker_lock:
        # Use model from config if set, otherwise use parameter
        config_model = _reranker_config.get("model", model)

        # Resolve to actual path or HuggingFace ID
        effective_model = resolve_model_path(config_model)

        # Handle "disabled" resolution
        if effective_model is None:
            _reranker_enabled = False
            _shared_reranker = None
            logger.info("Reranker disabled via model resolution")
            return None

        # Check if we need to create or recreate the reranker
        current_resolved = _reranker_config.get("resolved_model")
        if _shared_reranker is None or current_resolved != effective_model:
            logger.info(f"Initializing shared reranker: {effective_model}")
            _shared_reranker = SentenceTransformerRerank(
                model=effective_model,
                top_n=top_n
            )
            _reranker_config = {
                "model": config_model,
                "resolved_model": effective_model,
                "top_n": top_n
            }
            logger.info("Shared reranker initialized successfully")

    return ThreadSafeReranker(_shared_reranker, _reranker_lock, top_n)


def clear_shared_reranker() -> None:
    """Clear the shared reranker instance.

    Useful for testing or when you need to release memory.
    """
    global _shared_reranker, _reranker_config
    with _reranker_lock:
        _shared_reranker = None
        _reranker_config = {}
        logger.debug("Shared reranker cleared")


def set_reranker_config(
    model: Optional[str] = None,
    enabled: bool = True,
    top_n: Optional[int] = None
) -> dict:
    """Configure reranker at runtime.

    Allows switching reranker model or disabling reranker entirely without restart.
    Thread-safe - changes are applied atomically.

    Args:
        model: Reranker model name. If None, keeps current model.
               Options: "mixedbread-ai/mxbai-rerank-large-v1" (~3GB, best quality)
                        "mixedbread-ai/mxbai-rerank-base-v1" (~500MB, balanced)
                        "mixedbread-ai/mxbai-rerank-xsmall-v1" (~100MB, fastest)
        enabled: Whether reranking is enabled. If False, get_shared_reranker returns None.
        top_n: Default top_n for reranking. If None, keeps current value.

    Returns:
        Current configuration after update
    """
    global _shared_reranker, _reranker_config, _reranker_enabled

    with _reranker_lock:
        _reranker_enabled = enabled

        if not enabled:
            # Disable reranking - clear the instance to free memory
            _shared_reranker = None
            logger.info("Reranker disabled")
            return get_reranker_config()

        # Check if model change requires reload
        needs_reload = False
        if model and model != _reranker_config.get("model"):
            needs_reload = True
            _reranker_config["model"] = model
            # Clear resolved_model so it gets re-resolved
            _reranker_config.pop("resolved_model", None)

        if top_n is not None:
            _reranker_config["top_n"] = top_n

        if needs_reload:
            # Force reload on next get_shared_reranker() call
            _shared_reranker = None
            logger.info(f"Reranker model changed to {model}, will reload on next use")

        return get_reranker_config()


def get_reranker_config() -> dict:
    """Get current reranker configuration.

    Returns:
        Dict with keys:
        - enabled: Whether reranking is enabled
        - model: Original model identifier (alias, path, or HuggingFace ID)
        - resolved_model: Actual path/ID used for loading
        - top_n: Default top_n for reranking
        - loaded: Whether model is currently in memory
        - is_local: Whether using a local model path
    """
    with _reranker_lock:
        model = _reranker_config.get("model", "base")
        resolved = _reranker_config.get("resolved_model")
        if resolved is None and _reranker_enabled:
            resolved = resolve_model_path(model)

        return {
            "enabled": _reranker_enabled,
            "model": model,
            "resolved_model": resolved,
            "top_n": _reranker_config.get("top_n", 10),
            "loaded": _shared_reranker is not None,
            "is_local": resolved and os.path.exists(resolved) if resolved else False
        }


def is_reranker_enabled() -> bool:
    """Check if reranker is enabled.

    Returns:
        True if reranker is enabled, False otherwise
    """
    return _reranker_enabled


def list_available_models() -> list[dict]:
    """List all available reranker models (local and remote).

    Returns:
        List of model info dicts with keys:
        - id: Model identifier to use in API calls
        - name: Human-readable name
        - is_local: Whether model is available locally
        - path: Local path (if available locally)
        - size: Approximate size
        - quality: Quality rating
    """
    models = []
    local_dir = Path(DEFAULT_LOCAL_MODEL_DIR)

    # Define known models
    known_models = [
        {
            "id": "large",
            "name": "MxBai Large v1",
            "hf_id": "mixedbread-ai/mxbai-rerank-large-v1",
            "local_name": "mxbai-rerank-large-v1",
            "size": "~3GB",
            "quality": "Best",
            "speed": "Slow"
        },
        {
            "id": "base",
            "name": "MxBai Base v1",
            "hf_id": "mixedbread-ai/mxbai-rerank-base-v1",
            "local_name": "mxbai-rerank-base-v1",
            "size": "~500MB",
            "quality": "Good",
            "speed": "Medium"
        },
        {
            "id": "xsmall",
            "name": "MxBai XSmall v1",
            "hf_id": "mixedbread-ai/mxbai-rerank-xsmall-v1",
            "local_name": "mxbai-rerank-xsmall-v1",
            "size": "~100MB",
            "quality": "Fair",
            "speed": "Fast"
        },
    ]

    for model_info in known_models:
        local_path = local_dir / model_info["local_name"]
        is_local = local_path.exists()

        models.append({
            "id": model_info["id"],
            "name": model_info["name"],
            "hf_id": model_info["hf_id"],
            "is_local": is_local,
            "path": str(local_path) if is_local else None,
            "size": model_info["size"],
            "quality": model_info["quality"],
            "speed": model_info["speed"]
        })

    # Add "disabled" option
    models.append({
        "id": "disabled",
        "name": "Disabled",
        "hf_id": None,
        "is_local": True,
        "path": None,
        "size": "N/A",
        "quality": "N/A",
        "speed": "N/A"
    })

    return models
