import logging
from typing import List, Optional

from dotenv import load_dotenv
from llama_index.core.retrievers import (
    BaseRetriever,
    QueryFusionRetriever,
    VectorIndexRetriever,
    RouterRetriever
)
from llama_index.core.callbacks.base import CallbackManager
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.tools import RetrieverTool
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.schema import BaseNode, NodeWithScore, QueryBundle, IndexNode
from llama_index.core.llms.llm import LLM
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core import Settings, VectorStoreIndex

from ..prompt import get_query_gen_prompt
from ...setting import get_settings, RAGSettings

load_dotenv()

logger = logging.getLogger(__name__)


class TwoStageRetriever(QueryFusionRetriever):
    """
    Two-stage retriever that combines fusion retrieval with reranking.

    Stage 1: BM25 + Vector retrieval with query fusion
    Stage 2: Rerank results using cross-encoder model
    """

    def __init__(
        self,
        retrievers: List[BaseRetriever],
        setting: RAGSettings | None = None,
        llm: Optional[LLM] = None,
        query_gen_prompt: Optional[str] = None,
        mode: FUSION_MODES = FUSION_MODES.SIMPLE,
        similarity_top_k: int = 20,
        num_queries: int = 4,
        use_async: bool = True,
        verbose: bool = False,
        callback_manager: Optional[CallbackManager] = None,
        objects: Optional[List[IndexNode]] = None,
        object_map: Optional[dict] = None,
        retriever_weights: Optional[List[float]] = None
    ) -> None:
        super().__init__(
            retrievers, llm, query_gen_prompt, mode, similarity_top_k, num_queries,
            use_async, verbose, callback_manager, objects, object_map, retriever_weights
        )
        self._setting = setting or get_settings()
        self._rerank_model = SentenceTransformerRerank(
            top_n=self._setting.retriever.top_k_rerank,
            model=self._setting.retriever.rerank_llm,
        )
        logger.debug(f"TwoStageRetriever initialized with rerank model: {self._setting.retriever.rerank_llm}")

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        queries: List[QueryBundle] = [query_bundle]
        if self.num_queries > 1:
            queries.extend(self._get_queries(query_bundle.query_str))

        if self.use_async:
            results = self._run_nested_async_queries(queries)
        else:
            results = self._run_sync_queries(queries)

        results = self._simple_fusion(results)
        return self._rerank_model.postprocess_nodes(results, query_bundle)

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        queries: List[QueryBundle] = [query_bundle]
        if self.num_queries > 1:
            queries.extend(self._get_queries(query_bundle.query_str))

        results = await self._run_async_queries(queries)
        results = self._simple_fusion(results)
        return self._rerank_model.postprocess_nodes(results, query_bundle)


