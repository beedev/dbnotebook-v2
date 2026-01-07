"""
Text-to-SQL Query Engine for Chat with Data.

Uses LlamaIndex's SQLTableRetrieverQueryEngine for large schemas
and NLSQLTableQueryEngine for small schemas.
Integrates few-shot learning, intent classification, and semantic inspection.
"""

import logging
from typing import Dict, List, Optional, Tuple

from llama_index.core import SQLDatabase, VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.indices.struct_store import (
    NLSQLTableQueryEngine,
    SQLTableRetrieverQueryEngine,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from sqlalchemy.engine import Engine

from dbnotebook.core.sql_chat.few_shot_retriever import FewShotRetriever
from dbnotebook.core.sql_chat.intent_classifier import IntentClassifier
from dbnotebook.core.sql_chat.types import (
    FewShotExample,
    IntentClassification,
    QueryResult,
    SchemaInfo,
)
from dbnotebook.core.sql_chat.validators import QueryValidator

logger = logging.getLogger(__name__)


class TextToSQLEngine:
    """Generate SQL from natural language using LlamaIndex Text-to-SQL.

    Features:
    - Automatic table selection for large schemas (>20 tables)
    - Few-shot learning with Gretel dataset
    - Intent classification for SQL shape optimization
    - Self-correction on syntax errors
    """

    TABLE_THRESHOLD = 20  # Use retriever for schemas with >20 tables
    MAX_CORRECTION_ATTEMPTS = 3

    def __init__(
        self,
        llm: LLM,
        embed_model: BaseEmbedding,
        validator: QueryValidator,
        few_shot_retriever: Optional[FewShotRetriever] = None,
        table_threshold: int = 20
    ):
        """Initialize Text-to-SQL engine.

        Args:
            llm: Language model for SQL generation
            embed_model: Embedding model for table retrieval
            validator: SQL query validator
            few_shot_retriever: Optional few-shot retriever for examples
            table_threshold: Threshold for switching to retriever-based engine
        """
        self._llm = llm
        self._embed_model = embed_model
        self._validator = validator
        self._few_shot_retriever = few_shot_retriever
        self._table_threshold = table_threshold
        self._intent_classifier = IntentClassifier()

        # Cache for query engines per connection
        self._query_engines: Dict[str, any] = {}
        self._sql_databases: Dict[str, SQLDatabase] = {}

    def create_query_engine(
        self,
        connection_id: str,
        engine: Engine,
        schema: SchemaInfo
    ) -> None:
        """Create appropriate query engine based on schema size.

        Args:
            connection_id: Connection ID for caching
            engine: SQLAlchemy engine
            schema: Database schema info
        """
        # Create SQLDatabase
        sql_database = SQLDatabase(engine)
        self._sql_databases[connection_id] = sql_database

        table_count = len(schema.tables)
        logger.info(f"Creating query engine for {table_count} tables")

        if table_count <= self._table_threshold:
            # Small schema: Use simple NLSQLTableQueryEngine
            logger.info("Using NLSQLTableQueryEngine (small schema)")
            query_engine = NLSQLTableQueryEngine(
                sql_database=sql_database,
                llm=self._llm,
            )
        else:
            # Large schema: Use retriever-based engine
            logger.info("Using SQLTableRetrieverQueryEngine (large schema)")

            # Create table schema objects with context
            table_node_mapping = SQLTableNodeMapping(sql_database)
            table_schema_objs = [
                SQLTableSchema(
                    table_name=t.name,
                    context_str=self._get_table_context(t)
                )
                for t in schema.tables
            ]

            # Create object index for table retrieval
            obj_index = ObjectIndex.from_objects(
                table_schema_objs,
                table_node_mapping,
                VectorStoreIndex,
                embed_model=self._embed_model,
            )

            query_engine = SQLTableRetrieverQueryEngine(
                sql_database,
                obj_index.as_retriever(similarity_top_k=5),
                llm=self._llm,
            )

        self._query_engines[connection_id] = query_engine
        logger.info(f"Query engine created for connection {connection_id}")

    def _get_table_context(self, table) -> str:
        """Generate context string for a table.

        Args:
            table: TableInfo object

        Returns:
            Context string for table selection
        """
        cols = ", ".join([f"{c.name} ({c.type})" for c in table.columns])
        row_info = f" ~{table.row_count:,} rows" if table.row_count else ""
        return f"Table: {table.name}.{row_info} Columns: {cols}"

    def generate_sql(
        self,
        connection_id: str,
        nl_query: str,
        schema: Optional[SchemaInfo] = None,
        include_few_shot: bool = True
    ) -> Tuple[str, str, IntentClassification]:
        """Generate SQL from natural language query.

        Args:
            connection_id: Connection ID
            nl_query: Natural language query
            schema: Optional schema for few-shot domain inference
            include_few_shot: Whether to include few-shot examples

        Returns:
            Tuple of (sql_query, natural_response, intent)
        """
        query_engine = self._query_engines.get(connection_id)
        if not query_engine:
            raise ValueError(f"No query engine for connection {connection_id}")

        # Classify intent
        intent = self._intent_classifier.classify(nl_query)
        logger.debug(f"Intent: {intent.intent.value} (confidence: {intent.confidence})")

        # Build enhanced prompt
        enhanced_query = self._build_enhanced_query(
            nl_query, intent, schema, include_few_shot
        )

        # Generate SQL via LlamaIndex
        try:
            response = query_engine.query(enhanced_query)

            # Extract SQL from response
            sql = response.metadata.get("sql_query", "")
            natural_response = str(response)

            logger.debug(f"Generated SQL: {sql[:100]}...")
            return sql, natural_response, intent

        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise

    def _build_enhanced_query(
        self,
        nl_query: str,
        intent: IntentClassification,
        schema: Optional[SchemaInfo] = None,
        include_few_shot: bool = True
    ) -> str:
        """Build enhanced query with few-shot examples and hints.

        Args:
            nl_query: Original user query
            intent: Classified intent
            schema: Optional schema for domain inference
            include_few_shot: Whether to include few-shot examples

        Returns:
            Enhanced query string
        """
        parts = []

        # Add few-shot examples if available
        if include_few_shot and self._few_shot_retriever:
            # Infer domain from schema if available
            domain = None
            if schema:
                schema_text = " ".join([t.name for t in schema.tables])
                domain = self._few_shot_retriever.infer_domain(schema_text)

            examples = self._few_shot_retriever.get_examples(
                nl_query, top_k=5, domain_hint=domain
            )
            if examples:
                few_shot_prompt = self._few_shot_retriever.format_for_prompt(examples)
                parts.append(few_shot_prompt)

        # Add intent hints
        if intent.prompt_hints:
            parts.append(f"\nSQL Generation Hints: {intent.prompt_hints}")

        # Add the actual query
        parts.append(f"\nUser Question: {nl_query}")

        return "\n".join(parts)

    def generate_with_correction(
        self,
        connection_id: str,
        nl_query: str,
        schema: Optional[SchemaInfo] = None
    ) -> Tuple[str, bool, IntentClassification]:
        """Generate SQL with automatic retry on syntax errors.

        Args:
            connection_id: Connection ID
            nl_query: Natural language query
            schema: Optional schema

        Returns:
            Tuple of (sql, success, intent)
        """
        sql, _, intent = self.generate_sql(connection_id, nl_query, schema)

        for attempt in range(self.MAX_CORRECTION_ATTEMPTS):
            is_valid, error = self._validator.validate_generated_sql(sql, schema)

            if is_valid:
                return sql, True, intent

            # Try to correct
            logger.info(f"Attempt {attempt + 1}: Correcting SQL - {error}")
            sql = self._correct_sql(nl_query, sql, error)

        # Return last attempt
        return sql, False, intent

    def _correct_sql(self, nl_query: str, sql: str, error: str) -> str:
        """Ask LLM to correct SQL based on validation error.

        Args:
            nl_query: Original query
            sql: Current SQL
            error: Error message

        Returns:
            Corrected SQL
        """
        prompt = f"""The following SQL query has an issue:

Original question: {nl_query}

SQL query:
{sql}

Error: {error}

Generate a corrected SQL query. Return ONLY the SQL, no explanation.
"""
        try:
            response = self._llm.complete(prompt)
            corrected = response.text.strip()

            # Remove markdown code blocks if present
            if "```sql" in corrected:
                import re
                match = re.search(r'```sql\s*(.*?)\s*```', corrected, re.DOTALL)
                if match:
                    corrected = match.group(1).strip()
            elif "```" in corrected:
                import re
                match = re.search(r'```\s*(.*?)\s*```', corrected, re.DOTALL)
                if match:
                    corrected = match.group(1).strip()

            return corrected

        except Exception as e:
            logger.error(f"SQL correction failed: {e}")
            return sql

    def refine_sql(
        self,
        connection_id: str,
        previous_sql: str,
        refinement: str,
        schema: Optional[SchemaInfo] = None
    ) -> str:
        """Refine previous SQL based on user's modification request.

        Args:
            connection_id: Connection ID
            previous_sql: Previous SQL query
            refinement: User's refinement instruction
            schema: Optional schema

        Returns:
            Modified SQL query
        """
        prompt = f"""Modify the following SQL query based on the user's request.

Previous SQL:
{previous_sql}

User's modification request: {refinement}

Generate the modified SQL query. Return ONLY the SQL, no explanation.
"""
        try:
            response = self._llm.complete(prompt)
            modified = response.text.strip()

            # Clean up
            if "```" in modified:
                import re
                match = re.search(r'```(?:sql)?\s*(.*?)\s*```', modified, re.DOTALL)
                if match:
                    modified = match.group(1).strip()

            return modified

        except Exception as e:
            logger.error(f"SQL refinement failed: {e}")
            return previous_sql

    def explain_sql(self, sql: str) -> str:
        """Generate natural language explanation of SQL query.

        Args:
            sql: SQL query to explain

        Returns:
            Natural language explanation
        """
        prompt = f"""Explain the following SQL query in simple terms:

{sql}

Provide a brief, clear explanation of what this query does.
"""
        try:
            response = self._llm.complete(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"SQL explanation failed: {e}")
            return "Unable to generate explanation"

    def has_query_engine(self, connection_id: str) -> bool:
        """Check if query engine exists for connection.

        Args:
            connection_id: Connection ID

        Returns:
            True if query engine exists
        """
        return connection_id in self._query_engines

    def remove_query_engine(self, connection_id: str) -> None:
        """Remove query engine for connection.

        Args:
            connection_id: Connection ID
        """
        self._query_engines.pop(connection_id, None)
        self._sql_databases.pop(connection_id, None)
