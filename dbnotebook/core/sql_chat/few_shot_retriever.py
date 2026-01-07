"""
Few-Shot Retriever for Chat with Data.

Retrieves similar SQL examples from local PGVectorStore for few-shot prompting.
Supports domain filtering for improved relevance.
"""

import logging
from typing import List, Optional

from dbnotebook.core.sql_chat.types import FewShotExample

logger = logging.getLogger(__name__)


class FewShotRetriever:
    """Retrieve similar SQL examples from local PGVectorStore.

    Uses vector similarity search to find relevant examples from the
    Gretel dataset for few-shot prompting. Supports:
    - Pure similarity search
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

    def get_examples(
        self,
        query: str,
        top_k: int = 5,
        domain_hint: Optional[str] = None,
        complexity_hint: Optional[str] = None,
    ) -> List[FewShotExample]:
        """Retrieve similar SQL examples by vector search.

        Args:
            query: User's natural language query
            top_k: Number of examples to retrieve
            domain_hint: Optional domain to filter by (e.g., "finance", "healthcare")
            complexity_hint: Optional complexity to filter by

        Returns:
            List of FewShotExample sorted by similarity
        """
        try:
            # Embed the query
            query_embedding = self._embed_model.get_text_embedding(query)

            # Build SQL with optional filters
            if domain_hint:
                sql = """
                    SELECT id, sql_prompt, sql_query, sql_context, complexity, domain,
                           1 - (embedding <=> :embedding) as similarity
                    FROM sql_few_shot_examples
                    WHERE domain = :domain OR domain = 'general'
                    ORDER BY embedding <=> :embedding
                    LIMIT :limit
                """
                params = {
                    "embedding": query_embedding,
                    "domain": domain_hint.lower(),
                    "limit": top_k,
                }
            elif complexity_hint:
                sql = """
                    SELECT id, sql_prompt, sql_query, sql_context, complexity, domain,
                           1 - (embedding <=> :embedding) as similarity
                    FROM sql_few_shot_examples
                    WHERE complexity = :complexity
                    ORDER BY embedding <=> :embedding
                    LIMIT :limit
                """
                params = {
                    "embedding": query_embedding,
                    "complexity": complexity_hint,
                    "limit": top_k,
                }
            else:
                sql = """
                    SELECT id, sql_prompt, sql_query, sql_context, complexity, domain,
                           1 - (embedding <=> :embedding) as similarity
                    FROM sql_few_shot_examples
                    ORDER BY embedding <=> :embedding
                    LIMIT :limit
                """
                params = {
                    "embedding": query_embedding,
                    "limit": top_k,
                }

            with self._db_manager.get_session() as session:
                result = session.execute(sql, params)
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
                f"Retrieved {len(examples)} few-shot examples "
                f"(domain={domain_hint}, complexity={complexity_hint})"
            )
            return examples

        except Exception as e:
            logger.warning(f"Few-shot retrieval failed: {e}")
            return []

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
                    "SELECT DISTINCT domain FROM sql_few_shot_examples ORDER BY domain"
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
                    """
                    SELECT id, sql_prompt, sql_query, sql_context, complexity, domain
                    FROM sql_few_shot_examples
                    WHERE id = :id
                    """,
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
                    """
                    SELECT id, sql_prompt, sql_query, sql_context, complexity, domain
                    FROM sql_few_shot_examples
                    WHERE UPPER(sql_query) LIKE :pattern
                    LIMIT :limit
                    """,
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
