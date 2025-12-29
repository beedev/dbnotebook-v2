"""Multi-notebook query service for cross-notebook retrieval.

This service enables querying across multiple notebooks simultaneously,
aggregating results and providing unified answers with clear source attribution.
"""

import logging
from typing import Iterator, Dict, Any, Optional, List, Tuple

from llama_index.core.schema import BaseNode, QueryBundle
from llama_index.core import Settings

from .base import BaseService


logger = logging.getLogger(__name__)


class MultiNotebookService(BaseService):
    """Service for querying across multiple notebooks.

    Enables cross-notebook retrieval with source attribution and
    unified answer generation. Useful for finding information
    across multiple document collections.
    """

    def query_multiple(
        self,
        query: str,
        notebook_ids: List[str],
        user_id: Optional[str] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """Query across multiple notebooks and aggregate results.

        Retrieves relevant chunks from each specified notebook,
        aggregates them by relevance score, and generates a unified
        answer that synthesizes information from all sources.

        Args:
            query: User query text
            notebook_ids: List of notebook UUIDs to search
            user_id: Optional user UUID for access control
            top_k: Maximum number of results per notebook (default: 10)

        Returns:
            Dictionary containing:
            - answer: Unified answer synthesizing all sources
            - sources: List of source chunks with attribution
            - notebook_coverage: Per-notebook relevance metrics

        Example:
            >>> result = service.query_multiple(
            ...     query="How do we implement authentication?",
            ...     notebook_ids=["nb-uuid-1", "nb-uuid-2"],
            ...     top_k=10
            ... )
            >>> print(result['answer'])
            >>> for source in result['sources']:
            ...     print(f"{source['notebook_name']}: {source['content']}")
        """
        if not query or not query.strip():
            return {
                "error": "Query cannot be empty",
                "answer": "",
                "sources": [],
                "notebook_coverage": {}
            }

        if not notebook_ids:
            return {
                "error": "No notebooks specified",
                "answer": "",
                "sources": [],
                "notebook_coverage": {}
            }

        self._log_operation(
            "query_multiple",
            query_length=len(query),
            notebook_count=len(notebook_ids),
            user_id=user_id,
            top_k=top_k
        )

        all_sources = []
        notebook_names = {}

        # Query each notebook
        for nb_id in notebook_ids:
            try:
                # Get notebook name for attribution
                if self.notebook_manager:
                    notebook = self.notebook_manager.get_notebook(nb_id)
                    notebook_names[nb_id] = notebook.name if notebook else nb_id
                else:
                    notebook_names[nb_id] = nb_id

                # Retrieve from this notebook
                nodes_with_scores = self._retrieve_from_notebook(
                    query=query,
                    notebook_id=nb_id,
                    top_k=top_k
                )

                # Format results with full attribution
                for node, score in nodes_with_scores:
                    metadata = node.metadata or {}
                    all_sources.append({
                        "notebook_id": nb_id,
                        "notebook_name": notebook_names.get(nb_id, nb_id),
                        "source_id": metadata.get("source_id", ""),
                        "filename": metadata.get("file_name", "Unknown"),
                        "content": node.text[:500],  # Limit excerpt length
                        "score": score,
                        "page": metadata.get("page"),
                        "section": metadata.get("section")
                    })

                self.logger.debug(
                    f"Retrieved {len(nodes_with_scores)} results from notebook {nb_id}"
                )

            except Exception as e:
                self.logger.warning(f"Failed to query notebook {nb_id}: {e}")
                # Continue with other notebooks rather than failing
                continue

        if not all_sources:
            return {
                "answer": "No relevant information found across the selected notebooks.",
                "sources": [],
                "notebook_coverage": {}
            }

        # Sort by relevance score and limit to top_k
        all_sources.sort(key=lambda x: x["score"], reverse=True)
        top_sources = all_sources[:top_k]

        self.logger.info(
            f"Aggregated {len(all_sources)} total results, "
            f"selected top {len(top_sources)}"
        )

        # Generate unified answer using top sources
        answer = self._generate_unified_answer(query, top_sources)

        # Calculate coverage metrics per notebook
        coverage = self._calculate_notebook_coverage(top_sources)

        return {
            "answer": answer,
            "sources": top_sources,
            "notebook_coverage": coverage
        }

    def _retrieve_from_notebook(
        self,
        query: str,
        notebook_id: str,
        top_k: int
    ) -> List[Tuple[BaseNode, float]]:
        """Retrieve nodes from a specific notebook.

        Uses the pipeline's retriever to perform semantic search
        within the specified notebook's documents.

        Args:
            query: Search query
            notebook_id: Notebook UUID to search within
            top_k: Maximum results to return

        Returns:
            List of (node, score) tuples sorted by relevance
        """
        try:
            # Load nodes for this notebook only
            vector_store = self.pipeline._vector_store
            if not vector_store:
                self.logger.warning("Vector store not available")
                return []

            nodes = vector_store.get_nodes_by_notebook_sql(notebook_id)
            if not nodes:
                self.logger.debug(f"No nodes found for notebook {notebook_id}")
                return []

            self.logger.debug(
                f"Loaded {len(nodes)} nodes for notebook {notebook_id}"
            )

            # Get the retriever (hybrid by default)
            retriever = self.pipeline._engine._retriever.get_retrievers(
                llm=Settings.llm,
                language="eng",
                nodes=nodes,
                offering_filter=[notebook_id],  # Filter by notebook
                vector_store=vector_store
            )

            # Perform retrieval
            query_bundle = QueryBundle(query_str=query)
            retrieval_results = retriever.retrieve(query_bundle)

            # Convert to (node, score) tuples
            results = [
                (result.node, result.score or 0.0)
                for result in retrieval_results[:top_k]
            ]

            return results

        except Exception as e:
            self.logger.error(
                f"Error retrieving from notebook {notebook_id}: {e}",
                exc_info=True
            )
            return []

    def _generate_unified_answer(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """Generate unified answer from multiple sources.

        Creates a prompt with context from all relevant sources
        and uses the LLM to synthesize a comprehensive answer.

        Args:
            query: Original user query
            sources: List of source dictionaries with content and metadata

        Returns:
            Synthesized answer text
        """
        if not sources:
            return "No relevant information found across the selected notebooks."

        # Build context from top sources (limit to prevent token overflow)
        context_parts = []
        for i, source in enumerate(sources[:5], 1):
            context_parts.append(
                f"[{i}] From {source['notebook_name']} ({source['filename']}):\n"
                f"{source['content']}"
            )
        context = "\n\n".join(context_parts)

        # Create synthesis prompt
        prompt = f"""Based on the following information from multiple notebooks, answer the question comprehensively.

Context:
{context}

Question: {query}

Provide a comprehensive answer that synthesizes information from all relevant sources.
Cite sources using [1], [2], etc. to indicate which notebook/document the information comes from.
If sources provide different perspectives, acknowledge them in your answer."""

        try:
            # Use the pipeline's LLM to generate answer
            llm = self.pipeline._default_model
            response = llm.complete(prompt)

            answer = response.text.strip()
            self.logger.info(
                f"Generated unified answer ({len(answer)} chars) "
                f"from {len(sources)} sources"
            )
            return answer

        except Exception as e:
            self.logger.error(f"Failed to generate unified answer: {e}")
            return (
                f"Found {len(sources)} relevant sources but failed to "
                f"generate unified answer. Please try again."
            )

    def _calculate_notebook_coverage(
        self,
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate coverage metrics per notebook.

        Analyzes which notebooks contributed to the results
        and their relative relevance.

        Args:
            sources: List of source dictionaries

        Returns:
            Dictionary mapping notebook_id to metrics:
            - hits: Number of results from this notebook
            - relevance: Average relevance score
        """
        coverage = {}

        for source in sources:
            nb_id = source["notebook_id"]

            if nb_id not in coverage:
                coverage[nb_id] = {
                    "hits": 0,
                    "total_score": 0.0,
                    "notebook_name": source["notebook_name"]
                }

            coverage[nb_id]["hits"] += 1
            coverage[nb_id]["total_score"] += source["score"]

        # Calculate average relevance
        for nb_id in coverage:
            hits = coverage[nb_id]["hits"]
            coverage[nb_id]["relevance"] = (
                coverage[nb_id]["total_score"] / hits if hits > 0 else 0.0
            )
            # Remove temporary total_score
            del coverage[nb_id]["total_score"]

        return coverage

    def get_queryable_notebooks(
        self,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of notebooks available for querying.

        Returns notebooks that have at least one document,
        making them suitable for cross-notebook search.

        Args:
            user_id: Optional user UUID for filtering

        Returns:
            List of notebook dictionaries with:
            - id: Notebook UUID
            - name: Notebook name
            - document_count: Number of documents
        """
        if not self.notebook_manager:
            self.logger.warning("Notebook manager not available")
            return []

        # Use default user_id if not provided
        effective_user_id = user_id or "00000000-0000-0000-0000-000000000001"

        try:
            notebooks = self.notebook_manager.list_notebooks(user_id=effective_user_id)

            queryable = [
                {
                    "id": nb["id"],
                    "name": nb["name"],
                    "document_count": nb["document_count"]
                }
                for nb in notebooks
                if nb["document_count"] > 0  # Only notebooks with documents
            ]

            self.logger.info(
                f"Found {len(queryable)} queryable notebooks "
                f"(total: {len(notebooks)})"
            )

            return queryable

        except Exception as e:
            self.logger.error(f"Error listing queryable notebooks: {e}")
            return []
