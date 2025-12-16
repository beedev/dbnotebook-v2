"""Plugin auto-registration and initialization."""

import logging
import os
from typing import Optional

from dotenv import load_dotenv

from .registry import PluginRegistry
from .interfaces import RetrievalStrategy, LLMProvider, EmbeddingProvider
from .strategies import (
    HybridRetrievalStrategy,
    SemanticRetrievalStrategy,
    KeywordRetrievalStrategy,
)
from .providers import (
    OllamaLLMProvider,
    OpenAILLMProvider,
    AnthropicLLMProvider,
    HuggingFaceEmbeddingProvider,
)

load_dotenv()

logger = logging.getLogger(__name__)

# Flag to track if plugins have been initialized
_plugins_initialized = False


def register_default_plugins() -> None:
    """Register all default plugins with the registry."""
    global _plugins_initialized

    if _plugins_initialized:
        logger.debug("Plugins already initialized, skipping")
        return

    # Register retrieval strategies
    PluginRegistry.register_strategy("hybrid", HybridRetrievalStrategy)
    PluginRegistry.register_strategy("semantic", SemanticRetrievalStrategy)
    PluginRegistry.register_strategy("keyword", KeywordRetrievalStrategy)

    # Register LLM providers
    PluginRegistry.register_llm_provider("ollama", OllamaLLMProvider)
    PluginRegistry.register_llm_provider("openai", OpenAILLMProvider)
    PluginRegistry.register_llm_provider("anthropic", AnthropicLLMProvider)

    # Register embedding providers
    PluginRegistry.register_embedding_provider("huggingface", HuggingFaceEmbeddingProvider)

    _plugins_initialized = True
    logger.info(f"Registered plugins: {PluginRegistry.get_registry_stats()}")


def get_configured_llm(**override_kwargs) -> LLMProvider:
    """
    Get LLM provider configured from environment.

    Environment variables:
        LLM_PROVIDER: Provider name (ollama, openai, anthropic)
        LLM_MODEL: Model name

    Returns:
        Configured LLMProvider instance
    """
    register_default_plugins()

    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    model = os.getenv("LLM_MODEL")

    kwargs = {}
    if model:
        kwargs["model"] = model
    kwargs.update(override_kwargs)

    return PluginRegistry.get_llm_provider(provider, **kwargs)


def get_configured_embedding(**override_kwargs) -> EmbeddingProvider:
    """
    Get embedding provider configured from environment.

    Environment variables:
        EMBEDDING_PROVIDER: Provider name (huggingface)
        EMBEDDING_MODEL: Model name

    Returns:
        Configured EmbeddingProvider instance
    """
    register_default_plugins()

    provider = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
    model = os.getenv("EMBEDDING_MODEL")

    kwargs = {}
    if model:
        kwargs["model"] = model
    kwargs.update(override_kwargs)

    return PluginRegistry.get_embedding_provider(provider, **kwargs)


def get_configured_strategy(**override_kwargs) -> RetrievalStrategy:
    """
    Get retrieval strategy configured from environment.

    Environment variables:
        RETRIEVAL_STRATEGY: Strategy name (hybrid, semantic, keyword)

    Returns:
        Configured RetrievalStrategy instance
    """
    register_default_plugins()

    strategy = os.getenv("RETRIEVAL_STRATEGY", "hybrid").lower()
    return PluginRegistry.get_strategy(strategy, **override_kwargs)


def list_available_plugins() -> dict:
    """
    List all available plugins.

    Returns:
        Dictionary with plugin types and available options
    """
    register_default_plugins()
    return PluginRegistry.discover_plugins()


def get_plugin_info() -> dict:
    """
    Get detailed information about current configuration.

    Returns:
        Dictionary with current configuration and available options
    """
    register_default_plugins()

    return {
        "current_config": {
            "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
            "llm_model": os.getenv("LLM_MODEL", "default"),
            "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "huggingface"),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5"),
            "retrieval_strategy": os.getenv("RETRIEVAL_STRATEGY", "hybrid"),
        },
        "available_plugins": PluginRegistry.discover_plugins(),
        "registry_stats": PluginRegistry.get_registry_stats(),
    }
