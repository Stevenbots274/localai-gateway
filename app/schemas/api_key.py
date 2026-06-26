"""Pydantic schemas for API Key operations."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    rate_limit_per_minute: Optional[int] = Field(60, ge=1, le=10000)
    rate_limit_burst: Optional[int] = Field(10, ge=1, le=1000)
    is_admin: Optional[bool] = Field(False)
    expires_at: Optional[datetime] = Field(None)
    ip_whitelist: Optional[str] = Field(None)


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str = Field(..., description="The API key (shown only once at creation)")
    prefix: str
    rate_limit_per_minute: int
    rate_limit_burst: int
    is_active: bool
    is_admin: bool
    description: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyPublic(BaseModel):
    id: str
    name: str
    prefix: str
    rate_limit_per_minute: int
    rate_limit_burst: int
    total_requests: int
    total_tokens: int
    is_active: bool
    is_admin: bool
    description: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_burst: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    expires_at: Optional[datetime] = None
    ip_whitelist: Optional[str] = None


class APIKeyListResponse(BaseModel):
    keys: list[APIKeyPublic]
    total: int
