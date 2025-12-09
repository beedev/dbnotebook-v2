import logging
from typing import List, Union

from llama_index.core.chat_engine import CondensePlusContextChatEngine, SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms.llm import LLM
from llama_index.core.schema import BaseNode

from .retriever import LocalRetriever
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
    ) -> Union[CondensePlusContextChatEngine, SimpleChatEngine]:
        """
        Create appropriate chat engine based on available documents.

        Args:
            llm: Language model for chat
            nodes: Document nodes (empty for simple chat)
            language: Language code for prompts

        Returns:
            Configured chat engine
        """
        memory = ChatMemoryBuffer(
            token_limit=self._setting.ollama.chat_token_limit
        )

        # Simple chat engine (no documents)
        if not nodes:
            logger.debug("Creating SimpleChatEngine (no documents)")
            return SimpleChatEngine.from_defaults(
                llm=llm,
                memory=memory
            )

        # RAG chat engine with document retrieval
        logger.debug(f"Creating CondensePlusContextChatEngine with {len(nodes)} nodes")
        retriever = self._retriever.get_retrievers(
            llm=llm,
            language=language,
            nodes=nodes
        )

        return CondensePlusContextChatEngine.from_defaults(
            retriever=retriever,
            llm=llm,
            memory=memory
        )

    def clear_retriever_cache(self) -> None:
        """Clear the retriever's index cache."""
        self._retriever.clear_cache()
        logger.debug("Retriever cache cleared")
