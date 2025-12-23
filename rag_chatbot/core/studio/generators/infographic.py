"""Infographic generator using Gemini/Imagen."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base import ContentGenerator
from ...providers.gemini_image import GeminiImageProvider

logger = logging.getLogger(__name__)


class InfographicGenerator(ContentGenerator):
    """
    Generates infographics from notebook content using Gemini/Imagen.

    Uses the image generation capabilities to create visual summaries
    of notebook content.
    """

    def __init__(
        self,
        image_provider: Optional[GeminiImageProvider] = None,
        output_dir: Optional[str] = None,
    ):
        """
        Initialize infographic generator.

        Args:
            image_provider: Gemini image provider instance
            output_dir: Directory for generated images
        """
        self._output_dir = Path(output_dir or "outputs/studio/infographics")
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize or use provided image provider
        if image_provider:
            self._image_provider = image_provider
        else:
            try:
                self._image_provider = GeminiImageProvider(
                    output_dir=str(self._output_dir)
                )
            except Exception as e:
                logger.warning(f"Could not initialize image provider: {e}")
                self._image_provider = None

    @property
    def content_type(self) -> str:
        return "infographic"

    @property
    def name(self) -> str:
        return "Infographic Generator"

    def generate(
        self,
        content: str,
        prompt: Optional[str] = None,
        output_dir: Optional[Path] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate an infographic from content.

        Args:
            content: Source content to visualize
            prompt: Optional additional instructions
            output_dir: Override output directory
            **kwargs: Additional options (aspect_ratio, etc.)

        Returns:
            Dictionary with file_path, title, metadata
        """
        if not self._image_provider:
            raise RuntimeError("Image provider not available. Check GOOGLE_API_KEY.")

        target_dir = output_dir or self._output_dir

        # Build the generation prompt
        full_prompt = self.build_prompt(content, prompt)

        # Get aspect ratio (default to 16:9 for infographics)
        aspect_ratio = kwargs.get("aspect_ratio", "16:9")

        try:
            # Generate the image
            generated_paths = self._image_provider.generate(
                prompt=full_prompt,
                num_images=1,
                aspect_ratio=aspect_ratio,
            )

            if not generated_paths:
                raise RuntimeError("No images generated")

            file_path = generated_paths[0]

            # Generate a title from the content
            title = self._generate_title(content)

            logger.info(f"Generated infographic: {file_path}")

            return {
                "file_path": file_path,
                "thumbnail_path": file_path,  # Use same image as thumbnail
                "title": title,
                "metadata": {
                    "aspect_ratio": aspect_ratio,
                    "generator": self.name,
                    "model": self._image_provider._model if self._image_provider else None,
                    "prompt_used": full_prompt[:500],
                },
            }

        except Exception as e:
            logger.error(f"Infographic generation failed: {e}")
            raise RuntimeError(f"Failed to generate infographic: {e}") from e

    def get_generator_info(self) -> Dict[str, Any]:
        """Get information about this generator."""
        return {
            "content_type": self.content_type,
            "name": self.name,
            "available": self._image_provider is not None,
            "supported_aspect_ratios": ["16:9", "4:3", "1:1", "9:16"],
            "description": "Creates visual infographics from text content",
            "output_format": "png",
        }

    def _get_base_prompt(self) -> str:
        """Get the base prompt for infographic generation."""
        return """Create a professional, visually appealing infographic that summarizes the key points from the following content.

Design guidelines:
- Use a clean, modern design with clear hierarchy
- Include relevant icons and visual elements
- Use a cohesive color scheme
- Make the text readable and well-organized
- Highlight the most important information
- Include section headers for different topics
- Use charts or diagrams where appropriate

The infographic should be informative, easy to understand at a glance, and visually engaging."""

    def _generate_title(self, content: str) -> str:
        """Generate a title from the content."""
        # Simple title generation: use first sentence or first N words
        first_line = content.split('\n')[0].strip()
        if len(first_line) > 50:
            words = first_line.split()[:8]
            first_line = ' '.join(words) + '...'
        return f"Infographic: {first_line}" if first_line else "Generated Infographic"
