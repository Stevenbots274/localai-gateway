"""Service layer for API key operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import Optional, List
from datetime import datetime, timezone

from app.models.api_key import APIKey
from app.core.security import generate_api_key, hash_api_key
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate


class APIKeyService:

    @staticmethod
    async def create_key(db: AsyncSession, data: APIKeyCreate) -> tuple[APIKey, str]:
        plain_key = generate_api_key()
        hashed = hash_api_key(plain_key)
        prefix = plain_key[:16]

        db_key = APIKey(
            name=data.name,
            hashed_key=hashed,
            prefix=prefix,
            rate_limit_per_minute=data.rate_limit_per_minute or 60,
            rate_limit_burst=data.rate_limit_burst or 10,
            is_admin=data.is_admin or False,
            description=data.description,
            expires_at=data.expires_at,
            ip_whitelist=data.ip_whitelist,
        )

        db.add(db_key)
        await db.commit()
        await db.refresh(db_key)

        return db_key, plain_key

    @staticmethod
    async def get_key_by_hash(db: AsyncSession, hashed_key: str) -> Optional[APIKey]:
        result = await db.execute(select(APIKey).where(APIKey.hashed_key == hashed_key))
        return result.scalar_one_or_none()

    @staticmethod
    async def verify_key(db: AsyncSession, plain_key: str) -> Optional[APIKey]:
        hashed = hash_api_key(plain_key)
        key = await APIKeyService.get_key_by_hash(db, hashed)

        if not key:
            return None
        if not key.is_active:
            return None
        if key.expires_at and key.expires_at < datetime.now(timezone.utc):
            return None

        return key

    @staticmethod
    async def get_all_keys(db: AsyncSession, skip: int = 0, limit: int = 100) -> tuple[List[APIKey], int]:
        result = await db.execute(
            select(APIKey).offset(skip).limit(limit).order_by(APIKey.created_at.desc())
        )
        keys = result.scalars().all()

        count_result = await db.execute(select(func.count()).select_from(APIKey))
        total = count_result.scalar()

        return list(keys), total

    @staticmethod
    async def get_key_by_id(db: AsyncSession, key_id: str) -> Optional[APIKey]:
        result = await db.execute(select(APIKey).where(APIKey.id == key_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_key(db: AsyncSession, key_id: str, data: APIKeyUpdate) -> Optional[APIKey]:
        key = await APIKeyService.get_key_by_id(db, key_id)
        if not key:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            await db.execute(update(APIKey).where(APIKey.id == key_id).values(**update_data))
            await db.commit()
            await db.refresh(key)

        return key

    @staticmethod
    async def delete_key(db: AsyncSession, key_id: str) -> bool:
        result = await db.execute(delete(APIKey).where(APIKey.id == key_id))
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def increment_usage(db: AsyncSession, key_id: str, tokens: int = 0):
        await db.execute(
            update(APIKey)
            .where(APIKey.id == key_id)
            .values(
                total_requests=APIKey.total_requests + 1,
                total_tokens=APIKey.total_tokens + tokens,
                last_used_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()


api_key_service = APIKeyService()
