import logging
from typing import Optional

from llama_index.core import Settings
from llama_index.core.chat_engine.types import StreamingAgentChatResponse
from llama_index.core.prompts import ChatMessage, MessageRole

from .core import (
    LocalChatEngine,
    LocalDataIngestion,
    LocalRAGModel,
    LocalEmbedding,
    LocalVectorStore,
    get_system_prompt
)
from .setting import get_settings

logger = logging.getLogger(__name__)


class LocalRAGPipeline:
    """
    Main RAG pipeline orchestrating model, embedding, ingestion, and chat engine.

    Optimized for:
    - Single model/embedding initialization
    - Cached vector index
    - Proper logging
    """

    def __init__(self, host: str = "host.docker.internal") -> None:
        self._host = host
        self._language = "eng"
        self._model_name = ""
        self._system_prompt = get_system_prompt("eng", is_rag_prompt=False)
        self._query_engine = None
        self._settings = get_settings()

        # Initialize components once
        self._engine = LocalChatEngine(
            setting=self._settings,
            host=host
        )
        self._ingestion = LocalDataIngestion(
            setting=self._settings,
            max_workers=4,
            use_cache=True
        )
        self._vector_store = LocalVectorStore(
            host=host,
            setting=self._settings,
            persist=True
        )

        # Initialize models once and cache in Settings
        self._default_model = LocalRAGModel.set(
            model_name=self._model_name,
            host=host,
            setting=self._settings
        )
        Settings.llm = self._default_model
        Settings.embed_model = LocalEmbedding.set(
            host=host,
            setting=self._settings
        )

        logger.info(f"Pipeline initialized - Host: {host}")
        logger.debug(f"LLM Model: {self._model_name or self._settings.ollama.llm}")
        logger.debug(f"Embed Model: {self._settings.ingestion.embed_llm}")

    def get_model_name(self) -> str:
        return self._model_name

    def set_model_name(self, model_name: str) -> None:
        self._model_name = model_name
        logger.debug(f"Model name set to: {model_name}")

    def get_language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        self._language = language
        logger.debug(f"Language set to: {language}")

    def get_system_prompt(self) -> str:
        return self._system_prompt

    def set_system_prompt(self, system_prompt: Optional[str] = None) -> None:
        self._system_prompt = system_prompt or get_system_prompt(
            language=self._language,
            is_rag_prompt=self._ingestion.check_nodes_exist()
        )
        logger.debug("System prompt updated")

    def set_model(self) -> None:
        """Update the LLM model with current settings."""
        self._default_model = LocalRAGModel.set(
            model_name=self._model_name,
            system_prompt=self._system_prompt,
            host=self._host,
            setting=self._settings
        )
        Settings.llm = self._default_model
        logger.info(f"Model updated: {self._model_name}")

    def reset_engine(self) -> None:
        """Reset the chat engine without documents."""
        self._query_engine = self._engine.set_engine(
            llm=self._default_model,
            nodes=[],
            language=self._language
        )
        logger.debug("Engine reset (no documents)")

    def reset_documents(self) -> None:
        """Reset all ingested documents."""
        self._ingestion.reset()
        self._vector_store.reset()
        logger.info("Documents reset")

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        if self._query_engine:
            self._query_engine.reset()
            logger.debug("Conversation cleared")

    def reset_conversation(self) -> None:
        """Reset conversation and switch to non-RAG mode."""
        self.reset_engine()
        self.set_system_prompt(
            get_system_prompt(language=self._language, is_rag_prompt=False)
        )
        logger.info("Conversation reset to non-RAG mode")

    def set_embed_model(self, model_name: str) -> None:
        """Update the embedding model."""
        Settings.embed_model = LocalEmbedding.set(
            model_name=model_name,
            host=self._host,
            setting=self._settings
        )
        logger.info(f"Embedding model updated: {model_name}")

    def pull_model(self, model_name: str):
        """Pull an LLM model from Ollama."""
        logger.info(f"Pulling model: {model_name}")
        return LocalRAGModel.pull(self._host, model_name)

    def pull_embed_model(self, model_name: str):
        """Pull an embedding model from Ollama."""
        logger.info(f"Pulling embedding model: {model_name}")
        return LocalEmbedding.pull(self._host, model_name)

    def check_exist(self, model_name: str) -> bool:
        """Check if an LLM model exists on Ollama."""
        return LocalRAGModel.check_model_exist(self._host, model_name)

    def check_exist_embed(self, model_name: str) -> bool:
        """Check if an embedding model exists on Ollama."""
        return LocalEmbedding.check_model_exist(self._host, model_name)

    def store_nodes(self, input_files: Optional[list[str]] = None) -> None:
        """
        Process and store document nodes.

        Uses parallel processing and caching for efficiency.
        """
        if not input_files:
            logger.warning("No input files provided")
            return

        logger.info(f"Processing {len(input_files)} files")
        self._ingestion.store_nodes(input_files=input_files)
        logger.info("Document processing complete")

    def set_chat_mode(self, system_prompt: Optional[str] = None) -> None:
        """Configure chat mode with current documents and settings."""
        self.set_language(self._language)
        self.set_system_prompt(system_prompt)
        self.set_model()
        self.set_engine()
        logger.debug("Chat mode configured")

    def set_engine(self) -> None:
        """Set up the chat engine with current nodes."""
        nodes = self._ingestion.get_ingested_nodes()
        self._query_engine = self._engine.set_engine(
            llm=self._default_model,
            nodes=nodes,
            language=self._language
        )
        logger.debug(f"Engine set with {len(nodes)} nodes")

    def get_history(self, chatbot: list[dict]) -> list[ChatMessage]:
        """Convert chatbot history to ChatMessage format."""
        history = []
        for chat in chatbot:
            role_str = chat.get('role')
            content = chat.get('content')
            if role_str and content:
                role = MessageRole.USER if role_str == 'user' else MessageRole.ASSISTANT
                history.append(ChatMessage(role=role, content=content))
        return history

    def query(
        self,
        mode: str,
        message: str,
        chatbot: list[list[str]]
    ) -> StreamingAgentChatResponse:
        """
        Execute a query against the chat engine.

        Args:
            mode: "chat" for conversational, other for single Q&A
            message: User message
            chatbot: Conversation history

        Returns:
            Streaming response from the chat engine
        """
        logger.debug(f"Query mode: {mode}, message length: {len(message)}")

        if mode == "chat":
            history = self.get_history(chatbot)
            return self._query_engine.stream_chat(message, history)
        else:
            self._query_engine.reset()
            return self._query_engine.stream_chat(message)
