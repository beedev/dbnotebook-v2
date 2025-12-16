"""
SQLAlchemy ORM Models for Notebook Architecture

This module defines the database models for the NotebookLM-style document chatbot:
- Users: User accounts (multi-user ready, start with default user)
- Notebooks: Document collections with isolated embeddings
- NotebookSources: Files uploaded to notebooks with metadata
- Conversations: Persistent conversation history per notebook
- QueryLogs: Query logging for observability and cost tracking
"""

from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, ForeignKey, BigInteger, Index, TypeDecorator
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
import uuid
from datetime import datetime

Base = declarative_base()


# UUID type that works with both PostgreSQL and SQLite
class UUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's UUID type when available, otherwise stores as String(36).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            else:
                return uuid.UUID(value)


class User(Base):
    """User model for multi-user support (start with single default user)"""
    __tablename__ = "users"

    user_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    last_active = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    notebooks = relationship("Notebook", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}')>"


class Notebook(Base):
    """Notebook model - collection of documents with isolated embeddings"""
    __tablename__ = "notebooks"
    __table_args__ = (
        Index('idx_user_notebooks', 'user_id', 'created_at'),
    )

    notebook_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    document_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notebooks")
    sources = relationship("NotebookSource", back_populates="notebook", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="notebook", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="notebook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Notebook(notebook_id={self.notebook_id}, name='{self.name}', docs={self.document_count})>"


class NotebookSource(Base):
    """Document sources (files) uploaded to notebooks"""
    __tablename__ = "notebook_sources"
    __table_args__ = (
        Index('idx_notebook_sources', 'notebook_id', 'upload_timestamp'),
        Index('idx_source_hash', 'notebook_id', 'file_hash', unique=True),
    )

    source_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(UUID(), ForeignKey("notebooks.notebook_id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA256 for duplicate detection
    file_size = Column(BigInteger)  # File size in bytes
    file_type = Column(String(50))  # PDF, DOCX, TXT, etc.
    chunk_count = Column(Integer)  # Number of chunks/nodes created
    upload_timestamp = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationships
    notebook = relationship("Notebook", back_populates="sources")

    def __repr__(self):
        return f"<NotebookSource(source_id={self.source_id}, file_name='{self.file_name}', chunks={self.chunk_count})>"


class Conversation(Base):
    """Persistent conversation history per notebook"""
    __tablename__ = "conversations"
    __table_args__ = (
        Index('idx_notebook_conversations', 'notebook_id', 'timestamp'),
        Index('idx_user_conversations', 'user_id', 'timestamp'),
    )

    conversation_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(UUID(), ForeignKey("notebooks.notebook_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationships
    notebook = relationship("Notebook", back_populates="conversations")
    user = relationship("User", back_populates="conversations")

    def __repr__(self):
        return f"<Conversation(conversation_id={self.conversation_id}, role='{self.role}', timestamp={self.timestamp})>"


class QueryLog(Base):
    """Query logs for observability and cost tracking"""
    __tablename__ = "query_logs"
    __table_args__ = (
        Index('idx_query_logs_timestamp', 'timestamp'),
        Index('idx_query_logs_notebook', 'notebook_id', 'timestamp'),
        Index('idx_query_logs_user', 'user_id', 'timestamp'),
    )

    log_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(UUID(), ForeignKey("notebooks.notebook_id", ondelete="SET NULL"))
    user_id = Column(UUID(), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    query_text = Column(Text, nullable=False)
    model_name = Column(String(100))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    response_time_ms = Column(Integer)  # Response time in milliseconds
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # Relationships
    notebook = relationship("Notebook", back_populates="query_logs")
    user = relationship("User", back_populates="query_logs")

    def __repr__(self):
        return f"<QueryLog(log_id={self.log_id}, model='{self.model_name}', tokens={self.total_tokens}, time={self.response_time_ms}ms)>"
