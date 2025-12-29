"""Contextual Retrieval Service for chunk enrichment.

Implements Anthropic's Contextual Retrieval approach:
- Enriches each chunk with LLM-generated context during ingestion
- Improves retrieval for structured content (tables, lists)
- Context describes what the chunk contains and its relevance

Reference: https://www.anthropic.com/news/contextual-retrieval
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

from llama_index.core import Settings
from llama_index.core.llms import LLM
from llama_index.core.schema import TextNode

logger = logging.getLogger(__name__)

# Maximum characters for chunk content in context generation
MAX_CHUNK_CHARS = 2000

# Prompt for generating contextual descriptions
CONTEXT_GENERATION_PROMPT = """Analyze this chunk from a document and generate a brief contextual description (1-2 sentences) that explains:
1. What type of content this chunk contains (narrative, table, list, etc.)
2. What specific information or entities are mentioned
3. How this relates to the document's subject

Document title: {doc_title}

Chunk content:
{chunk_text}

Contextual description (be specific about data types, entities, and relationships):"""

# Batch processing configuration
DEFAULT_BATCH_SIZE = 5
DEFAULT_CONCURRENCY = 3


@dataclass
class ContextEnrichmentResult:
    """Result of context enrichment for a chunk."""
    original_text: str
    context_prefix: str
    enriched_text: str
    success: bool
    error: Optional[str] = None


@dataclass
class BatchEnrichmentResult:
    """Result of batch context enrichment."""
    enriched_nodes: List[TextNode]
    success_count: int
    failure_count: int
    errors: List[str]


class ContextualRetrievalService:
    """Generates contextual enrichment for document chunks.

    Enriches chunks with LLM-generated context to improve retrieval:
    - Tables get descriptions of their structure and content
    - Lists get summaries of their items
    - Narrative text gets topic and entity mentions

    Uses the user's currently selected LLM for privacy-first design.
    """

    def __init__(
        self,
        llm: Optional[LLM] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_concurrency: int = DEFAULT_CONCURRENCY
    ):
        """Initialize the contextual retrieval service.

        Args:
            llm: Optional LLM to use. If None, uses Settings.llm
            batch_size: Number of chunks to process in each batch
            max_concurrency: Maximum concurrent LLM calls
        """
        self._llm = llm
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency

    @property
    def llm(self) -> LLM:
        """Get the LLM to use for context generation."""
        return self._llm or Settings.llm

    async def enrich_chunk(
        self,
        chunk: TextNode,
        doc_title: str
    ) -> ContextEnrichmentResult:
        """Enrich a single chunk with contextual prefix.

        Args:
            chunk: The chunk to enrich
            doc_title: Title/name of the source document

        Returns:
            ContextEnrichmentResult with enriched text
        """
        try:
            context = await self._generate_context(chunk.text, doc_title)

            # Prepend context to chunk
            enriched_text = f"{context}\n\n{chunk.text}"

            return ContextEnrichmentResult(
                original_text=chunk.text,
                context_prefix=context,
                enriched_text=enriched_text,
                success=True
            )
        except Exception as e:
            logger.error(f"Context generation failed for chunk: {e}")
            return ContextEnrichmentResult(
                original_text=chunk.text,
                context_prefix="",
                enriched_text=chunk.text,  # Return original on failure
                success=False,
                error=str(e)
            )

    async def enrich_chunks(
        self,
        chunks: List[TextNode],
        doc_title: str
    ) -> BatchEnrichmentResult:
        """Enrich multiple chunks with contextual prefixes.

        Processes chunks in batches with controlled concurrency.

        Args:
            chunks: List of chunks to enrich
            doc_title: Title/name of the source document

        Returns:
            BatchEnrichmentResult with enriched nodes
        """
        if not chunks:
            return BatchEnrichmentResult(
                enriched_nodes=[],
                success_count=0,
                failure_count=0,
                errors=[]
            )

        enriched_nodes = []
        errors = []
        success_count = 0
        failure_count = 0

        # Process in batches with semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_chunk(chunk: TextNode) -> TextNode:
            async with semaphore:
                result = await self.enrich_chunk(chunk, doc_title)

                if result.success:
                    # Create enriched node with updated text and metadata
                    enriched_node = TextNode(
                        text=result.enriched_text,
                        metadata={
                            **chunk.metadata,
                            "has_context": True,
                            "original_text": result.original_text,
                            "context_prefix": result.context_prefix
                        }
                    )
                    return enriched_node, True, None
                else:
                    # Return original chunk on failure
                    return chunk, False, result.error

        # Process all chunks concurrently (with semaphore limiting)
        tasks = [process_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                failure_count += 1
                errors.append(str(result))
            else:
                node, success, error = result
                enriched_nodes.append(node)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                    if error:
                        errors.append(error)

        logger.info(
            f"Context enrichment complete: {success_count} succeeded, "
            f"{failure_count} failed out of {len(chunks)} chunks"
        )

        return BatchEnrichmentResult(
            enriched_nodes=enriched_nodes,
            success_count=success_count,
            failure_count=failure_count,
            errors=errors
        )

    async def _generate_context(self, chunk_text: str, doc_title: str) -> str:
        """Generate contextual description for a chunk.

        Args:
            chunk_text: The text content of the chunk
            doc_title: Title of the source document

        Returns:
            Contextual description string
        """
        # Truncate chunk if too long
        truncated_text = chunk_text[:MAX_CHUNK_CHARS]
        if len(chunk_text) > MAX_CHUNK_CHARS:
            truncated_text += "..."

        prompt = CONTEXT_GENERATION_PROMPT.format(
            doc_title=doc_title,
            chunk_text=truncated_text
        )

        try:
            response = await self.llm.acomplete(prompt)
            context = str(response).strip()

            # Ensure context is not too long
            if len(context) > 500:
                context = context[:497] + "..."

            return context
        except Exception as e:
            logger.error(f"LLM context generation failed: {e}")
            raise


# Synchronous wrapper for non-async contexts
def enrich_chunks_sync(
    chunks: List[TextNode],
    doc_title: str,
    llm: Optional[LLM] = None,
) -> BatchEnrichmentResult:
    """Synchronous wrapper for chunk enrichment.

    For use in non-async contexts.
    """
    service = ContextualRetrievalService(llm=llm)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        service.enrich_chunks(chunks, doc_title)
    )
