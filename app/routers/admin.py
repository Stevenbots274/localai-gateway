"""Admin routes for monitoring and management."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.routers.auth import require_admin
from app.models.api_key import APIKey
from app.services.usage_service import usage_service
from app.services.localai_proxy import localai_proxy

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/health")
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: APIKey = Depends(require_admin)
):
    """Full system health check."""
    localai_health = await localai_proxy.health_check()

    return {
        "status": "healthy" if localai_health.get("status") == "healthy" else "degraded",
        "localai": localai_health,
        "gateway": {"status": "healthy"},
    }


@router.get("/usage/stats")
async def get_usage_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    admin: APIKey = Depends(require_admin)
):
    """Get global usage statistics."""
    return await usage_service.get_usage_stats(db, days=days)


@router.get("/usage/logs")
async def get_usage_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin: APIKey = Depends(require_admin)
):
    """Get recent usage logs."""
    logs = await usage_service.get_recent_logs(db, limit=limit)
    return {
        "logs": [
            {
                "id": log.id,
                "api_key_id": log.api_key_id,
                "endpoint": log.endpoint,
                "method": log.method,
                "model": log.model,
                "status_code": log.status_code,
                "total_tokens": log.total_tokens,
                "latency_ms": log.latency_ms,
                "client_ip": log.client_ip,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    }


@router.get("/localai/models")
async def get_localai_models(
    admin: APIKey = Depends(require_admin)
):
    """Get models from LocalAI backend."""
    return await localai_proxy.list_models()
