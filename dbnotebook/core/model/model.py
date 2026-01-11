import logging
from typing import Optional

import requests
from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv

from ...setting import get_settings, RAGSettings

load_dotenv()

logger = logging.getLogger(__name__)

# Cache for LLM models to avoid re-initialization
_llm_cache: dict = {}


class LocalRAGModel:
    """Manages LLM model initialization and caching."""

    OPENAI_MODELS = {
        # GPT-3.5 and GPT-4 models
        "gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4.1",
        "gpt-4o-mini", "gpt-4-turbo-preview",
        "gpt-4-0125-preview", "gpt-4-1106-preview",  # GPT-4 Turbo versions
        "gpt-4o-2024-11-20", "gpt-4o-2024-08-06",     # GPT-4o versions
        # GPT-5 models (400K context)
        "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro",
        "gpt-5.1", "gpt-5.1-chat-latest",
        "gpt-5.2", "gpt-5.2-pro",
        # O-series reasoning models
        "o1", "o1-mini", "o1-preview",
        "o3", "o3-mini", "o4-mini"
    }
    CLAUDE_MODELS = {
        "claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022", "claude-3-opus-20240229"
    }
    GEMINI_MODELS = {
        "gemini-3-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash",
        "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"
    }

    @staticmethod
    def set(
        model_name: str = "",
        system_prompt: Optional[str] = None,
        host: str = "host.docker.internal",
        setting: RAGSettings | None = None
    ):
        """
        Get or create LLM model with caching.

        Args:
            model_name: Model name (uses settings default if empty)
            system_prompt: System prompt for the model
            host: Ollama host
            setting: RAGSettings instance

        Returns:
            LLM model instance
        """
        setting = setting or get_settings()
        model_name = model_name or setting.ollama.llm

        # Detect provider
        if model_name in LocalRAGModel.OPENAI_MODELS:
            provider = "openai"
        elif model_name in LocalRAGModel.CLAUDE_MODELS:
            provider = "claude"
        elif model_name in LocalRAGModel.GEMINI_MODELS:
            provider = "gemini"
        else:
            provider = "ollama"

        # Cache key includes provider and system prompt hash
        prompt_hash = hash(system_prompt) if system_prompt else "none"
        cache_key = f"{provider}_{model_name}_{prompt_hash}"

        # Check cache (but skip if system prompt changes)
        if cache_key in _llm_cache and system_prompt is None:
            logger.debug(f"Using cached LLM model: {model_name}")
            return _llm_cache[cache_key]

        # Create model based on provider
        if provider == "openai":
            model = OpenAI(
                model=model_name,
                temperature=setting.ollama.temperature
            )
        elif provider == "claude":
            from llama_index.llms.anthropic import Anthropic
            model = Anthropic(
                model=model_name,
                api_key=setting.anthropic.api_key,
                temperature=setting.anthropic.temperature,
                max_tokens=setting.anthropic.max_tokens
            )
        elif provider == "gemini":
            from llama_index.llms.gemini import Gemini
            # Gemini API requires model names to be prefixed with "models/"
            gemini_model_name = f"models/{model_name}" if not model_name.startswith("models/") else model_name
            model = Gemini(
                model=gemini_model_name,
                api_key=setting.gemini.api_key,
                temperature=setting.gemini.temperature,
                max_tokens=setting.gemini.max_output_tokens
            )
        else:
            # Create Ollama model
            additional_kwargs = {
                "tfs_z": setting.ollama.tfs_z,
                "top_k": setting.ollama.top_k,
                "top_p": setting.ollama.top_p,
                "repeat_last_n": setting.ollama.repeat_last_n,
                "repeat_penalty": setting.ollama.repeat_penalty,
            }

            model = Ollama(
                model=model_name,
                system_prompt=system_prompt,
                base_url=f"http://{host}:{setting.ollama.port}",
                temperature=setting.ollama.temperature,
                context_window=setting.ollama.context_window,
                request_timeout=setting.ollama.request_timeout,
                additional_kwargs=additional_kwargs
            )

        # Cache the model
        _llm_cache[cache_key] = model
        logger.debug(f"Created and cached {provider.upper()} model: {model_name}")

        return model

    @staticmethod
    def pull(host: str, model_name: str):
        """
        Pull LLM model from Ollama.

        Args:
            host: Ollama host
            model_name: Model to pull

        Returns:
            Response object from Ollama API
        """
        setting = get_settings()
        payload = {"name": model_name}
        url = f"http://{host}:{setting.ollama.port}/api/pull"

        try:
            return requests.post(url, json=payload, stream=True, timeout=30)
        except requests.RequestException as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            raise

    @staticmethod
    def check_model_exist(host: str, model_name: str) -> bool:
        """
        Check if LLM model exists on Ollama server.

        Args:
            host: Ollama host
            model_name: Model to check

        Returns:
            True if model exists, False otherwise
        """
        setting = get_settings()
        url = f"http://{host}:{setting.ollama.port}/api/tags"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            models = data.get("models")
            if not models:
                return False

            model_names = [m.get("name", "") for m in models]
            return model_name in model_names

        except requests.RequestException as e:
            logger.warning(f"Error checking model existence: {e}")
            return False
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Error parsing Ollama response: {e}")
            return False

    @staticmethod
    def clear_cache() -> None:
        """Clear the LLM model cache."""
        global _llm_cache
        _llm_cache.clear()
        logger.info("LLM model cache cleared")

    @staticmethod
    def list_available_models(host: str) -> list:
        """
        List available models on Ollama server.

        Args:
            host: Ollama host

        Returns:
            List of model names
        """
        setting = get_settings()
        url = f"http://{host}:{setting.ollama.port}/api/tags"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            models = data.get("models", [])
            return [m.get("name", "") for m in models if m.get("name")]

        except requests.RequestException as e:
            logger.warning(f"Error listing models: {e}")
            return []
