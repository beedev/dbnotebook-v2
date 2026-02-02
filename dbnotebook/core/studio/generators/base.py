"""Abstract base class for content generators."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class ContentGenerator(ABC):
    """
    Abstract base class for content generators.

    All content generators (infographic, mindmap, summary, etc.)
    must implement this interface.
    """

    @property
    @abstractmethod
    def content_type(self) -> str:
        """Get the content type identifier (e.g., 'infographic', 'mindmap')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the display name of this generator."""
        pass

    @abstractmethod
    def generate(
        self,
        content: str,
        prompt: Optional[str] = None,
        output_dir: Optional[Path] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate content from input text.

        Args:
            content: Source content/text to generate from
            prompt: Optional additional prompt/instructions
            output_dir: Directory to save generated files
            **kwargs: Generator-specific options

        Returns:
            Dictionary containing:
                - file_path: Path to generated file
                - thumbnail_path: Optional path to thumbnail
                - title: Generated title
                - metadata: Additional metadata
        """
        pass

    @abstractmethod
    def get_generator_info(self) -> Dict[str, Any]:
        """
        Get information about this generator.

        Returns:
            Dictionary with generator capabilities and settings
        """
        pass

    def validate(self) -> bool:
        """
        Validate generator configuration.

        Returns:
            True if generator is properly configured
        """
        try:
            info = self.get_generator_info()
            return info.get("available", False)
        except Exception:
            return False

    def build_prompt(
        self,
        content: str,
        user_prompt: Optional[str] = None,
    ) -> str:
        """
        Build the full generation prompt.

        Args:
            content: Source content
            user_prompt: Optional user-provided prompt

        Returns:
            Combined prompt string
        """
        base_prompt = self._get_base_prompt()

        # Combine prompts
        parts = [base_prompt]

        if user_prompt:
            parts.append(f"\nAdditional instructions: {user_prompt}")

        # Add content without "Source" label to avoid it appearing in generated image
        parts.append(f"\n\nCONTENT TO VISUALIZE (do not include this header in image):\n{content[:2000]}")

        return "\n".join(parts)

    @abstractmethod
    def _get_base_prompt(self) -> str:
        """Get the base prompt for this generator type."""
        pass
