"""Service layer for DBNotebook.

This package contains service implementations following the service layer pattern.
Services encapsulate business logic and coordinate between the pipeline, database,
and other core components.

Available Services:
- ChatService: Chat operations and conversation management
- DocumentService: Document upload, processing, and lifecycle management
- DocumentRoutingService: Two-stage LLM document routing for intelligent retrieval
- ImageService: Image generation and provider management
- MultiNotebookService: Cross-notebook query and retrieval
- SuggestionService: Smart document suggestions based on query gaps
- RefinementService: Query refinement and improvement
- ContinuityService: Conversation continuity and session management

Future Services (Wave 3+):
- NotebookService: Notebook CRUD and organization
- VisionService: Image analysis and text extraction
"""

from .base import BaseService
from .chat_service import ChatService
from .continuity_service import ContinuityService
from .document_service import DocumentService
from .document_routing_service import DocumentRoutingService
from .image_service import ImageService
from .multi_notebook_service import MultiNotebookService
from .refinement_service import RefinementService
from .suggestion_service import SuggestionService

__all__ = [
    "BaseService",
    "ChatService",
    "ContinuityService",
    "DocumentService",
    "DocumentRoutingService",
    "ImageService",
    "MultiNotebookService",
    "RefinementService",
    "SuggestionService",
]
