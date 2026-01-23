"""
Few-Shot Retriever for Chat with Data.

Retrieves similar SQL examples from local PGVectorStore for few-shot prompting.
Supports:
- Pure vector similarity search (default)
- Hybrid BM25+vector search with optional reranking (RAG integration)
- Domain and complexity filtering
"""

import logging
import os
from typing import List, Optional

from sqlalchemy import text

from dbnotebook.core.config import get_config_value
from dbnotebook.core.sql_chat.types import FewShotExample

logger = logging.getLogger(__name__)


def _get_rag_config() -> dict:
    """Get RAG integration configuration.

    Environment variables:
    - SQL_RERANKER_MODEL: Override reranker model for SQL Chat (e.g., "base", "xsmall")
    """
    # SQL_RERANKER_MODEL env var allows separate model for SQL Chat
    env_model = os.getenv("SQL_RERANKER_MODEL", "").strip()
    config_model = get_config_value("sql_chat", "few_shot", "rag_integration", "rerank_model",
                                    default="mixedbread-ai/mxbai-rerank-base-v1")
    rerank_model = env_model if env_model else config_model

    return {
        "enabled": get_config_value("sql_chat", "few_shot", "rag_integration", "enabled", default=True),
        "use_reranker": get_config_value("sql_chat", "few_shot", "rag_integration", "use_reranker", default=True),
        "rerank_model": rerank_model,
        "rerank_top_k": get_config_value("sql_chat", "few_shot", "rag_integration", "rerank_top_k", default=15),
        "bm25_weight": get_config_value("sql_chat", "few_shot", "rag_integration", "weights", "bm25", default=0.3),
        "vector_weight": get_config_value("sql_chat", "few_shot", "rag_integration", "weights", "vector", default=0.7),
    }


