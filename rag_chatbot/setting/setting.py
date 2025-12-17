import os
import yaml
from pathlib import Path
from functools import lru_cache
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


# Find config directory relative to project root
def _get_config_path() -> Path:
    """Get path to config directory."""
    # Try relative to this file first
    current_dir = Path(__file__).parent.parent.parent
    config_path = current_dir / "config"
    if config_path.exists():
        return config_path
    # Fallback to current working directory
    return Path.cwd() / "config"


class OllamaSettings(BaseModel):
    llm: str = Field(
        default="gpt-4.1", description="LLM model"
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
        default=10, description="Top k documents"
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


class ModelConfig(BaseModel):
    """Configuration for a single model."""
    name: str
    display_name: Optional[str] = None
    enabled: bool = True


class ProviderConfig(BaseModel):
    """Configuration for a model provider."""
    enabled: bool = True
    type: str = "api"  # "local" or "api"
    requires_api_key: bool = False
    env_key: Optional[str] = None
    models: List[ModelConfig] = []


class ModelsSettings(BaseModel):
    """Settings for available models loaded from config/models.yaml."""
    providers: Dict[str, ProviderConfig] = {}
    default_model: str = "llama3.1:latest"
    default_provider: str = "ollama"

    @classmethod
    def load_from_yaml(cls, config_path: Optional[Path] = None) -> "ModelsSettings":
        """Load models configuration from YAML file."""
        if config_path is None:
            config_path = _get_config_path() / "models.yaml"

        if not config_path.exists():
            # Return empty settings if config doesn't exist
            return cls()

        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}

            # Parse providers
            providers = {}
            for provider_name, provider_data in data.get('providers', {}).items():
                if provider_data is None:
                    continue

                # Parse models for this provider
                models = []
                for model_data in provider_data.get('models', []):
                    if isinstance(model_data, dict):
                        models.append(ModelConfig(**model_data))
                    elif isinstance(model_data, str):
                        models.append(ModelConfig(name=model_data))

                providers[provider_name] = ProviderConfig(
                    enabled=provider_data.get('enabled', True),
                    type=provider_data.get('type', 'api'),
                    requires_api_key=provider_data.get('requires_api_key', False),
                    env_key=provider_data.get('env_key'),
                    models=models
                )

            return cls(
                providers=providers,
                default_model=data.get('default_model', 'llama3.1:latest'),
                default_provider=data.get('default_provider', 'ollama')
            )
        except Exception as e:
            print(f"Warning: Failed to load models config: {e}")
            return cls()

    def get_models_for_provider(self, provider: str) -> List[ModelConfig]:
        """Get list of models for a specific provider."""
        if provider in self.providers and self.providers[provider].enabled:
            return [m for m in self.providers[provider].models if m.enabled]
        return []

    def is_provider_enabled(self, provider: str) -> bool:
        """Check if a provider is enabled in config."""
        return provider in self.providers and self.providers[provider].enabled

    def has_api_key(self, provider: str) -> bool:
        """Check if API key is available for a provider."""
        if provider not in self.providers:
            return False

        config = self.providers[provider]
        if not config.requires_api_key:
            return True

        if config.env_key:
            key = os.getenv(config.env_key, "")
            return bool(key and key != f"your_{provider}_api_key_here")

        return False


# Singleton for models settings
_models_settings_instance: ModelsSettings | None = None


def get_models_settings() -> ModelsSettings:
    """Get singleton ModelsSettings instance."""
    global _models_settings_instance
    if _models_settings_instance is None:
        _models_settings_instance = ModelsSettings.load_from_yaml()
    return _models_settings_instance


def reload_models_settings() -> ModelsSettings:
    """Reload models settings from config file."""
    global _models_settings_instance
    _models_settings_instance = ModelsSettings.load_from_yaml()
    return _models_settings_instance


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
