"""Notebook request/response schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class NotebookCreate(BaseModel):
    """Create notebook request."""
    name: str = Field(..., description="Notebook name", min_length=1)
    description: Optional[str] = Field(None, description="Notebook description")


class NotebookResponse(BaseModel):
    """Notebook response model."""
    success: bool = Field(..., description="Whether request succeeded")
    notebook: Optional[dict] = Field(None, description="Notebook data")
    data: Optional[dict] = Field(None, description="Notebook data (alternative key)")
    error: Optional[str] = Field(None, description="Error message if failed")


class NotebookInfo(BaseModel):
    """Notebook information."""
    id: str = Field(..., description="Notebook UUID")
    name: str = Field(..., description="Notebook name")
    description: Optional[str] = Field(None, description="Notebook description")
    document_count: int = Field(0, description="Number of documents")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class NotebookList(BaseModel):
    """List of notebooks response."""
    success: bool = Field(..., description="Whether request succeeded")
    notebooks: List[dict] = Field(default_factory=list, description="List of notebooks")
    count: int = Field(0, description="Total notebook count")
    error: Optional[str] = Field(None, description="Error message if failed")
