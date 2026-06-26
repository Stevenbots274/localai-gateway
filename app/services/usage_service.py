"""Service for tracking API usage."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from app.models.usage_log import UsageLog


class UsageService:

    @staticmethod
    async def log_request(
        db: AsyncSession,
        api_key_id: Optional[str],
        endpoint: str,
        method: str,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: Optional[float] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        log = UsageLog(
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            model=model,
            status_code=status_code,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            client_ip=client_ip,
            user_agent=user_agent,
            error_message=error_message,
        )
        db.add(log)
        await db.commit()

    @staticmethod
    async def get_usage_stats(db: AsyncSession, api_key_id: Optional[str] = None, days: int = 7) -> dict:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(UsageLog).where(UsageLog.created_at >= since)
        if api_key_id:
            query = query.where(UsageLog.api_key_id == api_key_id)

        result = await db.execute(query)
        logs = result.scalars().all()

        total_requests = len(logs)
        total_tokens = sum(log.total_tokens for log in logs)
        avg_latency = sum(log.latency_ms or 0 for log in logs) / total_requests if total_requests > 0 else 0

        endpoint_counts = {}
        model_counts = {}
        for log in logs:
            endpoint_counts[log.endpoint] = endpoint_counts.get(log.endpoint, 0) + 1
            if log.model:
                model_counts[log.model] = model_counts.get(log.model, 0) + 1

        return {
            "period_days": days,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "avg_latency_ms": round(avg_latency, 2),
            "endpoint_breakdown": endpoint_counts,
            "model_breakdown": model_counts,
        }

    @staticmethod
    async def get_recent_logs(db: AsyncSession, api_key_id: Optional[str] = None, limit: int = 100) -> List[UsageLog]:
        query = select(UsageLog).order_by(desc(UsageLog.created_at)).limit(limit)
        if api_key_id:
            query = query.where(UsageLog.api_key_id == api_key_id)

        result = await db.execute(query)
        return list(result.scalars().all())


usage_service = UsageService()
