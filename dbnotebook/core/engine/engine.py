import logging
from typing import List, Optional, Union

from llama_index.core.chat_engine import CondensePlusContextChatEngine, SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms.llm import LLM
from llama_index.core.schema import BaseNode
from llama_index.core.prompts import PromptTemplate

from .retriever import LocalRetriever
from ..prompt import get_condense_prompt
from ...setting import get_settings, RAGSettings

logger = logging.getLogger(__name__)


class LocalChatEngine:
    """
    Factory for creating chat engines with or without document context.

    - SimpleChatEngine: For general conversation without documents
    - CondensePlusContextChatEngine: For RAG with document retrieval
    """

    def __init__(
        self,
        setting: RAGSettings | None = None,
        host: str = "host.docker.internal"
    ):
        self._setting = setting or get_settings()
        self._retriever = LocalRetriever(self._setting, host)
        self._host = host
        logger.debug("LocalChatEngine initialized")

    def set_engine(
        self,
        llm: LLM,
        nodes: List[BaseNode],
        language: str = "eng",
        offering_filter: Optional[List[str]] = None,
        vector_store=None,
        chat_history: Optional[List] = None
    ) -> Union[CondensePlusContextChatEngine, SimpleChatEngine]:
        """
        Create appropriate chat engine based on available documents.

        Args:
            llm: Language model for chat
            nodes: Document nodes (empty for simple chat)
            language: Language code for prompts
            offering_filter: List of offering names to filter by (Sales Pitch mode)
            vector_store: Optional LocalVectorStore for metadata filtering
            chat_history: Optional chat history to preserve when recreating engine

        Returns:
            Configured chat engine
        """
        # Create memory buffer with optional preserved history
        memory = ChatMemoryBuffer(
            token_limit=self._setting.ollama.chat_token_limit,
            chat_history=chat_history or []
        )

        # Simple chat engine (no documents)
        if not nodes:
            logger.debug("Creating SimpleChatEngine (no documents)")
            return SimpleChatEngine.from_defaults(
                llm=llm,
                memory=memory
            )

        # RAG chat engine with document retrieval
        filter_msg = f" (filtered by offerings: {offering_filter})" if offering_filter else ""
        logger.debug(f"Creating CondensePlusContextChatEngine with {len(nodes)} nodes{filter_msg}")
        retriever = self._retriever.get_retrievers(
            llm=llm,
            language=language,
            nodes=nodes,
            offering_filter=offering_filter,
            vector_store=vector_store
        )

        # Get custom condense prompt for preserving customer context
        condense_prompt_str = get_condense_prompt(language)
        condense_prompt = PromptTemplate(condense_prompt_str)

        return CondensePlusContextChatEngine.from_defaults(
            retriever=retriever,
            llm=llm,
            memory=memory,
            condense_prompt=condense_prompt
        )

    def clear_retriever_cache(self) -> None:
        """Clear the retriever's index cache."""
        self._retriever.clear_cache()
        logger.debug("Retriever cache cleared")
