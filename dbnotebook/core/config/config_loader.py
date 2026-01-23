"""Unified configuration loader for YAML config files.

Loads configuration from config/ directory with fallback to defaults.
Config files are loaded once at startup and cached.
"""

import logging
import yaml
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def get_config_path() -> Path:
    """Get path to config directory.

    Searches in order:
    1. Relative to this file's project root
    2. Current working directory
    """
    # Try relative to this file (project structure)
    current_file = Path(__file__)
    # Go up: config_loader.py -> config -> core -> dbnotebook -> project_root
    project_root = current_file.parent.parent.parent.parent
    config_path = project_root / "config"

    if config_path.exists():
        return config_path

    # Fallback to current working directory
    cwd_config = Path.cwd() / "config"
    if cwd_config.exists():
        return cwd_config

    # Return project path even if doesn't exist (for error messages)
    return config_path


def _load_yaml_file(filename: str) -> Dict[str, Any]:
    """Load a YAML config file.

    Args:
        filename: Name of the YAML file (e.g., 'raptor.yaml')

    Returns:
        Parsed YAML as dictionary, empty dict if file not found
    """
    config_path = get_config_path() / filename

    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return {}

    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
            logger.info(f"Loaded config from {config_path}")
            return data or {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing {config_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading {config_path}: {e}")
        return {}


@lru_cache(maxsize=1)
def load_raptor_config() -> Dict[str, Any]:
    """Load RAPTOR configuration from config/raptor.yaml.

    Returns:
        Dictionary with RAPTOR configuration
    """
    return _load_yaml_file("raptor.yaml")


@lru_cache(maxsize=1)
def load_ingestion_config() -> Dict[str, Any]:
    """Load ingestion configuration from config/ingestion.yaml.

    Returns:
        Dictionary with ingestion configuration
    """
    return _load_yaml_file("ingestion.yaml")


@lru_cache(maxsize=1)
def load_sql_chat_config() -> Dict[str, Any]:
    """Load SQL Chat configuration from config/sql_chat.yaml.

    Returns:
        Dictionary with SQL Chat configuration
    """
    return _load_yaml_file("sql_chat.yaml")


def reload_configs() -> None:
    """Clear config caches to reload from files.

    Call this if config files are modified at runtime.
    """
    load_raptor_config.cache_clear()
    load_ingestion_config.cache_clear()
    load_sql_chat_config.cache_clear()
    logger.info("Config caches cleared - will reload on next access")


# Convenience getters for specific config sections

def get_clustering_config() -> Dict[str, Any]:
    """Get clustering configuration."""
    return load_raptor_config().get("clustering", {})


def get_summarization_config() -> Dict[str, Any]:
    """Get summarization configuration."""
    return load_raptor_config().get("summarization", {})


def get_tree_building_config() -> Dict[str, Any]:
    """Get tree building configuration."""
    return load_raptor_config().get("tree_building", {})


def get_retrieval_config() -> Dict[str, Any]:
    """Get retrieval configuration."""
    return load_raptor_config().get("retrieval", {})


def get_raptor_presets() -> Dict[str, Any]:
    """Get RAPTOR quality presets."""
    return load_raptor_config().get("presets", {})


def get_chunking_config() -> Dict[str, Any]:
    """Get chunking configuration."""
    return load_ingestion_config().get("chunking", {})


def get_embedding_config() -> Dict[str, Any]:
    """Get embedding configuration."""
    return load_ingestion_config().get("embedding", {})


def get_contextual_retrieval_config() -> Dict[str, Any]:
    """Get contextual retrieval configuration."""
    return load_ingestion_config().get("contextual_retrieval", {})


def get_retriever_settings() -> Dict[str, Any]:
    """Get retriever settings from ingestion config."""
    return load_ingestion_config().get("retriever", {})


def get_llm_settings() -> Dict[str, Any]:
    """Get LLM settings from ingestion config."""
    return load_ingestion_config().get("llm", {})


def get_config_value(
    config_type: str,
    *keys: str,
    default: Any = None
) -> Any:
    """Get a nested config value with fallback default.

    Args:
        config_type: 'raptor', 'ingestion', or 'sql_chat'
        *keys: Nested keys to traverse
        default: Default value if key not found

    Returns:
        Config value or default

    Example:
        get_config_value('raptor', 'clustering', 'min_cluster_size', default=3)
        get_config_value('sql_chat', 'few_shot', 'rag_integration', 'enabled', default=True)
    """
    if config_type == 'raptor':
        config = load_raptor_config()
    elif config_type == 'ingestion':
        config = load_ingestion_config()
    elif config_type == 'sql_chat':
        config = load_sql_chat_config()
    else:
        logger.warning(f"Unknown config type: {config_type}")
        return default

    # Traverse nested keys
    for key in keys:
        if isinstance(config, dict) and key in config:
            config = config[key]
        else:
            return default

    return config
