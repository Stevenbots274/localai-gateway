"""Authentication and API key management routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.services.api_key_service import api_key_service
from app.schemas.api_key import (
    APIKeyCreate, APIKeyResponse, APIKeyPublic, 
    APIKeyUpdate, APIKeyListResponse
)
from app.models.api_key import APIKey

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_current_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER)
) -> APIKey:
    """Validate API key from header."""
    api_key = None

    if authorization and authorization.startswith("Bearer "):
        api_key = authorization.replace("Bearer ", "")

    if not api_key and x_api_key:
        api_key = x_api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via Authorization: Bearer <key> or X-API-Key header"
        )

    # Admin bypass
    if api_key == settings.ADMIN_API_KEY:
        return APIKey(
            id="admin", name="admin", hashed_key="admin", prefix="admin",
            is_active=True, is_admin=True,
            rate_limit_per_minute=100000, rate_limit_burst=10000,
        )

    key = await api_key_service.verify_key(db, api_key)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )

    # IP whitelist check
    if key.ip_whitelist:
        client_ip = request.client.host if request.client else None
        allowed_ips = [ip.strip() for ip in key.ip_whitelist.split(",")]
        if client_ip and client_ip not in allowed_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP not whitelisted"
            )

    # Rate limiting
    rate = key.rate_limit_per_minute / 60.0
    capacity = key.rate_limit_burst
    allowed, retry_after = rate_limiter.is_allowed(key.id, rate, capacity)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {int(retry_after)} seconds.",
            headers={"Retry-After": str(int(retry_after))}
        )

    return key


async def require_admin(key: APIKey = Depends(get_current_api_key)) -> APIKey:
    if not key.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return key


@router.post("/keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    admin: APIKey = Depends(require_admin)
):
    """Create a new API key (admin only)."""
    db_key, plain_key = await api_key_service.create_key(db, data)

    return APIKeyResponse(
        id=db_key.id,
        name=db_key.name,
        key=plain_key,
        prefix=db_key.prefix,
        rate_limit_per_minute=db_key.rate_limit_per_minute,
        rate_limit_burst=db_key.rate_limit_burst,
        is_active=db_key.is_active,
        is_admin=db_key.is_admin,
        description=db_key.description,
        created_at=db_key.created_at,
        expires_at=db_key.expires_at,
    )


@router.get("/keys", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin: APIKey = Depends(require_admin)
):
    """List all API keys (admin only)."""
    keys, total = await api_key_service.get_all_keys(db, skip, limit)
    return APIKeyListResponse(
        keys=[APIKeyPublic.model_validate(k) for k in keys],
        total=total
    )


@router.get("/keys/me", response_model=APIKeyPublic)
async def get_my_key(key: APIKey = Depends(get_current_api_key)):
    """Get current API key info."""
    return APIKeyPublic.model_validate(key)


@router.patch("/keys/{key_id}", response_model=APIKeyPublic)
async def update_api_key(
    key_id: str, data: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    admin: APIKey = Depends(require_admin)
):
    """Update an API key (admin only)."""
    updated = await api_key_service.update_key(db, key_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="API key not found")
    return APIKeyPublic.model_validate(updated)


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    admin: APIKey = Depends(require_admin)
):
    """Delete an API key (admin only)."""
    success = await api_key_service.delete_key(db, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return None


@router.post("/keys/{key_id}/revoke", response_model=APIKeyPublic)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    admin: APIKey = Depends(require_admin)
):
    """Revoke an API key."""
    from app.schemas.api_key import APIKeyUpdate
    updated = await api_key_service.update_key(db, key_id, APIKeyUpdate(is_active=False))
    if not updated:
        raise HTTPException(status_code=404, detail="API key not found")
    return APIKeyPublic.model_validate(updated)