class LocalRetriever:
    """
    Factory for creating optimized retrievers based on document count.

    Strategies:
    - Small collections (≤ top_k_rerank): Simple vector retriever
    - Large collections: Router with fusion and two-stage options
    """

    def __init__(
        self,
        setting: RAGSettings | None = None,
        host: str = "host.docker.internal"
    ):
        self._setting = setting or get_settings()
        self._host = host
        self._index_cache: Optional[VectorStoreIndex] = None
        self._cached_node_count: int = 0
        logger.debug("LocalRetriever initialized")

    def _get_or_create_index(
        self,
        nodes: List[BaseNode],
        force_rebuild: bool = False
    ) -> VectorStoreIndex:
        """Get cached index or create new one."""
        if (
            not force_rebuild and
            self._index_cache is not None and
            len(nodes) == self._cached_node_count
        ):
            logger.debug("Using cached vector index")
            return self._index_cache

        logger.debug(f"Creating new vector index with {len(nodes)} nodes")
        self._index_cache = VectorStoreIndex(nodes=nodes)
        self._cached_node_count = len(nodes)
        return self._index_cache

    def _get_normal_retriever(
        self,
        vector_index: VectorStoreIndex,
        llm: Optional[LLM] = None,
        language: str = "eng",
    ) -> VectorIndexRetriever:
        """Create simple vector retriever for small collections."""
        return VectorIndexRetriever(
            index=vector_index,
            similarity_top_k=self._setting.retriever.similarity_top_k,
            embed_model=Settings.embed_model,
            verbose=False
        )

    def _get_hybrid_retriever(
        self,
        vector_index: VectorStoreIndex,
        llm: Optional[LLM] = None,
        language: str = "eng",
        gen_query: bool = True
    ) -> BaseRetriever:
        """Create hybrid BM25 + vector retriever."""
        llm = llm or Settings.llm

        # Vector retriever
        vector_retriever = VectorIndexRetriever(
            index=vector_index,
            similarity_top_k=self._setting.retriever.similarity_top_k,
            embed_model=Settings.embed_model,
            verbose=False
        )

        # BM25 retriever
        bm25_retriever = BM25Retriever.from_defaults(
            index=vector_index,
            similarity_top_k=self._setting.retriever.similarity_top_k,
            verbose=False
        )

        retrievers = [bm25_retriever, vector_retriever]
        weights = self._setting.retriever.retriever_weights

        if gen_query:
            # Fusion retriever with query generation
            return QueryFusionRetriever(
                retrievers=retrievers,
                retriever_weights=weights,
                llm=llm,
                query_gen_prompt=get_query_gen_prompt(language),
                similarity_top_k=self._setting.retriever.top_k_rerank,
                num_queries=self._setting.retriever.num_queries,
                mode=self._setting.retriever.fusion_mode,
                verbose=False
            )
        else:
            # Two-stage retriever with reranking
            return TwoStageRetriever(
                retrievers=retrievers,
                retriever_weights=weights,
                setting=self._setting,
                llm=llm,
                query_gen_prompt=None,
                similarity_top_k=self._setting.retriever.similarity_top_k,
                num_queries=1,
                mode=self._setting.retriever.fusion_mode,
                verbose=False
            )

    def _get_router_retriever(
        self,
        vector_index: VectorStoreIndex,
        llm: Optional[LLM] = None,
        language: str = "eng",
    ) -> RouterRetriever:
        """Create router retriever that selects between fusion and two-stage."""
        llm = llm or Settings.llm

        fusion_tool = RetrieverTool.from_defaults(
            retriever=self._get_hybrid_retriever(
                vector_index, llm, language, gen_query=True
            ),
            description="Use this tool when the user's query is ambiguous or unclear.",
            name="Fusion Retriever with BM25 and Vector Retriever and LLM Query Generation."
        )

        two_stage_tool = RetrieverTool.from_defaults(
            retriever=self._get_hybrid_retriever(
                vector_index, llm, language, gen_query=False
            ),
            description="Use this tool when the user's query is clear and unambiguous.",
            name="Two Stage Retriever with BM25 and Vector Retriever and LLM Rerank."
        )

        return RouterRetriever.from_defaults(
            selector=LLMSingleSelector.from_defaults(llm=llm),
            retriever_tools=[fusion_tool, two_stage_tool],
            llm=llm
        )

    def get_retrievers(
        self,
        llm: LLM,
        language: str,
        nodes: List[BaseNode],
        offering_filter: Optional[List[str]] = None,
        practice_filter: Optional[List[str]] = None,
        vector_store=None
    ) -> BaseRetriever:
        """
        Get appropriate retriever based on collection size with optional filtering.

        Args:
            llm: Language model for query generation
            language: Language code for prompts
            nodes: Document nodes to index
            offering_filter: List of offering IDs to filter by (OR operation)
            practice_filter: List of practice names to filter by (OR operation)
            vector_store: Optional LocalVectorStore instance for metadata filtering

        Returns:
            Configured retriever instance
        """
        # Apply metadata filtering if requested
        filtered_nodes = nodes

        if (offering_filter or practice_filter) and vector_store:
            # Use vector store's filtering capability
            filtered_index = vector_store.get_index_with_filter(
                nodes=nodes,
                offering_ids=offering_filter,
                practice_names=practice_filter
            )

            if filtered_index is None:
                logger.warning("No nodes matched the filters, using unfiltered retriever")
                vector_index = self._get_or_create_index(nodes)
            else:
                vector_index = filtered_index
                # Update filtered_nodes count for retriever selection
                if offering_filter or practice_filter:
                    # Estimate filtered node count
                    filtered_nodes = vector_store.get_nodes_by_metadata(
                        nodes,
                        {"offering_id": offering_filter[0]} if offering_filter else {"it_practice": practice_filter[0]}
                    ) if (offering_filter or practice_filter) else nodes
        elif offering_filter or practice_filter:
            # Manual filtering without vector store
            logger.debug("Filtering nodes manually without vector store")
            logger.info(f"=== OFFERING FILTER DEBUG ===")
            logger.info(f"Offering filter: {offering_filter}")
            logger.info(f"Practice filter: {practice_filter}")
            logger.info(f"Total nodes to filter: {len(nodes)}")

            filtered_nodes = []

            for node in nodes:
                metadata = node.metadata or {}

                # Debug: Log metadata for each node
                logger.info(f"Node metadata: {metadata.get('file_name', 'unknown')}: offering_name={metadata.get('offering_name')}, offering_id={metadata.get('offering_id')}, notebook_id={metadata.get('notebook_id')}, it_practice={metadata.get('it_practice')}")

                # Check offering filter (by name, id, or notebook_id)
                if offering_filter:
                    node_offering_id = metadata.get("offering_id")
                    node_offering_name = metadata.get("offering_name")
                    node_notebook_id = metadata.get("notebook_id")

                    # Match against offering_id, offering_name, OR notebook_id
                    if (node_offering_id and node_offering_id in offering_filter) or \
                       (node_offering_name and node_offering_name in offering_filter) or \
                       (node_notebook_id and node_notebook_id in offering_filter):
                        logger.info(f"✓ Node MATCHED filter: {metadata.get('file_name')} (notebook_id={node_notebook_id})")
                        filtered_nodes.append(node)
                        continue
                    else:
                        logger.info(f"✗ Node REJECTED (no match): {metadata.get('file_name')}")

                # Check practice filter
                if practice_filter:
                    node_practice = metadata.get("it_practice")
                    if node_practice and node_practice in practice_filter:
                        filtered_nodes.append(node)
                        continue

            if not filtered_nodes:
                logger.warning("No nodes matched the filters, using all nodes")
                filtered_nodes = nodes

            logger.info(
                f"Filtered {len(filtered_nodes)} nodes from {len(nodes)} "
                f"(offerings={offering_filter}, practices={practice_filter})"
            )

            vector_index = self._get_or_create_index(filtered_nodes)
        else:
            # No filtering
            vector_index = self._get_or_create_index(nodes)

        # Select retriever strategy based on node count
        node_count = len(filtered_nodes)

        if node_count > self._setting.retriever.top_k_rerank:
            logger.debug(f"Using router retriever for {node_count} nodes")
            return self._get_router_retriever(vector_index, llm, language)
        else:
            logger.debug(f"Using simple retriever for {node_count} nodes")
            return self._get_normal_retriever(vector_index, llm, language)

    def get_all_nodes_for_offering(
        self,
        nodes: List[BaseNode],
        offering_filter: List[str]
    ) -> List[BaseNode]:
        """
        Retrieve ALL nodes for specific offerings (no top-k limit).

        Useful for comprehensive queries like "summarize Nexus offering"
        where we need full context, not just top-k similar chunks.

        Args:
            nodes: All available nodes
            offering_filter: List of offering names/IDs to retrieve

        Returns:
            All nodes matching the offering filter
        """
        if not offering_filter:
            logger.warning("No offering filter provided for comprehensive retrieval")
            return []

        filtered_nodes = []

        for node in nodes:
            metadata = node.metadata or {}
            node_offering_id = metadata.get("offering_id")
            node_offering_name = metadata.get("offering_name")

            if (node_offering_id and node_offering_id in offering_filter) or \
               (node_offering_name and node_offering_name in offering_filter):
                filtered_nodes.append(node)

        logger.info(
            f"Comprehensive retrieval: {len(filtered_nodes)} nodes for offerings {offering_filter}"
        )

        return filtered_nodes

    def clear_cache(self) -> None:
        """Clear the index cache."""
        self._index_cache = None
        self._cached_node_count = 0
        logger.debug("Retriever cache cleared")
