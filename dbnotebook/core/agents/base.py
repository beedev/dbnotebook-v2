"""Base class for all agentic features."""

from abc import ABC, abstractmethod
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agentic features in DBNotebook.

    Provides common infrastructure for:
    - LLM integration via pipeline
    - Stateless, composable design
    - Dependency injection for testability
    """

    def __init__(self, pipeline=None, config: Optional[dict] = None):
        """
        Initialize agent with pipeline and configuration.

        Args:
            pipeline: LocalRAGPipeline instance for LLM access
            config: Optional configuration dictionary
        """
        self.pipeline = pipeline
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def analyze(self, input_data: Any) -> dict:
        """
        Analyze input and return insights.

        Args:
            input_data: Input to analyze (type varies by agent)

        Returns:
            Dictionary containing analysis results
        """
        pass

    @abstractmethod
    def suggest(self, context: dict) -> list[dict]:
        """
        Generate suggestions based on context.

        Args:
            context: Context information for generating suggestions

        Returns:
            List of suggestion dictionaries
        """
        pass

    def execute(self, action: str, params: dict) -> dict:
        """
        Execute a suggested action. Override in subclasses.

        Args:
            action: Action type to execute
            params: Parameters for the action

        Returns:
            Dictionary containing execution results

        Raises:
            NotImplementedError: If action is not implemented by subclass
        """
        raise NotImplementedError(
            f"Action '{action}' not implemented by {self.__class__.__name__}"
        )

    def _get_llm_response(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Get LLM response for analysis.

        Uses the pipeline's configured LLM for consistency with the rest
        of the application.

        Args:
            prompt: Prompt text for the LLM
            max_tokens: Maximum tokens in response (currently unused,
                       controlled by LLM settings)

        Returns:
            LLM response text

        Raises:
            RuntimeError: If pipeline is not configured
        """
        if not self.pipeline:
            raise RuntimeError("Pipeline not configured for this agent")

        try:
            # Use the pipeline's LLM for consistency
            llm = self.pipeline._default_model
            response = llm.complete(prompt)
            return str(response).strip()
        except Exception as e:
            self.logger.error(f"Error getting LLM response: {e}")
            raise