class FewShotRetriever:
    """Retrieve similar SQL examples from local PGVectorStore.

    Uses vector similarity search to find relevant examples from the
    Gretel dataset for few-shot prompting. Supports:
    - Pure similarity search (fallback)
    - Hybrid BM25+vector search with optional reranking (RAG integration)
    - Domain-filtered search (e.g., only finance examples)
    - Complexity-filtered search
    """

    DEFAULT_TOP_K = 5

    def __init__(
        self,
        db_manager,
        embed_model,
    ):
        """Initialize few-shot retriever.

        Args:
            db_manager: Database manager for PGVectorStore access
            embed_model: Embedding model for query embedding
        """
        self._db_manager = db_manager
        self._embed_model = embed_model
        self._examples_available: Optional[bool] = None  # Cache availability check
        self._rag_config = _get_rag_config()
        self._reranker = None

        # Initialize reranker if enabled
        # Uses dedicated reranker if SQL_RERANKER_MODEL is set, otherwise shared
        if self._rag_config["enabled"] and self._rag_config["use_reranker"]:
            try:
                sql_model = os.getenv("SQL_RERANKER_MODEL", "").strip()
                rag_model = os.getenv("RERANKER_MODEL", "").strip()

                if sql_model and sql_model != rag_model:
                    # Create dedicated reranker for SQL Chat (different from RAG)
                    from dbnotebook.core.providers.reranker_provider import resolve_model_path
                    from llama_index.core.postprocessor import SentenceTransformerRerank
                    resolved = resolve_model_path(sql_model)
                    logger.info(f"SQL Chat using dedicated reranker: {resolved}")
                    self._reranker = SentenceTransformerRerank(model=resolved, top_n=self.DEFAULT_TOP_K)
                else:
                    # Use shared reranker (same model as RAG)
                    from dbnotebook.core.providers.reranker_provider import get_shared_reranker
                    self._reranker = get_shared_reranker(
                        model=self._rag_config["rerank_model"],
                        top_n=self.DEFAULT_TOP_K,
                    )
                    logger.info(f"Few-shot using shared reranker: {self._rag_config['rerank_model']}")
            except Exception as e:
                logger.warning(f"Failed to initialize reranker: {e}. Using hybrid search without reranking.")
                self._reranker = None

    def _check_examples_available(self) -> bool:
        """Check if few-shot examples table exists and has data.

        Returns:
            True if examples are available, False otherwise
        """
        if self._examples_available is not None:
            return self._examples_available

        try:
            with self._db_manager.get_session() as session:
                # Check if table exists and has at least one row
                result = session.execute(
                    text("SELECT EXISTS (SELECT 1 FROM sql_few_shot_examples LIMIT 1)")
                )
                row = result.fetchone()
                self._examples_available = row[0] if row else False
        except Exception as e:
            # Table doesn't exist or other error
            logger.debug(f"Few-shot examples not available: {e}")
            self._examples_available = False

        return self._examples_available

    def _hybrid_search(
        self,
        query: str,
        query_embedding: list,
        top_k: int,
        domain_hint: Optional[str] = None,
        complexity_hint: Optional[str] = None,
    ) -> List[FewShotExample]:
        """Perform hybrid BM25+vector search.

        Uses PostgreSQL full-text search for keyword matching (BM25-like)
        combined with vector similarity for semantic matching.

        Args:
            query: User's natural language query
            query_embedding: Pre-computed query embedding
            top_k: Number of examples to retrieve
            domain_hint: Optional domain filter
            complexity_hint: Optional complexity filter

        Returns:
            List of FewShotExample with combined scores
        """
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        bm25_weight = self._rag_config["bm25_weight"]
        vector_weight = self._rag_config["vector_weight"]
        rerank_top_k = self._rag_config["rerank_top_k"] if self._reranker else top_k

        # Build hybrid search SQL
        # Uses PostgreSQL ts_rank for BM25-like ranking with full-text search
        # Combines with vector similarity using weighted average
        domain_filter = ""
        complexity_filter = ""
        params = {
            "embedding": embedding_str,
            "query": query,
            "bm25_weight": bm25_weight,
            "vector_weight": vector_weight,
            "limit": rerank_top_k,
        }

        if domain_hint:
            domain_filter = "AND (domain = :domain OR domain = 'general')"
            params["domain"] = domain_hint.lower()

        if complexity_hint:
            complexity_filter = "AND complexity = :complexity"
            params["complexity"] = complexity_hint

        sql = f"""
            WITH scored AS (
                SELECT
                    id,
                    sql_prompt,
                    sql_query,
                    sql_context,
                    complexity,
                    domain,
                    -- BM25-like score using PostgreSQL full-text search
                    ts_rank(
                        to_tsvector('english', sql_prompt || ' ' || COALESCE(sql_query, '')),
                        plainto_tsquery('english', :query)
                    ) as bm25_score,
                    -- Vector similarity score (cosine similarity)
                    1 - (embedding <=> CAST(:embedding AS vector)) as vector_score
                FROM sql_few_shot_examples
                WHERE embedding IS NOT NULL
                {domain_filter}
                {complexity_filter}
            )
            SELECT
                id,
                sql_prompt,
                sql_query,
                sql_context,
                complexity,
                domain,
                bm25_score,
                vector_score,
                -- Combined hybrid score using weighted average
                -- Normalize BM25 score (typically 0-1 range with ts_rank)
                (LEAST(bm25_score, 1.0) * :bm25_weight + vector_score * :vector_weight) as similarity
            FROM scored
            ORDER BY similarity DESC
            LIMIT :limit
        """

        try:
            with self._db_manager.get_session() as session:
                result = session.execute(text(sql), params)
                examples = []
                for row in result:
                    examples.append(FewShotExample(
                        id=row.id,
                        sql_prompt=row.sql_prompt,
                        sql_query=row.sql_query,
                        sql_context=row.sql_context,
                        complexity=row.complexity,
                        domain=row.domain,
                        similarity=row.similarity,
                    ))

                logger.debug(
                    f"Hybrid search retrieved {len(examples)} examples "
                    f"(bm25_w={bm25_weight}, vector_w={vector_weight})"
                )
                return examples

        except Exception as e:
            logger.warning(f"Hybrid search failed: {e}. Falling back to vector-only search.")
            return []

    def _rerank_examples(
        self,
        query: str,
        examples: List[FewShotExample],
        top_k: int
    ) -> List[FewShotExample]:
        """Rerank examples using cross-encoder model.

        Args:
            query: Original query for reranking
            examples: Examples to rerank
            top_k: Number of examples to return after reranking

        Returns:
            Reranked list of examples
        """
        if not self._reranker or not examples:
            return examples[:top_k]

        try:
            from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle

            # Convert examples to NodeWithScore for reranker
            nodes = []
            for ex in examples:
                node = TextNode(
                    text=f"Question: {ex.sql_prompt}\nSQL: {ex.sql_query}",
                    id_=str(ex.id),
                    metadata={"example_id": ex.id}
                )
                nodes.append(NodeWithScore(node=node, score=ex.similarity))

            # Rerank using cross-encoder
            query_bundle = QueryBundle(query_str=query)
            self._reranker.top_n = top_k
            reranked_nodes = self._reranker.postprocess_nodes(nodes, query_bundle)

            # Map back to examples with updated scores
            example_map = {str(ex.id): ex for ex in examples}
            reranked_examples = []
            for i, node_with_score in enumerate(reranked_nodes):
                example_id = node_with_score.node.metadata.get("example_id") or node_with_score.node.id_
                if str(example_id) in example_map:
                    example = example_map[str(example_id)]
                    # Update similarity with reranker score
                    reranked_examples.append(FewShotExample(
                        id=example.id,
                        sql_prompt=example.sql_prompt,
                        sql_query=example.sql_query,
                        sql_context=example.sql_context,
                        complexity=example.complexity,
                        domain=example.domain,
                        similarity=node_with_score.score or (1.0 - i * 0.05),  # Fallback score
                    ))

            logger.debug(f"Reranked {len(examples)} → {len(reranked_examples)} examples")
            return reranked_examples

        except Exception as e:
            logger.warning(f"Reranking failed: {e}. Using hybrid scores.")
            return examples[:top_k]

    def get_examples(
        self,
        query: str,
        top_k: int = 5,
        domain_hint: Optional[str] = None,
        complexity_hint: Optional[str] = None,
    ) -> List[FewShotExample]:
        """Retrieve similar SQL examples using hybrid search with optional reranking.

        When RAG integration is enabled:
        1. Performs hybrid BM25+vector search for better keyword coverage
        2. Optionally reranks results using cross-encoder for precision

        Args:
            query: User's natural language query
            top_k: Number of examples to retrieve
            domain_hint: Optional domain to filter by (e.g., "finance", "healthcare")
            complexity_hint: Optional complexity to filter by

        Returns:
            List of FewShotExample sorted by similarity
        """
        # Early return if no examples available (avoids unnecessary embedding computation)
        if not self._check_examples_available():
            logger.debug("No few-shot examples available, skipping retrieval")
            return []

        try:
            # Embed the query
            query_embedding = self._embed_model.get_text_embedding(query)

            # Use hybrid search if RAG integration is enabled
            if self._rag_config["enabled"]:
                examples = self._hybrid_search(
                    query=query,
                    query_embedding=query_embedding,
                    top_k=top_k,
                    domain_hint=domain_hint,
                    complexity_hint=complexity_hint,
                )

                # Fallback to vector-only if hybrid search failed
                if not examples:
                    examples = self._vector_only_search(
                        query_embedding=query_embedding,
                        top_k=top_k,
                        domain_hint=domain_hint,
                        complexity_hint=complexity_hint,
                    )

                # Apply reranking if enabled and we have a reranker
                if self._reranker and examples:
                    examples = self._rerank_examples(query, examples, top_k)

                return examples

            # Fallback to vector-only search
            return self._vector_only_search(
                query_embedding=query_embedding,
                top_k=top_k,
                domain_hint=domain_hint,
                complexity_hint=complexity_hint,
            )

        except Exception as e:
            logger.warning(f"Few-shot retrieval failed: {e}")
            return []

    def _vector_only_search(
        self,
        query_embedding: list,
        top_k: int,
        domain_hint: Optional[str] = None,
        complexity_hint: Optional[str] = None,
    ) -> List[FewShotExample]:
        """Original vector-only similarity search (fallback).

        Args:
            query_embedding: Pre-computed query embedding
            top_k: Number of examples to retrieve
            domain_hint: Optional domain filter
            complexity_hint: Optional complexity filter

        Returns:
            List of FewShotExample sorted by similarity
        """
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Build SQL with optional filters
        if domain_hint:
            sql = """
                SELECT id, sql_prompt, sql_query, sql_context, complexity, domain,
                       1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM sql_few_shot_examples
                WHERE domain = :domain OR domain = 'general'
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """
            params = {
                "embedding": embedding_str,
                "domain": domain_hint.lower(),
                "limit": top_k,
            }
        elif complexity_hint:
            sql = """
                SELECT id, sql_prompt, sql_query, sql_context, complexity, domain,
                       1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM sql_few_shot_examples
                WHERE complexity = :complexity
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """
            params = {
                "embedding": embedding_str,
                "complexity": complexity_hint,
                "limit": top_k,
            }
        else:
            sql = """
                SELECT id, sql_prompt, sql_query, sql_context, complexity, domain,
                       1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM sql_few_shot_examples
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """
            params = {
                "embedding": embedding_str,
                "limit": top_k,
            }

        with self._db_manager.get_session() as session:
            result = session.execute(text(sql), params)
            examples = []
            for row in result:
                examples.append(FewShotExample(
                    id=row.id,
                    sql_prompt=row.sql_prompt,
                    sql_query=row.sql_query,
                    sql_context=row.sql_context,
                    complexity=row.complexity,
                    domain=row.domain,
                    similarity=row.similarity,
                ))

        logger.debug(
            f"Vector search retrieved {len(examples)} few-shot examples "
            f"(domain={domain_hint}, complexity={complexity_hint})"
        )
        return examples

    def format_for_prompt(
        self,
        examples: List[FewShotExample],
        include_context: bool = False
    ) -> str:
        """Format examples as few-shot prompt section.

        Args:
            examples: List of examples to format
            include_context: Whether to include sql_context

        Returns:
            Formatted string for LLM prompt
        """
        if not examples:
            return ""

        lines = ["Here are some similar SQL examples for reference:"]
        lines.append("")

        for i, ex in enumerate(examples, 1):
            lines.append(f"Example {i}:")
            lines.append(f"Question: {ex.sql_prompt}")
            lines.append(f"SQL: {ex.sql_query}")
            if include_context and ex.sql_context:
                lines.append(f"Context: {ex.sql_context}")
            lines.append("")

        return "\n".join(lines)

    def infer_domain(self, schema_text: str) -> Optional[str]:
        """Infer domain from schema table/column names.

        Args:
            schema_text: Text representation of schema

        Returns:
            Inferred domain or None
        """
        schema_lower = schema_text.lower()

        # Domain keyword mappings
        domain_keywords = {
            "finance": ["account", "transaction", "balance", "payment", "invoice",
                       "ledger", "credit", "debit", "revenue", "expense"],
            "healthcare": ["patient", "diagnosis", "prescription", "doctor",
                          "hospital", "medical", "treatment", "appointment"],
            "retail": ["product", "order", "customer", "inventory", "cart",
                      "purchase", "sale", "item", "catalog", "price"],
            "hr": ["employee", "salary", "department", "hiring", "payroll",
                  "leave", "attendance", "performance", "position"],
            "education": ["student", "course", "grade", "enrollment", "teacher",
                         "class", "assignment", "semester", "degree"],
            "ecommerce": ["order", "product", "customer", "shipping", "review",
                         "category", "wishlist", "checkout"],
            "logistics": ["shipment", "warehouse", "delivery", "tracking",
                         "route", "carrier", "package", "freight"],
        }

        # Score each domain
        scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for kw in keywords if kw in schema_lower)
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)

        return None

    def get_best_similarity(self, examples: List[FewShotExample]) -> float:
        """Get the best similarity score from retrieved examples.

        Args:
            examples: List of retrieved examples

        Returns:
            Best similarity score (0-1), or 0 if no examples
        """
        if not examples:
            return 0.0
        return max(ex.similarity for ex in examples)

    def get_available_domains(self) -> List[str]:
        """Get list of available domains in the database.

        Returns:
            List of domain names
        """
        try:
            with self._db_manager.get_session() as session:
                result = session.execute(
                    text("SELECT DISTINCT domain FROM sql_few_shot_examples ORDER BY domain")
                )
                return [row.domain for row in result if row.domain]
        except Exception:
            return []

    def get_example_by_id(self, example_id: int) -> Optional[FewShotExample]:
        """Get a specific example by ID.

        Args:
            example_id: Example ID

        Returns:
            FewShotExample or None
        """
        try:
            with self._db_manager.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT id, sql_prompt, sql_query, sql_context, complexity, domain
                    FROM sql_few_shot_examples
                    WHERE id = :id
                    """),
                    {"id": example_id}
                )
                row = result.fetchone()
                if row:
                    return FewShotExample(
                        id=row.id,
                        sql_prompt=row.sql_prompt,
                        sql_query=row.sql_query,
                        sql_context=row.sql_context,
                        complexity=row.complexity,
                        domain=row.domain,
                        similarity=0.0,
                    )
        except Exception:
            pass
        return None

    def search_by_sql_pattern(
        self,
        pattern: str,
        limit: int = 10
    ) -> List[FewShotExample]:
        """Search examples by SQL pattern (for debugging/analysis).

        Args:
            pattern: SQL pattern to search for (e.g., "GROUP BY")
            limit: Max results

        Returns:
            List of matching examples
        """
        try:
            with self._db_manager.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT id, sql_prompt, sql_query, sql_context, complexity, domain
                    FROM sql_few_shot_examples
                    WHERE UPPER(sql_query) LIKE :pattern
                    LIMIT :limit
                    """),
                    {"pattern": f"%{pattern.upper()}%", "limit": limit}
                )
                return [
                    FewShotExample(
                        id=row.id,
                        sql_prompt=row.sql_prompt,
                        sql_query=row.sql_query,
                        sql_context=row.sql_context,
                        complexity=row.complexity,
                        domain=row.domain,
                        similarity=0.0,
                    )
                    for row in result
                ]
        except Exception:
            return []
