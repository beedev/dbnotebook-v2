import os
from functools import lru_cache
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

load_dotenv()


class OllamaSettings(BaseModel):
    llm: str = Field(
        default="llama3.1:latest", description="LLM model"
    )
    keep_alive: str = Field(
        default="1h", description="Keep alive time for the server"
    )
    tfs_z: float = Field(
        default=1.0, description="TFS normalization factor"
    )
    top_k: int = Field(
        default=40, description="Top k sampling"
    )
    top_p: float = Field(
        default=0.9, description="Top p sampling"
    )
    repeat_last_n: int = Field(
        default=64, description="Repeat last n tokens"
    )
    repeat_penalty: float = Field(
        default=1.1, description="Repeat penalty"
    )
    request_timeout: float = Field(
        default=300, description="Request timeout"
    )
    port: int = Field(
        default=11434, description="Port number"
    )
    context_window: int = Field(
        default=8000, description="Context window size"
    )
    temperature: float = Field(
        default=0.1, description="Temperature"
    )
    chat_token_limit: int = Field(
        default=8000, description="Chat memory limit"
    )


class RetrieverSettings(BaseModel):
    num_queries: int = Field(
        default=5, description="Number of generated queries"
    )
    similarity_top_k: int = Field(
        default=20, description="Top k documents"
    )
    retriever_weights: List[float] = Field(
        default=[0.4, 0.6], description="Weights for retriever"
    )
    top_k_rerank: int = Field(
        default=6, description="Top k rerank"
    )
    rerank_llm: str = Field(
       ##default="BAAI/bge-reranker-large", description="Rerank LLM model"
        default="mixedbread-ai/mxbai-rerank-large-v1", description="Rerank LLM model" 
    )
    fusion_mode: str = Field(
        default="dist_based_score", description="Fusion mode"
    )


class IngestionSettings(BaseModel):
    embed_llm: str = Field(
        ##default="BAAI/bge-large-en-v1.5", description="Embedding LLM model"
        default="nomic-ai/nomic-embed-text-v1.5", description="Embedding LLM model"
    )
    embed_batch_size: int = Field(
        default=8, description="Embedding batch size"
    )
    cache_folder: str = Field(
        default="data/huggingface", description="Cache folder"
    )
    chunk_size: int = Field(
        default=512, description="Document chunk size"
    )
    chunk_overlap: int = Field(
        default=32, description="Document chunk overlap"
    )
    chunking_regex: str = Field(
        default="[^,.;。？！]+[,.;。？！]?", description="Chunking regex"
    )
    paragraph_sep: str = Field(
        default="\n \n", description="Paragraph separator"
    )
    num_workers: int = Field(
        default=0, description="Number of workers"
    )


class StorageSettings(BaseModel):
    persist_dir_chroma: str = Field(
        default="data/chroma", description="Chroma directory"
    )
    persist_dir_storage: str = Field(
        default="data/storage", description="Storage directory"
    )
    collection_name: str = Field(
        default="collection", description="Collection name"
    )
    port: int = Field(
        default=8000, description="Port number"
    )


class AnthropicSettings(BaseModel):
    """Settings for Anthropic/Claude models."""
    api_key: str | None = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"),
        description="Anthropic API key"
    )
    model: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        description="Default Claude model"
    )
    temperature: float = Field(
        default_factory=lambda: float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
        description="Temperature for Claude models"
    )
    max_tokens: int = Field(
        default_factory=lambda: int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096")),
        description="Maximum tokens for Claude models"
    )


class GeminiSettings(BaseModel):
    """Settings for Google Gemini models."""
    api_key: str | None = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY"),
        description="Google API key for Gemini"
    )
    model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
        description="Default Gemini model"
    )
    temperature: float = Field(
        default_factory=lambda: float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
        description="Temperature for Gemini models"
    )
    max_output_tokens: int = Field(
        default_factory=lambda: int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "4096")),
        description="Maximum output tokens for Gemini models"
    )


class ImageGenerationSettings(BaseModel):
    """Settings for image generation."""
    provider: str = Field(
        default_factory=lambda: os.getenv("IMAGE_GENERATION_PROVIDER", "imagen"),
        description="Image generation provider (dalle|imagen)"
    )
    imagen_model: str = Field(
        default_factory=lambda: os.getenv("IMAGEN_MODEL", "imagen-3.0-generate-001"),
        description="Imagen model name"
    )
    num_images: int = Field(
        default_factory=lambda: int(os.getenv("IMAGEN_NUM_IMAGES", "1")),
        description="Number of images to generate"
    )
    aspect_ratio: str = Field(
        default_factory=lambda: os.getenv("IMAGEN_ASPECT_RATIO", "1:1"),
        description="Image aspect ratio"
    )
    output_format: str = Field(
        default_factory=lambda: os.getenv("IMAGEN_OUTPUT_FORMAT", "png"),
        description="Image output format"
    )
    output_dir: str = Field(
        default_factory=lambda: os.getenv("IMAGE_OUTPUT_DIR", "outputs/images"),
        description="Output directory for generated images"
    )
    max_image_size_mb: int = Field(
        default_factory=lambda: int(os.getenv("MAX_IMAGE_SIZE_MB", "10")),
        description="Maximum image file size in MB"
    )
    supported_formats: str = Field(
        default_factory=lambda: os.getenv("SUPPORTED_IMAGE_FORMATS", "jpg,jpeg,png,webp"),
        description="Supported image formats (comma-separated)"
    )


class RAGSettings(BaseModel):
    ollama: OllamaSettings = OllamaSettings()
    retriever: RetrieverSettings = RetrieverSettings()
    ingestion: IngestionSettings = IngestionSettings()
    storage: StorageSettings = StorageSettings()
    anthropic: AnthropicSettings = AnthropicSettings()
    gemini: GeminiSettings = GeminiSettings()
    image_generation: ImageGenerationSettings = ImageGenerationSettings()


# Singleton pattern for settings - use this instead of creating new instances
_settings_instance: RAGSettings | None = None


@lru_cache(maxsize=1)
def get_settings() -> RAGSettings:
    """Get singleton RAGSettings instance. Use this instead of RAGSettings()."""
    return RAGSettings()


def get_settings_instance() -> RAGSettings:
    """Alternative singleton accessor without lru_cache."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = RAGSettings()
    return _settings_instance
