"""AI Transformations module for document processing.

Provides:
- TransformationService: Generates AI transformations (summaries, insights, questions)
- TransformationWorker: Background processor for async transformation jobs
- Prompt templates for transformation generation
"""

from .transformation_service import TransformationService, TransformationResult, generate_transformations_sync
from .worker import TransformationWorker, TransformationJob, process_source_transformations
from .prompts import DENSE_SUMMARY_PROMPT, KEY_INSIGHTS_PROMPT, REFLECTION_QUESTIONS_PROMPT

__all__ = [
    "TransformationService",
    "TransformationResult",
    "generate_transformations_sync",
    "TransformationWorker",
    "TransformationJob",
    "process_source_transformations",
    "DENSE_SUMMARY_PROMPT",
    "KEY_INSIGHTS_PROMPT",
    "REFLECTION_QUESTIONS_PROMPT",
]
