"""
Few-Shot Dataset Setup for Chat with Data.

One-time setup to download and embed the Gretel synthetic_text_to_sql dataset
into local PGVectorStore for few-shot retrieval.
"""

import logging
from typing import List, Optional

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

    def is_initialized(self) -> bool:
        """Check if few-shot examples are already loaded.

        Returns:
            True if sufficient examples exist in database
        """
        try:
            with self._db_manager.get_session() as session:
                result = session.execute(
                    "SELECT COUNT(*) FROM sql_few_shot_examples"
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
                    "SELECT COUNT(*) FROM sql_few_shot_examples"
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
                session.execute(
                    """
                    INSERT INTO sql_few_shot_examples
                    (embedding, sql_prompt, sql_query, sql_context, complexity, domain)
                    VALUES (:embedding, :sql_prompt, :sql_query, :sql_context, :complexity, :domain)
                    """,
                    {
                        "embedding": embedding,
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
                    """
                    SELECT domain, COUNT(*) as count
                    FROM sql_few_shot_examples
                    GROUP BY domain
                    ORDER BY count DESC
                    """
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
                    """
                    SELECT complexity, COUNT(*) as count
                    FROM sql_few_shot_examples
                    GROUP BY complexity
                    ORDER BY count DESC
                    """
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
                session.execute("DELETE FROM sql_few_shot_examples")
                session.commit()
            logger.info("Few-shot examples cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear examples: {e}")
            return False
