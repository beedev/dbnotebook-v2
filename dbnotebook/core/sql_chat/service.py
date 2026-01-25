"""
SQL Chat Service - Main orchestrator for Chat with Data feature.

Coordinates all components: connection management, schema introspection,
SQL generation, execution, and conversation memory.
"""

import asyncio
import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
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
from dbnotebook.core.sql_chat.dictionary_generator import DictionaryGenerator
from dbnotebook.core.sql_chat.schema_linker import SchemaLinker
from dbnotebook.core.sql_chat.result_validator import ResultValidator
from dbnotebook.core.sql_chat.query_decomposer import QueryDecomposer
from dbnotebook.core.sql_chat.query_learner import QueryLearner

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

        # Store pipeline for dynamic LLM access
        self._pipeline = pipeline

        # Get embedding model (stable across requests)
        # NOTE: LLM is now retrieved per-request for multi-user safety
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
        # Response generator uses per-request LLM via _get_current_llm()
        self._response_generator = None  # Created per-request

        # Initialize few-shot retriever (will be None if not set up)
        try:
            self._few_shot_retriever = FewShotRetriever(db_manager, self._embed_model)
        except Exception:
            self._few_shot_retriever = None
            logger.warning("Few-shot retriever not available")

        # Query engine (initialized per connection, uses per-request LLM)
        self._query_engine = TextToSQLEngine(
            llm=None,  # Will use per-request LLM
            embed_model=self._embed_model,
            validator=self._validator,
            few_shot_retriever=self._few_shot_retriever
        )

        # New components for enhanced SQL Chat
        self._dictionary_generator = DictionaryGenerator()
        self._schema_linker = SchemaLinker(self._embed_model)
        self._result_validator = ResultValidator()
        # Query decomposer uses per-request LLM
        self._query_decomposer = None  # Created per-request
        self._query_learner = QueryLearner(db_manager, notebook_manager)

        # Session storage
        self._sessions: Dict[str, SQLChatSession] = {}
        self._session_memories: Dict[str, SQLChatMemory] = {}

        # Schema fingerprints for smart caching
        self._schema_fingerprints: Dict[str, str] = {}  # connection_id -> fingerprint

        # Dictionary generation threads (session_id -> Thread)
        self._dictionary_threads: Dict[str, threading.Thread] = {}

        # Dedicated GPT-4.1 LLM for SQL generation (lazy initialization)
        self._sql_llm: Optional[LLM] = None

        logger.info("SQLChatService initialized with enhanced components")

    def _get_current_llm(self) -> LLM:
        """Get GPT-4.1 LLM for SQL generation.

        SQL Chat uses GPT-4.1 specifically for accurate SQL generation,
        regardless of the main pipeline LLM configuration. This ensures
        consistent SQL quality with the 1M token context window.

        Returns:
            GPT-4.1 LLM instance
        """
        if self._sql_llm is None:
            import os
            from llama_index.llms.openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set, falling back to pipeline LLM")
                return self._pipeline.get_llm()

            self._sql_llm = OpenAI(
                model="gpt-4.1",
                api_key=api_key,
                temperature=0.0,  # Deterministic for SQL generation
                context_window=1000000,  # GPT-4.1 supports 1M context
            )
            logger.info("SQL Chat using dedicated GPT-4.1 LLM (context_window: 1,000,000)")

        return self._sql_llm

    def _get_response_generator(self, llm: LLM) -> ResponseGenerator:
        """Get response generator with given LLM.

        Per-request creation ensures multi-user safety.
        """
        return ResponseGenerator(llm)

    def _get_query_decomposer(self, llm: LLM) -> QueryDecomposer:
        """Get query decomposer with given LLM.

        Per-request creation ensures multi-user safety.
        """
        return QueryDecomposer(llm)

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
        schema: Optional[str] = None,
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
            schema: Optional PostgreSQL schema(s) e.g., 'public' or 'sales,hr'
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
            schema=schema,
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
        password: str,
        schema: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Test database connection.

        Args:
            db_type: Database type
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password
            schema: Optional PostgreSQL schema(s) e.g., 'public' or 'sales,hr'

        Returns:
            Tuple of (success, message)
        """
        return self._connections.test_connection(
            db_type, host, port, database, username, password, schema
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
        connection_id: str,
        force_refresh: bool = False,
        skip_schema_refresh: bool = False
    ) -> Tuple[str, Optional[str]]:
        """Create a new SQL chat session.

        Args:
            user_id: User ID
            connection_id: Database connection ID
            force_refresh: Force refresh schema cache (default False for performance)
            skip_schema_refresh: Skip schema introspection if already loaded (for performance
                when frontend already called get_schema via selectConnection)

        Returns:
            Tuple of (session_id, error_message)
        """
        # Verify connection exists
        conn = self._connections.get_connection(connection_id)
        if not conn:
            return "", "Connection not found"

        # Get engine
        engine = self._connections.get_engine(connection_id)
        if not engine:
            return "", "Failed to connect to database"

        # Fast path: skip schema refresh if already loaded by selectConnection
        if skip_schema_refresh and self._query_engine.has_query_engine(connection_id):
            # Use cached schema from query engine
            schema = self._schema.get_cached_schema(connection_id)
            if schema:
                logger.info(f"Skipping schema refresh for {connection_id} (skip_schema_refresh=True)")
            else:
                # Fallback: load schema if cache miss
                schema = self._schema.introspect(engine, connection_id, force_refresh=False)
        else:
            # Check if we can reuse cached query engine (fingerprint-based)
            current_fp = self._schema.get_fingerprint(engine)
            cached_fp = self._schema_fingerprints.get(connection_id)

            # Reuse existing query engine if schema unchanged
            if (not force_refresh and
                cached_fp == current_fp and
                current_fp and
                self._query_engine.has_query_engine(connection_id)):
                logger.info(f"Reusing cached query engine for {connection_id} (fingerprint match)")
                schema = self._schema.get_cached_schema(connection_id) or \
                         self._schema.introspect(engine, connection_id, force_refresh=False)
            else:
                # Need to refresh schema and/or recreate query engine
                if force_refresh or cached_fp != current_fp:
                    logger.info(f"Schema changed or force refresh for {connection_id}, refreshing")

                schema = self._schema.introspect(engine, connection_id, force_refresh=force_refresh)

                if schema:
                    self._query_engine.remove_query_engine(connection_id)
                    self._query_engine.create_query_engine(connection_id, engine, schema)
                    self._schema_fingerprints[connection_id] = current_fp

        session_id = str(uuid.uuid4())
        session = SQLChatSession(
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            schema=schema,
            status="generating_dictionary",  # Start in dictionary generation state
            created_at=datetime.utcnow(),
        )

        self._sessions[session_id] = session
        self._session_memories[session_id] = SQLChatMemory()

        # Trigger dictionary generation in background thread
        def run_dictionary_generation():
            asyncio.run(self._generate_dictionary_async(session_id))

        thread = threading.Thread(
            target=run_dictionary_generation,
            name=f"dict-gen-{session_id[:8]}",
            daemon=True
        )
        self._dictionary_threads[session_id] = thread
        thread.start()

        logger.info(f"Created SQL chat session {session_id} for connection {connection_id}")
        return session_id, None

    def get_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[SQLChatSession]:
        """Get session by ID with optional user validation.

        Multi-user safe: If user_id is provided, validates that the session
        belongs to that user. Returns None if access is denied.

        Args:
            session_id: Session ID
            user_id: Optional user ID for access validation

        Returns:
            SQLChatSession or None (if not found or access denied)
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        # Multi-user access control
        if user_id is not None and session.user_id != user_id:
            logger.warning(f"User {user_id} attempted to access session {session_id} owned by {session.user_id}")
            return None

        return session

    def validate_session_access(self, session_id: str, user_id: str) -> bool:
        """Validate that a user has access to a session.

        Args:
            session_id: Session ID to check
            user_id: User ID requesting access

        Returns:
            True if access is allowed, False otherwise
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
        return session.user_id == user_id

    def refresh_session_schema(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Refresh schema for an existing session.

        Forces reload of database schema and recreates query engine.
        Use this when database schema has changed.

        Multi-user safe: If user_id is provided, validates session access.

        Args:
            session_id: Session ID
            user_id: Optional user ID for access validation

        Returns:
            Tuple of (success, message)
        """
        session = self.get_session(session_id, user_id)
        if not session:
            return False, "Session not found"

        connection_id = session.connection_id
        engine = self._connections.get_engine(connection_id)
        if not engine:
            return False, "Connection not available"

        # Force refresh schema from database
        schema = self._schema.introspect(engine, connection_id, force_refresh=True)

        # Recreate query engine with fresh schema
        self._query_engine.remove_query_engine(connection_id)
        self._query_engine.create_query_engine(connection_id, engine, schema)

        # Update session with new schema
        session.schema = schema

        table_count = len(schema.tables) if schema else 0
        column_count = sum(len(t.columns) for t in schema.tables) if schema else 0
        logger.info(f"Refreshed schema for session {session_id}: {table_count} tables, {column_count} columns")

        return True, f"Schema refreshed: {table_count} tables, {column_count} columns"

    # ========== Query Execution ==========

    async def execute_query(
        self,
        session_id: str,
        nl_query: str,
        user_id: Optional[str] = None,
        **query_settings
    ) -> QueryResult:
        """Execute a natural language query.

        Multi-user safe: If user_id is provided, validates session access.

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
            user_id: Optional user ID for access validation
            **query_settings: Optional settings for few-shot retrieval:
                - use_reranker: bool - Enable/disable reranking
                - reranker_model: str - Model: 'xsmall', 'base', 'large'
                - top_k: int - Number of few-shot examples
                - use_hybrid: bool - Enable hybrid BM25+vector search

        Returns:
            QueryResult
        """
        # Log query settings for debugging (settings ready for future wire-up)
        if query_settings:
            logger.debug(f"SQL query settings: {query_settings}")
        # Get per-request LLM (multi-user safe)
        request_llm = self._get_current_llm()

        start_time = time.time()
        timings = {}  # Track per-stage timing

        # Multi-user safe: validate session access if user_id provided
        session = self.get_session(session_id, user_id)
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

        # Block queries until dictionary generation is complete
        if session.status == "generating_dictionary":
            return QueryResult(
                success=False,
                sql_generated="",
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error_message="Dictionary generation in progress. Please wait for schema analysis to complete."
            )

        # Update session status
        session.status = "generating"

        # Step 1: Validate user input
        t1 = time.time()
        is_valid, error = self._validator.validate_user_input(nl_query)
        timings["1_input_validation_ms"] = int((time.time() - t1) * 1000)
        if not is_valid:
            return QueryResult(
                success=False,
                sql_generated="",
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=0,
                error_message=error,
                timings=timings
            )

        # Step 2: Check if this is a refinement
        memory = self._session_memories.get(session_id)
        if memory and memory.is_follow_up(nl_query):
            return await self._execute_refinement(session, nl_query, memory)

        # Step 3: Classify intent
        t2 = time.time()
        session.status = "generating"
        intent = self._intent_classifier.classify(nl_query)
        timings["2_intent_classification_ms"] = int((time.time() - t2) * 1000)

        try:
            # Step 3.5: Smart schema caching with fingerprint detection
            # Only refresh if schema has changed (fast ~10ms fingerprint check)
            t3 = time.time()
            engine = self._connections.get_engine(session.connection_id)
            if engine:
                if self._schema.has_schema_changed(engine, session.connection_id):
                    logger.info(f"Schema changed for {session.connection_id}, refreshing")
                    fresh_schema = self._schema.introspect(engine, session.connection_id, force_refresh=True)
                    session.schema = fresh_schema
                    self._query_engine.remove_query_engine(session.connection_id)
                    self._query_engine.create_query_engine(session.connection_id, engine, fresh_schema)
                    # Update fingerprint cache
                    current_fp = self._schema.get_fingerprint(engine)
                    if current_fp:
                        self._schema_fingerprints[session.connection_id] = current_fp
                elif not self._query_engine.has_query_engine(session.connection_id):
                    # Query engine doesn't exist, create it
                    logger.info(f"Creating missing query engine for {session.connection_id}")
                    self._query_engine.create_query_engine(session.connection_id, engine, session.schema)

                # Verify query engine was created successfully
                if not self._query_engine.has_query_engine(session.connection_id):
                    logger.error(f"Failed to create query engine for {session.connection_id}")
                    return QueryResult(
                        success=False,
                        sql_generated="",
                        data=[],
                        columns=[],
                        row_count=0,
                        execution_time_ms=0,
                        error_message="Failed to initialize query engine. Please try again.",
                        timings=timings
                    )
            timings["3_schema_check_ms"] = int((time.time() - t3) * 1000)

            # Step 3.6: Schema linking - pre-filter relevant tables
            t4 = time.time()
            focused_schema = session.schema
            relevant_table_names = []
            if session.schema and len(session.schema.tables) > self._schema_linker._top_k:
                relevant_tables = self._schema_linker.link_tables(
                    nl_query, session.schema, session.connection_id
                )
                focused_schema = self._schema_linker.filter_schema(session.schema, relevant_tables)
                relevant_table_names = relevant_tables  # link_tables returns List[str]
                logger.info(f"Schema linking: {len(relevant_tables)} tables selected: {relevant_tables}")
            elif session.schema:
                relevant_table_names = [t.name for t in session.schema.tables]
            timings["4_schema_linking_ms"] = int((time.time() - t4) * 1000)

            # Step 3.7: Retrieve dictionary context for accurate SQL generation
            t5 = time.time()
            dictionary_context = self._get_dictionary_context(
                session.connection_id,
                nl_query,
                relevant_table_names
            )
            timings["5_dictionary_context_ms"] = int((time.time() - t5) * 1000)
            if dictionary_context:
                logger.info("Dictionary context retrieved for SQL generation")

            # Step 4: Generate SQL with dictionary context
            # Use focused_schema (RAG-filtered tables) instead of full schema
            # Set the dedicated GPT-4.1 LLM for SQL generation
            t6 = time.time()
            self._query_engine.set_llm(self._get_current_llm())
            sql, success, intent = self._query_engine.generate_with_correction(
                session.connection_id,
                nl_query,
                focused_schema,  # Only relevant tables from schema linking
                dictionary_context=dictionary_context
            )
            timings["6_sql_generation_ms"] = int((time.time() - t6) * 1000)

            if not success:
                return QueryResult(
                    success=False,
                    sql_generated=sql,
                    data=[],
                    columns=[],
                    row_count=0,
                    execution_time_ms=0,
                    error_message="Failed to generate valid SQL",
                    timings=timings
                )

            # Step 5: Estimate cost
            t7 = time.time()
            session.status = "validating"
            engine = self._connections.get_engine(session.connection_id)
            cost_estimate = None
            if engine:
                cost_estimate = self._cost_estimator.estimate(engine, sql)
                if cost_estimate:
                    is_safe, warning = self._cost_estimator.is_safe(cost_estimate)
                    if not is_safe:
                        timings["7_cost_estimation_ms"] = int((time.time() - t7) * 1000)
                        return QueryResult(
                            success=False,
                            sql_generated=sql,
                            data=[],
                            columns=[],
                            row_count=0,
                            execution_time_ms=0,
                            error_message=warning,
                            cost_estimate=cost_estimate,
                            timings=timings
                        )
            timings["7_cost_estimation_ms"] = int((time.time() - t7) * 1000)

            # Step 6: Execute with semantic inspection (pass schema for error correction)
            t8 = time.time()
            session.status = "executing"
            inspector = SemanticInspector(request_llm)

            def execute_fn(sql_to_run):
                return self._executor.execute_readonly(engine, sql_to_run)

            result, inspection_passed, retry_count = await inspector.execute_with_inspection(
                nl_query, sql, execute_fn, session.connection_id, schema=session.schema
            )
            timings["8_sql_execution_ms"] = int((time.time() - t8) * 1000)

            # Step 7: Apply data masking
            t9 = time.time()
            conn = self._connections.get_connection(session.connection_id)
            if conn and conn.masking_policy and result.success:
                result.data = self._data_masker.apply(result.data, conn.masking_policy)
            timings["9_data_masking_ms"] = int((time.time() - t9) * 1000)

            # Step 7.5: Result validation - sanity checks
            validation_issues = self._result_validator.validate(
                nl_query, result.sql_generated, result.data, session.schema
            )
            if validation_issues:
                # Add validation warnings to result
                result.validation_warnings = [
                    {"severity": i.severity.value, "message": i.message, "suggestion": i.suggestion}
                    for i in validation_issues
                ]
                if self._result_validator.has_errors(validation_issues):
                    logger.warning(f"Result validation found errors for query")

            # Step 8: Compute confidence
            t10 = time.time()
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
            timings["10_confidence_scoring_ms"] = int((time.time() - t10) * 1000)

            result.intent = intent

            # Step 9: Generate natural language explanation
            t11 = time.time()
            if result.success:
                column_names = [c.name for c in result.columns]
                response_gen = self._get_response_generator(request_llm)
                result.explanation = response_gen.generate(
                    user_query=nl_query,
                    sql=result.sql_generated,
                    data=result.data,
                    columns=column_names,
                    row_count=result.row_count,
                    error_message=result.error_message
                )
            timings["11_response_generation_ms"] = int((time.time() - t11) * 1000)

            # Set total execution time and timings on result
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            result.timings = timings

            # Step 10: Log telemetry
            self._telemetry.log_from_result(
                session_id, nl_query, result, intent.intent.value
            )

            # Step 10.5: Query learning - record successful queries
            if result.success and result.row_count > 0:
                try:
                    self._query_learner.record_success(
                        session, nl_query, result.sql_generated, result
                    )
                except Exception as learn_err:
                    logger.debug(f"Query learning failed: {learn_err}")

            # Step 11: Update memory
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

        # Get per-request LLM (multi-user safe) and set on query engine
        request_llm = self._get_current_llm()
        self._query_engine.set_llm(request_llm)

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

        # Generate natural language explanation (per-request LLM)
        if result.success:
            column_names = [c.name for c in result.columns]
            response_gen = self._get_response_generator(request_llm)
            result.explanation = response_gen.generate(
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

    def get_query_history(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> List[QueryResult]:
        """Get query history for session.

        Multi-user safe: If user_id is provided, validates session access.

        Args:
            session_id: Session ID
            user_id: Optional user ID for access validation

        Returns:
            List of QueryResult (empty list if session not found or access denied)
        """
        session = self.get_session(session_id, user_id)
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

    # ========== Dictionary Management ==========

    def generate_dictionary(
        self,
        connection_id: str,
        connection_name: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """Generate Markdown dictionary for a connection.

        Args:
            connection_id: Connection ID
            connection_name: Optional display name

        Returns:
            Tuple of (dictionary_markdown, error_message)
        """
        # Get engine and introspect WITH sample values for accurate dictionaries
        engine = self._connections.get_engine(connection_id)
        if not engine:
            return "", "Connection not available"

        # Force include_samples=True for dictionary generation
        schema = self._schema.introspect(
            engine, connection_id, force_refresh=True, include_samples=True
        )
        if not schema:
            return "", "Schema not available"

        name = connection_name or schema.database_name or connection_id
        dictionary = self._dictionary_generator.generate_dictionary(
            schema, name, include_samples=True, include_inferred=True
        )

        return dictionary, None

    def get_schema_delta(
        self,
        connection_id: str,
        existing_dictionary: str,
        connection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute delta between existing dictionary and current schema.

        Args:
            connection_id: Connection ID
            existing_dictionary: Existing dictionary Markdown
            connection_name: Optional connection name

        Returns:
            Delta information including added/removed tables/columns
        """
        # Get engine and introspect WITH sample values
        engine = self._connections.get_engine(connection_id)
        if not engine:
            return {"error": "Connection not available", "has_changes": False}

        schema = self._schema.introspect(
            engine, connection_id, force_refresh=True, include_samples=True
        )
        if not schema:
            return {"error": "Schema not available", "has_changes": False}

        name = connection_name or schema.database_name or connection_id
        delta = self._dictionary_generator.compute_delta(
            existing_dictionary, schema, name
        )

        return delta

    def merge_dictionary(
        self,
        connection_id: str,
        existing_dictionary: str
    ) -> Tuple[str, Optional[str]]:
        """Merge existing dictionary with current schema, preserving edits.

        Args:
            connection_id: Connection ID
            existing_dictionary: Existing dictionary Markdown

        Returns:
            Tuple of (merged_dictionary, error_message)
        """
        schema = self.get_schema(connection_id, force_refresh=True)
        if not schema:
            return "", "Schema not available"

        delta = self._dictionary_generator.compute_delta(
            existing_dictionary, schema, ""
        )

        merged = self._dictionary_generator.merge_with_delta(
            existing_dictionary, delta, schema
        )

        return merged, None

    def _get_dictionary_context(
        self,
        connection_id: str,
        nl_query: str,
        tables: Optional[List[str]] = None
    ) -> Optional[str]:
        """Retrieve relevant dictionary context for SQL generation via RAG.

        The dictionary is stored as a notebook source in "SQL: <connection_name>" notebook.
        This method queries that notebook to get relevant schema descriptions,
        sample values, and relationships to improve Text-to-SQL accuracy.

        Args:
            connection_id: Connection ID
            nl_query: User's natural language query
            tables: Optional list of relevant table names

        Returns:
            Formatted dictionary context for LLM prompt, or None if not available
        """
        try:
            # 1. Get connection info to find notebook name
            connection = self._connections.get_connection(connection_id)
            if not connection:
                logger.debug(f"No connection found for {connection_id}")
                return None

            conn_name = connection.name
            sql_notebook_name = f"SQL: {conn_name}"

            # 2. Find the SQL Chat notebook
            if not self.notebook_manager:
                logger.debug("No notebook manager available")
                return None

            user_id = self.pipeline._current_user_id
            notebooks = self.notebook_manager.list_notebooks(user_id)
            notebook_id = None
            for nb in notebooks:
                if nb.get('name') == sql_notebook_name:
                    notebook_id = nb.get('id')
                    break

            if not notebook_id:
                logger.debug(f"No SQL notebook found for {conn_name}")
                return None

            # 3. Build retrieval query combining user question + table names
            table_str = ' '.join(tables) if tables else ''
            retrieval_query = f"{nl_query} {table_str} columns sample values description"

            # 4. Retrieve from dictionary using vector store
            if not hasattr(self.pipeline, '_vector_store') or not self.pipeline._vector_store:
                logger.debug("No vector store available")
                return None

            # Get query embedding
            query_embedding = self._embed_model.get_query_embedding(retrieval_query)

            # Query vector store filtered to this notebook (retrieve more for reranking)
            results = self.pipeline._vector_store.query(
                query_embedding=query_embedding,
                similarity_top_k=15,  # Retrieve more for reranking
                filters={"notebook_id": notebook_id}
            )

            if not results:
                logger.debug(f"No dictionary chunks found for query")
                return None

            # 4b. Apply reranking for better precision
            from dbnotebook.core.providers.reranker_provider import (
                get_shared_reranker,
                is_reranker_enabled,
            )
            from llama_index.core.schema import NodeWithScore, QueryBundle

            if is_reranker_enabled() and len(results) > 5:
                try:
                    reranker = get_shared_reranker(model="base", top_n=5)
                    if reranker:
                        # Convert results to NodeWithScore for reranking
                        nodes_with_scores = [
                            NodeWithScore(node=node, score=score)
                            for node, score in results
                        ]
                        query_bundle = QueryBundle(query_str=retrieval_query)
                        reranked = reranker.postprocess_nodes(nodes_with_scores, query_bundle)
                        # Convert back to (node, score) tuples
                        results = [(nws.node, nws.score) for nws in reranked]
                        logger.debug(f"Reranked {len(results)} dictionary chunks")
                except Exception as e:
                    logger.debug(f"Reranking failed, using original results: {e}")

            # 5. Format dictionary chunks for prompt
            context_parts = ["## Dictionary Context (from database documentation):"]
            for node, score in results[:5]:  # Top 5 most relevant chunks
                content = node.get_content() if hasattr(node, 'get_content') else str(node)
                if content:
                    context_parts.append(content)

            if len(context_parts) == 1:  # Only header, no content
                return None

            logger.info(f"Retrieved {len(context_parts) - 1} dictionary chunks for SQL generation")
            return "\n\n".join(context_parts)

        except Exception as e:
            logger.warning(f"Failed to retrieve dictionary context: {e}")
            return None

    def get_table_relevance_scores(
        self,
        session_id: str,
        query: str
    ) -> List[Tuple[str, float]]:
        """Get table relevance scores for a query (for debugging/UI).

        Args:
            session_id: Session ID
            query: Natural language query

        Returns:
            List of (table_name, score) tuples sorted by score
        """
        session = self._sessions.get(session_id)
        if not session or not session.schema:
            return []

        return self._schema_linker.get_table_scores(
            query, session.schema, session.connection_id
        )

    def get_learned_join_patterns(
        self,
        connection_id: str
    ) -> List[Dict[str, Any]]:
        """Get learned JOIN patterns for a connection.

        Args:
            connection_id: Connection ID

        Returns:
            List of JOIN pattern dicts
        """
        patterns = self._query_learner.get_join_patterns(connection_id)
        return [
            {
                "table1": p.table1,
                "column1": p.column1,
                "table2": p.table2,
                "column2": p.column2,
                "join_type": p.join_type,
                "usage_count": p.usage_count
            }
            for p in patterns
        ]

    async def _generate_dictionary_async(self, session_id: str) -> None:
        """Generate dictionary files and upload to SQL notebook asynchronously.

        This method runs in the background after session creation:
        1. Generates schema_dictionary.md (schema structure)
        2. Generates sample_values.md (sample data from tables)
        3. Finds or creates the SQL notebook for the connection
        4. Uploads both files to the notebook for RAG retrieval
        5. Sets session.status = "ready" when complete

        Args:
            session_id: Session ID to generate dictionary for
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found for dictionary generation")
            return

        connection_id = session.connection_id
        connection = self._connections.get_connection(connection_id)
        if not connection:
            logger.error(f"Connection {connection_id} not found for dictionary generation")
            session.status = "ready"  # Allow queries but without dictionary
            return

        engine = self._connections.get_engine(connection_id)
        if not engine:
            logger.error(f"Could not get engine for {connection_id}")
            session.status = "ready"
            return

        try:
            sql_notebook_name = f"SQL: {connection.name}"
            user_id = self.pipeline._current_user_id or "00000000-0000-0000-0000-000000000001"

            # 1. Check if dictionary already exists in notebook
            notebook_id = None
            dictionary_exists = False

            if self.notebook_manager:
                notebooks = self.notebook_manager.list_notebooks(user_id)
                for nb in notebooks:
                    if nb.get('name') == sql_notebook_name:
                        notebook_id = nb.get('id')
                        break

                # Check if dictionary files already exist in the notebook
                # Accept multiple naming patterns:
                # - New: schema_dictionary_{id}.md, sample_values_{id}.md
                # - Old: {name}_dictionary.md, {name}_samples.md
                # - Generic: any file with "dictionary", "schema", or "sample" in name
                if notebook_id:
                    try:
                        docs = self.notebook_manager.get_documents(notebook_id)
                        doc_names = [d.get('file_name', '').lower() for d in docs]

                        # Check for schema/dictionary file (any pattern)
                        has_schema = any(
                            'schema_dictionary' in name or
                            '_dictionary' in name or
                            'dictionary' in name
                            for name in doc_names
                        )

                        # Check for sample values file (any pattern)
                        has_samples = any(
                            'sample_values' in name or
                            '_samples' in name or
                            'sample' in name
                            for name in doc_names
                        )

                        if has_schema and has_samples:
                            dictionary_exists = True
                            logger.info(f"Dictionary already exists for {connection.name} ({len(docs)} docs), skipping generation")
                        elif has_schema or has_samples:
                            # Partial dictionary - log but regenerate to ensure completeness
                            logger.info(f"Partial dictionary found for {connection.name} (schema={has_schema}, samples={has_samples}), regenerating")
                    except Exception as e:
                        logger.debug(f"Could not check existing documents: {e}")

            # 2. If dictionary exists, mark session ready and return
            if dictionary_exists:
                session.status = "ready"
                return

            # 3. Generate dictionary files
            logger.info(f"Starting dictionary generation for session {session_id}")
            start_time = datetime.utcnow()

            # Generate schema dictionary (fast - metadata only)
            schema_md = self._schema.generate_schema_dictionary(engine, connection.name)

            # Generate sample values (one query per table)
            samples_md = self._schema.generate_sample_values(engine, connection.name, limit=5)

            # 4. Create notebook if it doesn't exist
            if not notebook_id and self.notebook_manager:
                try:
                    nb_result = self.notebook_manager.create_notebook(
                        user_id=user_id,
                        name=sql_notebook_name,
                        description=f"Schema dictionary and sample data for {connection.name} database"
                    )
                    notebook_id = nb_result.get('id')
                    logger.info(f"Created SQL notebook {notebook_id} for {connection.name}")
                except ValueError as e:
                    # Notebook might already exist from another session
                    logger.warning(f"Could not create notebook: {e}")

            # 4. Save dictionary files to disk and ingest
            if notebook_id:
                upload_dir = Path("uploads") / "sql_dictionaries"
                upload_dir.mkdir(parents=True, exist_ok=True)

                # Save and ingest schema dictionary
                schema_file = upload_dir / f"schema_dictionary_{connection_id}.md"
                schema_file.write_text(schema_md, encoding='utf-8')

                # Save and ingest sample values
                samples_file = upload_dir / f"sample_values_{connection_id}.md"
                samples_file.write_text(samples_md, encoding='utf-8')

                # Store in vector store via pipeline
                try:
                    self.pipeline.store_nodes(
                        input_files=[str(schema_file), str(samples_file)],
                        notebook_id=notebook_id,
                        user_id=user_id
                    )
                    logger.info(f"Stored dictionary files in notebook {notebook_id}")
                except Exception as e:
                    logger.warning(f"Failed to store dictionary in vector store: {e}")

            # 5. Mark session as ready
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            session.status = "ready"
            logger.info(f"Dictionary generation complete for session {session_id} in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"Dictionary generation failed for session {session_id}: {e}")
            session.status = "ready"  # Allow queries but without dictionary
        finally:
            # Clean up thread reference
            self._dictionary_threads.pop(session_id, None)

    def get_session_status(self, session_id: str) -> Optional[str]:
        """Get the current status of a session.

        Args:
            session_id: Session ID

        Returns:
            Session status string or None if session not found
        """
        session = self._sessions.get(session_id)
        return session.status if session else None

    def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        # Dictionary generation threads are daemon threads, they will be cleaned up on exit
        self._dictionary_threads.clear()

        self._connections.close_all()
        self._schema_linker.clear_cache()
        self._query_learner.clear_cache()
        logger.info("SQLChatService cleaned up")
