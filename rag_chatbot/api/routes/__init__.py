"""API route modules."""

from .chat import create_chat_routes
# from .notebooks import create_notebook_routes  # TODO: MVP 2 - implement notebook routes
# from .documents import create_document_routes  # TODO: MVP 2 - implement document routes

__all__ = [
    'create_chat_routes',
    # 'create_notebook_routes',
    # 'create_document_routes',
]
