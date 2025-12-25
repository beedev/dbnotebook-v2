# Patch llama_index to support newer models before any imports
# OpenAI models patch
try:
    from llama_index.llms.openai import utils as openai_utils
    # Add gpt-4.1 (and other newer models) that llama_index doesn't know about
    _new_openai_models = {'gpt-4.1': 128000, 'gpt-4.1-mini': 128000}
    for model, ctx in _new_openai_models.items():
        openai_utils.GPT4_MODELS[model] = ctx
        openai_utils.ALL_AVAILABLE_MODELS[model] = ctx
        openai_utils.CHAT_MODELS[model] = ctx  # Mark as chat model
except (ImportError, AttributeError):
    pass

# Gemini models patch - add newer models to llama_index's default list
try:
    import llama_index.llms.gemini.base as gemini_base
    # Add newer Gemini models that llama_index doesn't know about
    _new_gemini_models = (
        "models/gemini-2.0-flash-exp",
        "models/gemini-3-pro-preview",
        "models/gemini-3-pro-image-preview",
        "models/gemini-2.5-pro",
        "models/gemini-2.5-flash",
    )
    # Extend the GEMINI_MODELS tuple
    gemini_base.GEMINI_MODELS = gemini_base.GEMINI_MODELS + _new_gemini_models
except (ImportError, AttributeError):
    pass

from .pipeline import LocalRAGPipeline
from .ollama import run_ollama_server

__all__ = [
    "LocalRAGPipeline",
    "run_ollama_server",
]
