"""Transformation Service for generating AI transformations from documents.

Generates:
- Dense Summary: Comprehensive 300-500 word summary
- Key Insights: 5-10 actionable takeaways
- Reflection Questions: 5-7 thought-provoking questions

Uses the user's selected LLM (privacy-first design).
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from llama_index.core import Settings
from llama_index.core.llms import LLM

from .prompts import (
    DENSE_SUMMARY_PROMPT,
    KEY_INSIGHTS_PROMPT,
    REFLECTION_QUESTIONS_PROMPT,
    DENSE_SUMMARY_CHUNK_PROMPT,
    COMBINE_SUMMARIES_PROMPT,
)

logger = logging.getLogger(__name__)

# Maximum characters to send to LLM in a single call
MAX_CHARS_PER_CALL = 8000
# Maximum characters before using chunked processing
CHUNK_THRESHOLD = 10000


@dataclass
class TransformationResult:
    """Result of document transformation."""
    dense_summary: Optional[str] = None
    key_insights: Optional[List[str]] = None
    reflection_questions: Optional[List[str]] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if transformation was successful."""
        return self.error is None and (
            self.dense_summary is not None or
            self.key_insights is not None or
            self.reflection_questions is not None
        )


class TransformationService:
    """Generates AI transformations for documents.

    Uses the user's currently selected LLM for privacy-first design:
    - Ollama users: Transformations run locally
    - Cloud users: Uses their API key
    """

    def __init__(self, llm: Optional[LLM] = None):
        """Initialize with optional LLM override.

        Args:
            llm: Optional LLM to use. If None, uses Settings.llm (user's current selection)
        """
        self._llm = llm

    @property
    def llm(self) -> LLM:
        """Get the LLM to use for transformations."""
        return self._llm or Settings.llm

    async def generate_all(
        self,
        document_text: str,
        generate_summary: bool = True,
        generate_insights: bool = True,
        generate_questions: bool = True,
    ) -> TransformationResult:
        """Generate all enabled transformations for a document.

        Args:
            document_text: Full text of the document
            generate_summary: Whether to generate dense summary
            generate_insights: Whether to generate key insights
            generate_questions: Whether to generate reflection questions

        Returns:
            TransformationResult with generated transformations
        """
        if not document_text or not document_text.strip():
            return TransformationResult(error="Empty document text")

        tasks = []
        task_names = []

        if generate_summary:
            tasks.append(self._generate_summary(document_text))
            task_names.append("summary")

        if generate_insights:
            tasks.append(self._generate_insights(document_text))
            task_names.append("insights")

        if generate_questions:
            tasks.append(self._generate_questions(document_text))
            task_names.append("questions")

        if not tasks:
            return TransformationResult(error="No transformations enabled")

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            result = TransformationResult()
            errors = []

            for i, (name, res) in enumerate(zip(task_names, results)):
                if isinstance(res, Exception):
                    errors.append(f"{name}: {str(res)}")
                    logger.error(f"Error generating {name}: {res}")
                else:
                    if name == "summary":
                        result.dense_summary = res
                    elif name == "insights":
                        result.key_insights = res
                    elif name == "questions":
                        result.reflection_questions = res

            if errors and not result.success:
                result.error = "; ".join(errors)

            return result

        except Exception as e:
            logger.error(f"Error in generate_all: {e}")
            return TransformationResult(error=str(e))

    async def _generate_summary(self, text: str) -> str:
        """Generate dense summary using chunked processing if needed."""
        if len(text) <= CHUNK_THRESHOLD:
            return await self._call_llm(
                DENSE_SUMMARY_PROMPT.format(text=text[:MAX_CHARS_PER_CALL])
            )
        else:
            # Chunked processing for long documents
            return await self._generate_chunked_summary(text)

    async def _generate_chunked_summary(self, text: str) -> str:
        """Generate summary by processing chunks and combining."""
        chunks = self._split_into_chunks(text, MAX_CHARS_PER_CALL)

        # Generate summary for each chunk
        chunk_tasks = [
            self._call_llm(DENSE_SUMMARY_CHUNK_PROMPT.format(text=chunk))
            for chunk in chunks
        ]
        chunk_summaries = await asyncio.gather(*chunk_tasks)

        # Combine chunk summaries
        combined_text = "\n\n---\n\n".join(chunk_summaries)
        return await self._call_llm(
            COMBINE_SUMMARIES_PROMPT.format(summaries=combined_text)
        )

    async def _generate_insights(self, text: str) -> List[str]:
        """Generate key insights from document."""
        response = await self._call_llm(
            KEY_INSIGHTS_PROMPT.format(text=text[:MAX_CHARS_PER_CALL])
        )
        return self._parse_numbered_list(response)

    async def _generate_questions(self, text: str) -> List[str]:
        """Generate reflection questions from document."""
        response = await self._call_llm(
            REFLECTION_QUESTIONS_PROMPT.format(text=text[:MAX_CHARS_PER_CALL])
        )
        return self._parse_numbered_list(response)

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM with a prompt and return the response."""
        try:
            # Use complete (not chat) for simple prompts
            response = await self.llm.acomplete(prompt)
            return str(response).strip()
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_numbered_list(self, text: str) -> List[str]:
        """Parse numbered list from LLM response.

        Handles formats like:
        1. Item one
        2. Item two

        Or:
        1) Item one
        2) Item two
        """
        lines = text.strip().split("\n")
        items = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match patterns like "1. ", "1) ", "- ", "* "
            match = re.match(r'^(?:\d+[\.\)]\s*|[-*]\s*)', line)
            if match:
                item = line[match.end():].strip()
                if item:
                    items.append(item)
            elif items:
                # Continuation of previous item (no number prefix)
                items[-1] += " " + line

        # If no numbered items found, try splitting by newlines
        if not items:
            items = [line.strip() for line in lines if line.strip()]

        return items

    def _split_into_chunks(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks, trying to break at sentence boundaries."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        current_pos = 0

        while current_pos < len(text):
            end_pos = current_pos + chunk_size

            if end_pos >= len(text):
                chunks.append(text[current_pos:])
                break

            # Try to find sentence boundary
            search_start = max(current_pos + chunk_size - 500, current_pos)
            segment = text[search_start:end_pos]

            # Look for sentence endings
            for delimiter in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                last_delim = segment.rfind(delimiter)
                if last_delim != -1:
                    end_pos = search_start + last_delim + len(delimiter)
                    break

            chunks.append(text[current_pos:end_pos])
            current_pos = end_pos

        return chunks


# Synchronous wrapper for non-async contexts
def generate_transformations_sync(
    document_text: str,
    llm: Optional[LLM] = None,
    generate_summary: bool = True,
    generate_insights: bool = True,
    generate_questions: bool = True,
) -> TransformationResult:
    """Synchronous wrapper for generating transformations.

    For use in non-async contexts (e.g., Flask routes without async support).
    """
    service = TransformationService(llm=llm)

    # Create event loop if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        service.generate_all(
            document_text,
            generate_summary=generate_summary,
            generate_insights=generate_insights,
            generate_questions=generate_questions,
        )
    )
