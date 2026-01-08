"""
SQL Chat Service - Main orchestrator for Chat with Data feature.

Coordinates all components: connection management, schema introspection,
SQL generation, execution, and conversation memory.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms.llm import LLM

from dbnotebook.core.services.base import BaseService
from dbnotebook.core.sql_chat.confidence_scorer import ConfidenceScorer
from dbnotebook.core.sql_chat.connection import DatabaseConnectionManager
from dbnotebook.core.sql_chat.cost_estimator import QueryCostEstimator
from dbnotebook.core.sql_chat.data_masker import DataMasker
from dbnotebook.core.sql_chat.executor import SafeQueryExecutor
from dbnotebook.core.sql_chat.few_shot_retriever import FewShotRetriever
from dbnotebook.core.sql_chat.intent_classifier import IntentClassifier
from dbnotebook.core.sql_chat.memory import SQLChatMemory
from dbnotebook.core.sql_chat.query_engine import TextToSQLEngine
from dbnotebook.core.sql_chat.response_generator import ResponseGenerator
from dbnotebook.core.sql_chat.schema import SchemaIntrospector
from dbnotebook.core.sql_chat.semantic_inspector import SemanticInspector
from dbnotebook.core.sql_chat.telemetry import TelemetryLogger
from dbnotebook.core.sql_chat.types import (
    DatabaseConnection,
    DatabaseType,
    MaskingPolicy,
    QueryResult,
    QueryState,
    SchemaInfo,
    SQLChatSession,
)
from dbnotebook.core.sql_chat.validators import QueryValidator

logger = logging.getLogger(__name__)


class SQLChatService(BaseService):
    """Main service for Chat with Data feature.

    Orchestrates:
    - Database connection management
    - Schema introspection and caching
    - Text-to-SQL generation with LlamaIndex
    - Safe query execution with validation
    - Multi-turn conversation memory
    - Confidence scoring and telemetry
    """

    def __init__(
        self,
        pipeline,
        db_manager,
        notebook_manager,
        llm: Optional[LLM] = None,
        embed_model: Optional[BaseEmbedding] = None
    ):
        """Initialize SQL Chat Service.

        Args:
            pipeline: RAG pipeline (for LLM access)
            db_manager: Database manager for internal storage
            notebook_manager: Notebook manager (unused but required by base)
            llm: Optional LLM override
            embed_model: Optional embedding model override
        """
        super().__init__(pipeline, db_manager, notebook_manager)

        # Get LLM and embedding model
        self._llm = llm or pipeline.get_llm()
        self._embed_model = embed_model or pipeline.get_embed_model()

        # Initialize components (pass db_manager for persistent storage)
        self._connections = DatabaseConnectionManager(db_manager=db_manager)
        self._schema = SchemaIntrospector()
        self._validator = QueryValidator()
        self._executor = SafeQueryExecutor()
        self._cost_estimator = QueryCostEstimator()
        self._data_masker = DataMasker()
        self._intent_classifier = IntentClassifier()
        self._confidence_scorer = ConfidenceScorer()
        self._telemetry = TelemetryLogger(db_manager)
        self._response_generator = ResponseGenerator(self._llm)

        # Initialize few-shot retriever (will be None if not set up)
        try:
            self._few_shot_retriever = FewShotRetriever(db_manager, self._embed_model)
        except Exception:
            self._few_shot_retriever = None
            logger.warning("Few-shot retriever not available")

        # Query engine (initialized per connection)
        self._query_engine = TextToSQLEngine(
            llm=self._llm,
            embed_model=self._embed_model,
            validator=self._validator,
            few_shot_retriever=self._few_shot_retriever
        )

        # Session storage
        self._sessions: Dict[str, SQLChatSession] = {}
        self._session_memories: Dict[str, SQLChatMemory] = {}

        logger.info("SQLChatService initialized")

    # ========== Connection Management ==========

    def create_connection(
        self,
        user_id: str,
        name: str,
        db_type: DatabaseType,
        host: str,
        database: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        masking_policy: Optional[MaskingPolicy] = None
    ) -> Tuple[str, Optional[str]]:
        """Create and store a new database connection.

        Args:
            user_id: User ID
            name: Connection display name
            db_type: Database type (postgresql, mysql, sqlite)
            host: Database host
            database: Database name
            username: Database username
            password: Database password
            port: Optional port (uses default if not specified)
            masking_policy: Optional data masking configuration

        Returns:
            Tuple of (connection_id, error_message)
        """
        conn_id, error = self._connections.create_connection(
            user_id=user_id,
            name=name,
            db_type=db_type,
            host=host,
            database=database,
            username=username,
            password=password,
            port=port,
            masking_policy=masking_policy
        )

        if error:
            return "", error

        # Pre-load schema and create query engine
        try:
            engine = self._connections.get_engine(conn_id)
            if engine:
                schema = self._schema.introspect(engine, conn_id)
                self._query_engine.create_query_engine(conn_id, engine, schema)
        except Exception as e:
            logger.warning(f"Failed to pre-load schema: {e}")

        return conn_id, None

    def test_connection(
        self,
        db_type: DatabaseType,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str
    ) -> Tuple[bool, str]:
        """Test database connection.

        Args:
            db_type: Database type
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password

        Returns:
            Tuple of (success, message)
        """
        return self._connections.test_connection(
            db_type, host, port, database, username, password
        )

    def list_connections(self, user_id: str) -> List[DatabaseConnection]:
        """List all connections for a user.

        Args:
            user_id: User ID

        Returns:
            List of connections
        """
        return self._connections.list_connections(user_id)

    def delete_connection(self, connection_id: str) -> bool:
        """Delete a database connection.

        Args:
            connection_id: Connection to delete

        Returns:
            True if successful
        """
        # Clean up query engine
        self._query_engine.remove_query_engine(connection_id)
        self._schema.clear_cache(connection_id)
        self._connections.disconnect(connection_id)
        return True

    def get_schema(
        self,
        connection_id: str,
        force_refresh: bool = False
    ) -> Optional[SchemaInfo]:
        """Get database schema for connection.

        Args:
            connection_id: Connection ID
            force_refresh: Force cache refresh

        Returns:
            SchemaInfo or None
        """
        engine = self._connections.get_engine(connection_id)
        if not engine:
            return None

        return self._schema.introspect(engine, connection_id, force_refresh)

    # ========== Session Management ==========

    def create_session(
        self,
        user_id: str,
        connection_id: str
    ) -> Tuple[str, Optional[str]]:
        """Create a new SQL chat session.

        Args:
            user_id: User ID
            connection_id: Database connection ID

        Returns:
            Tuple of (session_id, error_message)
        """
        # Verify connection exists
        conn = self._connections.get_connection(connection_id)
        if not conn:
            return "", "Connection not found"

        # Get schema
        engine = self._connections.get_engine(connection_id)
        schema = self._schema.introspect(engine, connection_id) if engine else None

        # Ensure query engine is created
        if not self._query_engine.has_query_engine(connection_id):
            if engine and schema:
                self._query_engine.create_query_engine(connection_id, engine, schema)

        session_id = str(uuid.uuid4())
        session = SQLChatSession(
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            schema=schema,
            status="pending",
            created_at=datetime.utcnow(),
        )

        self._sessions[session_id] = session
        self._session_memories[session_id] = SQLChatMemory()

        logger.info(f"Created SQL chat session {session_id} for connection {connection_id}")
        return session_id, None

    def get_session(self, session_id: str) -> Optional[SQLChatSession]:
        """Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            SQLChatSession or None
        """
        return self._sessions.get(session_id)

    # ========== Query Execution ==========

    async def execute_query(
        self,
        session_id: str,
        nl_query: str
    ) -> QueryResult:
        """Execute a natural language query.

        Full pipeline:
        1. Validate user input
        2. Classify intent
        3. Generate SQL (with few-shot)
        4. Estimate cost
        5. Execute with semantic inspection
        6. Apply data masking
        7. Compute confidence
        8. Log telemetry

        Args:
            session_id: Session ID
            nl_query: Natural language query

        Returns:
            QueryResult
        """
        session = self._sessions.get(session_id)
        if not session:
            return QueryResult(
                success=False,
                sql_generated="",
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error_message="Session not found"
            )

        # Update session status
        session.status = "generating"

        # Step 1: Validate user input
        is_valid, error = self._validator.validate_user_input(nl_query)
        if not is_valid:
            return QueryResult(
                success=False,
                sql_generated="",
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error_message=error
            )

        # Step 2: Check if this is a refinement
        memory = self._session_memories.get(session_id)
        if memory and memory.is_follow_up(nl_query):
            return await self._execute_refinement(session, nl_query, memory)

        # Step 3: Classify intent
        session.status = "generating"
        intent = self._intent_classifier.classify(nl_query)

        try:
            # Step 4: Generate SQL
            sql, success, intent = self._query_engine.generate_with_correction(
                session.connection_id,
                nl_query,
                session.schema
            )

            if not success:
                return QueryResult(
                    success=False,
                    sql_generated=sql,
                    data=[],
                    columns=[],
                    row_count=0,
                    execution_time_ms=0,
                    error_message="Failed to generate valid SQL"
                )

            # Step 5: Estimate cost
            session.status = "validating"
            engine = self._connections.get_engine(session.connection_id)
            if engine:
                cost_estimate = self._cost_estimator.estimate(engine, sql)
                if cost_estimate:
                    is_safe, warning = self._cost_estimator.is_safe(cost_estimate)
                    if not is_safe:
                        return QueryResult(
                            success=False,
                            sql_generated=sql,
                            data=[],
                            columns=[],
                            row_count=0,
                            execution_time_ms=0,
                            error_message=warning,
                            cost_estimate=cost_estimate
                        )

            # Step 6: Execute with semantic inspection (pass schema for error correction)
            session.status = "executing"
            inspector = SemanticInspector(self._llm)

            def execute_fn(sql_to_run):
                return self._executor.execute_readonly(engine, sql_to_run)

            result, inspection_passed, retry_count = await inspector.execute_with_inspection(
                nl_query, sql, execute_fn, session.connection_id, schema=session.schema
            )

            # Step 7: Apply data masking
            conn = self._connections.get_connection(session.connection_id)
            if conn and conn.masking_policy and result.success:
                result.data = self._data_masker.apply(result.data, conn.masking_policy)

            # Step 8: Compute confidence
            query_terms = self._confidence_scorer.extract_query_terms(nl_query)
            result_columns = [c.name for c in result.columns]
            column_overlap = self._confidence_scorer.compute_column_overlap(query_terms, result_columns)

            # Get few-shot similarity if available
            few_shot_similarity = 0.5
            if self._few_shot_retriever:
                examples = self._few_shot_retriever.get_examples(nl_query, top_k=1)
                if examples:
                    few_shot_similarity = examples[0].similarity

            result.confidence = self._confidence_scorer.compute(
                table_relevance=0.7,  # Default - could be improved with actual retrieval scores
                few_shot_similarity=few_shot_similarity,
                retry_count=retry_count,
                column_intent_overlap=column_overlap
            )

            result.intent = intent

            # Step 9: Generate natural language explanation
            if result.success:
                column_names = [c.name for c in result.columns]
                result.explanation = self._response_generator.generate(
                    user_query=nl_query,
                    sql=result.sql_generated,
                    data=result.data,
                    columns=column_names,
                    row_count=result.row_count,
                    error_message=result.error_message
                )

            # Step 10: Log telemetry
            self._telemetry.log_from_result(
                session_id, nl_query, result, intent.intent.value
            )

            # Step 10: Update memory
            if memory:
                memory.add_exchange(nl_query, result.sql_generated, result)

            # Update session
            session.status = "complete"
            session.last_query_at = datetime.utcnow()
            session.query_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            session.status = "error"
            return QueryResult(
                success=False,
                sql_generated="",
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error_message=str(e)
            )

    async def _execute_refinement(
        self,
        session: SQLChatSession,
        refinement: str,
        memory: SQLChatMemory
    ) -> QueryResult:
        """Execute a query refinement.

        Args:
            session: Current session
            refinement: User's refinement instruction
            memory: Conversation memory

        Returns:
            QueryResult
        """
        previous_sql = memory.get_last_sql()
        if not previous_sql:
            # No previous SQL, treat as new query
            return await self.execute_query(session.session_id, refinement)

        logger.info(f"Refining previous SQL: {refinement}")

        # Generate refined SQL
        refined_sql = self._query_engine.refine_sql(
            session.connection_id,
            previous_sql,
            refinement,
            session.schema
        )

        # Execute refined query
        engine = self._connections.get_engine(session.connection_id)
        if not engine:
            return QueryResult(
                success=False,
                sql_generated=refined_sql,
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error_message="Connection not available"
            )

        result = self._executor.execute_readonly(engine, refined_sql)

        # Apply masking
        conn = self._connections.get_connection(session.connection_id)
        if conn and conn.masking_policy and result.success:
            result.data = self._data_masker.apply(result.data, conn.masking_policy)

        # Generate natural language explanation
        if result.success:
            column_names = [c.name for c in result.columns]
            result.explanation = self._response_generator.generate(
                user_query=refinement,
                sql=result.sql_generated,
                data=result.data,
                columns=column_names,
                row_count=result.row_count,
                error_message=result.error_message
            )

        # Update memory
        memory.add_exchange(refinement, refined_sql, result)

        return result

    def get_query_history(self, session_id: str) -> List[QueryResult]:
        """Get query history for session.

        Args:
            session_id: Session ID

        Returns:
            List of QueryResult
        """
        session = self._sessions.get(session_id)
        return session.query_history if session else []

    # ========== Utilities ==========

    def get_schema_formatted(
        self,
        connection_id: str
    ) -> str:
        """Get formatted schema for display.

        Args:
            connection_id: Connection ID

        Returns:
            Formatted schema string
        """
        schema = self.get_schema(connection_id)
        if not schema:
            return "Schema not available"

        return self._schema.format_for_llm(schema)

    def get_accuracy_metrics(
        self,
        days: int = 30,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get accuracy metrics from telemetry.

        Args:
            days: Days of history
            session_id: Optional session filter

        Returns:
            Metrics dict
        """
        return self._telemetry.get_accuracy_metrics(days, session_id)

    def get_default_port(self, db_type: DatabaseType) -> int:
        """Get default port for database type.

        Args:
            db_type: Database type

        Returns:
            Default port
        """
        return self._connections.get_default_port(db_type)

    def parse_connection_string(
        self,
        connection_string: str
    ) -> Tuple[Optional[dict], str]:
        """Parse connection string into components.

        Args:
            connection_string: Connection string

        Returns:
            Tuple of (parsed_config, error_message)
        """
        return self._connections.parse_connection_string(connection_string)

    def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        self._connections.close_all()
        logger.info("SQLChatService cleaned up")
