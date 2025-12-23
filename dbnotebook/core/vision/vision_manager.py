"""Vision Manager for orchestrating vision providers."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..interfaces.vision import VisionProvider, VisionAnalysisResult
from ..providers.gemini_vision import GeminiVisionProvider
from ..providers.openai_vision import OpenAIVisionProvider

logger = logging.getLogger(__name__)


class VisionManager:
    """
    Manages vision providers for image understanding.

    Handles provider selection, fallback logic, and orchestration
    between multiple vision providers (OpenAI GPT-4V, Gemini Vision).
    """

    SUPPORTED_PROVIDERS = {
        "gemini": GeminiVisionProvider,
        "openai": OpenAIVisionProvider,
    }

    def __init__(
        self,
        default_provider: Optional[str] = None,
        enable_fallback: bool = True,
    ):
        """
        Initialize the Vision Manager.

        Args:
            default_provider: Default provider name (gemini or openai)
            enable_fallback: Enable fallback to other providers on failure
        """
        self._default_provider = default_provider or os.getenv(
            "VISION_PROVIDER", "gemini"
        )
        self._enable_fallback = enable_fallback
        self._providers: Dict[str, VisionProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize all available providers."""
        for name, provider_class in self.SUPPORTED_PROVIDERS.items():
            try:
                provider = provider_class()
                if provider.validate():
                    self._providers[name] = provider
                    logger.info(f"Vision provider '{name}' initialized successfully")
                else:
                    logger.debug(f"Vision provider '{name}' not available (validation failed)")
            except Exception as e:
                logger.debug(f"Could not initialize vision provider '{name}': {e}")

    def get_provider(self, name: Optional[str] = None) -> Optional[VisionProvider]:
        """
        Get a specific provider by name.

        Args:
            name: Provider name (defaults to default_provider)

        Returns:
            VisionProvider instance or None if not available
        """
        provider_name = name or self._default_provider
        return self._providers.get(provider_name)

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self._providers.keys())

    def analyze_image(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> VisionAnalysisResult:
        """
        Analyze an image using the specified or default provider.

        Args:
            image_path: Path to the image file
            prompt: Optional prompt to guide analysis
            provider: Provider name to use (uses default if not specified)
            **kwargs: Additional provider-specific options

        Returns:
            VisionAnalysisResult with description and text content

        Raises:
            RuntimeError: If no providers are available
        """
        # Validate image path
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Get provider preference order
        providers_to_try = self._get_provider_order(provider)

        if not providers_to_try:
            raise RuntimeError(
                "No vision providers available. "
                "Set GOOGLE_API_KEY or OPENAI_API_KEY environment variable."
            )

        last_error = None
        for provider_name in providers_to_try:
            vision_provider = self._providers.get(provider_name)
            if not vision_provider:
                continue

            try:
                logger.debug(f"Analyzing image with provider: {provider_name}")
                result = vision_provider.analyze_image(image_path, prompt, **kwargs)
                return result
            except Exception as e:
                logger.warning(f"Provider '{provider_name}' failed: {e}")
                last_error = e
                if not self._enable_fallback:
                    raise

        # All providers failed
        raise RuntimeError(
            f"All vision providers failed. Last error: {last_error}"
        )

    def extract_text(
        self,
        image_path: str,
        provider: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Extract text from an image using OCR.

        Args:
            image_path: Path to the image file
            provider: Provider name to use (uses default if not specified)
            **kwargs: Additional provider-specific options

        Returns:
            Extracted text content

        Raises:
            RuntimeError: If no providers are available
        """
        # Validate image path
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Get provider preference order
        providers_to_try = self._get_provider_order(provider)

        if not providers_to_try:
            raise RuntimeError(
                "No vision providers available. "
                "Set GOOGLE_API_KEY or OPENAI_API_KEY environment variable."
            )

        last_error = None
        for provider_name in providers_to_try:
            vision_provider = self._providers.get(provider_name)
            if not vision_provider:
                continue

            try:
                logger.debug(f"Extracting text with provider: {provider_name}")
                text = vision_provider.extract_text(image_path, **kwargs)
                return text
            except Exception as e:
                logger.warning(f"Provider '{provider_name}' text extraction failed: {e}")
                last_error = e
                if not self._enable_fallback:
                    raise

        # All providers failed
        raise RuntimeError(
            f"All vision providers failed for text extraction. Last error: {last_error}"
        )

    def _get_provider_order(self, preferred: Optional[str] = None) -> List[str]:
        """
        Get the order of providers to try.

        Args:
            preferred: Preferred provider name

        Returns:
            List of provider names in order of preference
        """
        providers = []

        # Add preferred provider first
        if preferred and preferred in self._providers:
            providers.append(preferred)

        # Add default provider if different from preferred
        if self._default_provider != preferred and self._default_provider in self._providers:
            providers.append(self._default_provider)

        # Add remaining providers for fallback
        if self._enable_fallback:
            for name in self._providers:
                if name not in providers:
                    providers.append(name)

        return providers

    def get_providers_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all providers.

        Returns:
            List of provider info dictionaries
        """
        info_list = []
        for name, provider in self._providers.items():
            info = provider.get_provider_info()
            info["is_default"] = name == self._default_provider
            info_list.append(info)

        # Add info for unavailable providers
        for name in self.SUPPORTED_PROVIDERS:
            if name not in self._providers:
                info_list.append({
                    "name": name,
                    "available": False,
                    "is_default": name == self._default_provider,
                })

        return info_list

    def is_available(self) -> bool:
        """Check if any vision provider is available."""
        return len(self._providers) > 0

    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats."""
        if self._providers:
            # Use the first available provider's formats
            provider = next(iter(self._providers.values()))
            return provider.get_supported_formats()
        return [".png", ".jpg", ".jpeg", ".gif", ".webp"]


# Singleton instance for easy access
_vision_manager: Optional[VisionManager] = None


def get_vision_manager() -> VisionManager:
    """
    Get the singleton VisionManager instance.

    Returns:
        VisionManager instance
    """
    global _vision_manager
    if _vision_manager is None:
        _vision_manager = VisionManager()
    return _vision_manager
