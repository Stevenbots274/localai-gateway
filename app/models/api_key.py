"""API Key database model for Neon PostgreSQL."""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, Index
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class APIKey(Base):
    """API Key model for authentication and rate limiting."""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    hashed_key = Column(String(64), nullable=False, unique=True, index=True)
    prefix = Column(String(16), nullable=False, index=True)

    # Rate limiting (per-key overrides)
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_burst = Column(Integer, default=10)

    # Usage tracking
    total_requests = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Metadata
    description = Column(Text, nullable=True)
    ip_whitelist = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_api_keys_is_active", "is_active"),
        Index("ix_api_keys_created_at", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "prefix": self.prefix,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_burst": self.rate_limit_burst,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
