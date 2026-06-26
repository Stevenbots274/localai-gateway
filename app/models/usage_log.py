"""Usage log model for tracking all API requests."""
from sqlalchemy import Column, String, DateTime, Integer, Text, Float, Index, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class UsageLog(Base):
    """Usage log for tracking all API requests."""

    __tablename__ = "usage_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(String(36), ForeignKey("api_keys.id"), nullable=True, index=True)

    # Request details
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    model = Column(String(100), nullable=True, index=True)
    status_code = Column(Integer, nullable=True)

    # Token usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Performance
    latency_ms = Column(Float, nullable=True)

    # Client info
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_usage_logs_created_at_endpoint", "created_at", "endpoint"),
        Index("ix_usage_logs_api_key_created", "api_key_id", "created_at"),
    )
