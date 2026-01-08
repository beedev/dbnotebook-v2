"""
Few-Shot Dataset Setup for Chat with Data.

One-time setup to download and embed the Gretel synthetic_text_to_sql dataset
into local PGVectorStore for few-shot retrieval.

The embedding dimension is dynamically determined based on the configured
embedding model (from .env), ensuring compatibility regardless of whether
HuggingFace (768 dim) or OpenAI (1536 dim) embeddings are used.
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy import text

logger = logging.getLogger(__name__)


class FewShotSetup:
    """One-time setup to load Gretel dataset into local PGVectorStore.

    The Gretel synthetic_text_to_sql dataset contains 105K examples of
    natural language questions paired with SQL queries across 100 domains.

    This class handles:
    - Checking if setup is already complete
    - Downloading the dataset from HuggingFace
    - Batch embedding the prompts
    - Storing in PGVectorStore for fast retrieval
    """

    DATASET_NAME = "gretelai/synthetic_text_to_sql"
    BATCH_SIZE = 100  # Embedding batch size
    MIN_REQUIRED_EXAMPLES = 50000  # Minimum for setup to be considered complete

    def __init__(
        self,
        db_manager,
        embed_model,
        batch_size: int = 100
    ):
        """Initialize few-shot setup.

        Args:
            db_manager: Database manager for PGVectorStore access
            embed_model: Embedding model for prompt embedding
            batch_size: Batch size for embedding
        """
        self._db_manager = db_manager
        self._embed_model = embed_model
        self._batch_size = batch_size
        self._embed_dim: Optional[int] = None  # Cached embedding dimension

    def _get_embedding_dimension(self) -> int:
        """Get the embedding dimension from the configured model.

        Detects dimension by:
        1. Checking embed_model.embed_dim attribute (LlamaIndex models)
        2. Falling back to generating a test embedding

        Returns:
            Embedding dimension (e.g., 768 for nomic, 1536 for OpenAI)
        """
        if self._embed_dim is not None:
            return self._embed_dim

        # Try to get dimension from model attribute (LlamaIndex standard)
        if hasattr(self._embed_model, 'embed_dim'):
            self._embed_dim = self._embed_model.embed_dim
            logger.info(f"Embedding dimension from model: {self._embed_dim}")
            return self._embed_dim

        # Fallback: generate a test embedding to determine dimension
        try:
            test_embedding = self._embed_model.get_text_embedding("test")
            self._embed_dim = len(test_embedding)
            logger.info(f"Embedding dimension from test: {self._embed_dim}")
            return self._embed_dim
        except Exception as e:
            logger.error(f"Failed to determine embedding dimension: {e}")
            raise RuntimeError(f"Cannot determine embedding dimension: {e}")

    def _get_current_column_dimension(self) -> Optional[int]:
        """Check if embedding column exists and get its dimension.

        Returns:
            Current column dimension, or None if column doesn't exist
        """
        try:
            with self._db_manager.get_session() as session:
                # Check if column exists and get its type
                result = session.execute(text("""
                    SELECT udt_name, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = 'sql_few_shot_examples'
                    AND column_name = 'embedding'
                """))
                row = result.fetchone()
                if not row:
                    return None

                # For vector type, we need to check pg_attribute for dimension
                result = session.execute(text("""
                    SELECT atttypmod
                    FROM pg_attribute
                    WHERE attrelid = 'sql_few_shot_examples'::regclass
                    AND attname = 'embedding'
                """))
                attr_row = result.fetchone()
                if attr_row and attr_row[0] > 0:
                    return attr_row[0]
                return None
        except Exception as e:
            logger.debug(f"Error checking embedding column: {e}")
            return None

    def _ensure_embedding_column(self) -> bool:
        """Ensure embedding column exists with correct dimension.

        Creates or alters the embedding column to match the configured
        embedding model's dimension. Also creates the IVFFlat index.

        Returns:
            True if column is ready for use
        """
        required_dim = self._get_embedding_dimension()
        current_dim = self._get_current_column_dimension()

        logger.info(f"Embedding column check: required={required_dim}, current={current_dim}")

        try:
            with self._db_manager.get_session() as session:
                if current_dim is None:
                    # Column doesn't exist, create it
                    logger.info(f"Creating embedding column with {required_dim} dimensions")
                    session.execute(text(f"""
                        ALTER TABLE sql_few_shot_examples
                        ADD COLUMN embedding vector({required_dim})
                    """))
                    session.commit()
                elif current_dim != required_dim:
                    # Dimension mismatch - check if we have data
                    result = session.execute(text(
                        "SELECT COUNT(*) FROM sql_few_shot_examples WHERE embedding IS NOT NULL"
                    ))
                    data_count = result.scalar() or 0

                    if data_count > 0:
                        # Have existing data - warn but don't drop
                        logger.error(
                            f"Embedding dimension mismatch: table has {current_dim} dimensions "
                            f"with {data_count} rows, but configured model uses {required_dim}. "
                            f"Clear examples first with clear_examples() or change embedding model."
                        )
                        return False

                    # No data - safe to recreate column
                    logger.warning(
                        f"Embedding dimension mismatch: table has {current_dim}, "
                        f"model uses {required_dim}. Recreating column (no data to lose)..."
                    )
                    # Drop index first if exists
                    session.execute(text("""
                        DROP INDEX IF EXISTS idx_few_shot_embedding
                    """))
                    # Drop and recreate column
                    session.execute(text("""
                        ALTER TABLE sql_few_shot_examples DROP COLUMN embedding
                    """))
                    session.execute(text(f"""
                        ALTER TABLE sql_few_shot_examples
                        ADD COLUMN embedding vector({required_dim})
                    """))
                    session.commit()
                    logger.info(f"Embedding column recreated with {required_dim} dimensions")
                else:
                    logger.debug(f"Embedding column already has correct dimension: {required_dim}")

                # Ensure IVFFlat index exists
                self._ensure_vector_index(session)
                return True

        except Exception as e:
            logger.error(f"Failed to ensure embedding column: {e}")
            return False

    def _ensure_vector_index(self, session) -> None:
        """Create IVFFlat index if it doesn't exist.

        Args:
            session: Database session
        """
        try:
            # Check if index exists
            result = session.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'sql_few_shot_examples'
                AND indexname = 'idx_few_shot_embedding'
            """))
            if result.fetchone():
                logger.debug("Vector index already exists")
                return

            # Get row count to determine if we should create index now
            result = session.execute(text(
                "SELECT COUNT(*) FROM sql_few_shot_examples WHERE embedding IS NOT NULL"
            ))
            count = result.scalar() or 0

            if count < 1000:
                # Not enough data for IVFFlat, skip index creation
                # Index will be created after data is loaded
                logger.info(f"Skipping index creation (only {count} rows with embeddings)")
                return

            # Create IVFFlat index for fast vector similarity search
            logger.info("Creating IVFFlat vector index...")
            # Increase work memory for index creation
            session.execute(text("SET maintenance_work_mem = '256MB'"))
            session.execute(text("""
                CREATE INDEX idx_few_shot_embedding ON sql_few_shot_examples
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            session.commit()
            logger.info("Vector index created successfully")

        except Exception as e:
            logger.warning(f"Failed to create vector index: {e}")
            # Non-fatal - index can be created later

    def create_vector_index_if_needed(self) -> bool:
        """Create vector index after data loading if it doesn't exist.

        Call this after data loading is complete.

        Returns:
            True if index exists or was created
        """
        try:
            with self._db_manager.get_session() as session:
                self._ensure_vector_index(session)
                return True
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            return False

    def is_initialized(self) -> bool:
        """Check if few-shot examples are already loaded.

        Returns:
            True if sufficient examples exist in database
        """
        try:
            with self._db_manager.get_session() as session:
                result = session.execute(
                    text("SELECT COUNT(*) FROM sql_few_shot_examples")
                )
                count = result.scalar()
                logger.debug(f"Few-shot examples count: {count}")
                return count >= self.MIN_REQUIRED_EXAMPLES
        except Exception as e:
            logger.debug(f"Few-shot table check failed: {e}")
            return False

    def get_example_count(self) -> int:
        """Get current count of loaded examples.

        Returns:
            Number of examples in database
        """
        try:
            with self._db_manager.get_session() as session:
                result = session.execute(
                    text("SELECT COUNT(*) FROM sql_few_shot_examples")
                )
                return result.scalar() or 0
        except Exception:
            return 0

    async def initialize(
        self,
        max_examples: Optional[int] = None,
        progress_callback=None
    ) -> bool:
        """Download and embed Gretel dataset (one-time setup).

        This is a long-running operation (~30 min for full dataset).

        Args:
            max_examples: Optional limit on examples to load
            progress_callback: Optional callback(current, total) for progress

        Returns:
            True if initialization successful
        """
        try:
            from datasets import load_dataset
        except ImportError:
            logger.error("'datasets' package required. Install with: pip install datasets")
            return False

        logger.info(f"Starting few-shot setup from {self.DATASET_NAME}")

        try:
            # Ensure embedding column exists with correct dimension
            if not self._ensure_embedding_column():
                logger.error("Failed to ensure embedding column, aborting initialization")
                return False

            # Load dataset
            logger.info("Downloading dataset from HuggingFace...")
            ds = load_dataset(self.DATASET_NAME, split="train")

            total = len(ds)
            if max_examples:
                total = min(total, max_examples)
                ds = ds.select(range(total))

            logger.info(f"Processing {total} examples")

            # Process in batches
            examples_processed = 0
            batch_data = []

            for i, example in enumerate(ds):
                # Extract fields
                sql_prompt = example.get("sql_prompt", "")
                sql_query = example.get("sql", "")
                sql_context = example.get("sql_context", "")
                complexity = example.get("complexity", "")
                domain = example.get("domain", "")

                if not sql_prompt or not sql_query:
                    continue

                batch_data.append({
                    "sql_prompt": sql_prompt,
                    "sql_query": sql_query,
                    "sql_context": sql_context,
                    "complexity": complexity,
                    "domain": domain,
                })

                # Process batch
                if len(batch_data) >= self._batch_size:
                    await self._process_batch(batch_data)
                    examples_processed += len(batch_data)
                    batch_data = []

                    if progress_callback:
                        progress_callback(examples_processed, total)

                    if examples_processed % 10000 == 0:
                        logger.info(f"Processed {examples_processed}/{total} examples")

            # Process remaining
            if batch_data:
                await self._process_batch(batch_data)
                examples_processed += len(batch_data)

            # Create vector index after data loading (needs sufficient data for IVFFlat)
            logger.info("Creating vector index for fast similarity search...")
            self.create_vector_index_if_needed()

            logger.info(f"Few-shot setup complete. Loaded {examples_processed} examples")
            return True

        except Exception as e:
            logger.error(f"Few-shot setup failed: {e}")
            return False

    async def _process_batch(self, batch_data: List[dict]) -> None:
        """Process and store a batch of examples.

        Args:
            batch_data: List of example dicts
        """
        # Get embeddings for prompts
        prompts = [d["sql_prompt"] for d in batch_data]
        embeddings = self._embed_model.get_text_embedding_batch(prompts)

        # Store in database
        with self._db_manager.get_session() as session:
            for data, embedding in zip(batch_data, embeddings):
                # Convert embedding to string format for pgvector
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                # Use CAST syntax to avoid :: conflicting with SQLAlchemy parameter binding
                session.execute(
                    text("""
                    INSERT INTO sql_few_shot_examples
                    (embedding, sql_prompt, sql_query, sql_context, complexity, domain)
                    VALUES (CAST(:embedding AS vector), :sql_prompt, :sql_query, :sql_context, :complexity, :domain)
                    """),
                    {
                        "embedding": embedding_str,
                        "sql_prompt": data["sql_prompt"],
                        "sql_query": data["sql_query"],
                        "sql_context": data["sql_context"],
                        "complexity": data["complexity"],
                        "domain": data["domain"],
                    }
                )
            session.commit()

    def get_domain_distribution(self) -> dict:
        """Get distribution of examples by domain.

        Returns:
            Dict mapping domain to count
        """
        try:
            with self._db_manager.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT domain, COUNT(*) as count
                    FROM sql_few_shot_examples
                    GROUP BY domain
                    ORDER BY count DESC
                    """)
                )
                return {row.domain: row.count for row in result}
        except Exception as e:
            logger.error(f"Failed to get domain distribution: {e}")
            return {}

    def get_complexity_distribution(self) -> dict:
        """Get distribution of examples by complexity.

        Returns:
            Dict mapping complexity to count
        """
        try:
            with self._db_manager.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT complexity, COUNT(*) as count
                    FROM sql_few_shot_examples
                    GROUP BY complexity
                    ORDER BY count DESC
                    """)
                )
                return {row.complexity: row.count for row in result}
        except Exception as e:
            logger.error(f"Failed to get complexity distribution: {e}")
            return {}

    def clear_examples(self) -> bool:
        """Clear all few-shot examples from database.

        Returns:
            True if successful
        """
        try:
            with self._db_manager.get_session() as session:
                session.execute(text("DELETE FROM sql_few_shot_examples"))
                session.commit()
            logger.info("Few-shot examples cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear examples: {e}")
            return False
