"""Token bucket rate limiter using in-memory storage (Redis recommended for multi-instance)."""
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class Bucket:
    """Token bucket for rate limiting."""
    tokens: float
    last_update: float
    rate: float
    capacity: float


class RateLimiter:
    """In-memory token bucket rate limiter."""

    def __init__(self):
        self.buckets: Dict[str, Bucket] = {}

    def _get_bucket(self, key: str, rate: float, capacity: float) -> Bucket:
        """Get or create bucket for a key."""
        now = time.time()
        if key not in self.buckets:
            self.buckets[key] = Bucket(
                tokens=capacity,
                last_update=now,
                rate=rate,
                capacity=capacity
            )
        return self.buckets[key]

    def _update_bucket(self, bucket: Bucket) -> None:
        """Add tokens based on time elapsed."""
        now = time.time()
        elapsed = now - bucket.last_update
        bucket.tokens = min(bucket.capacity, bucket.tokens + elapsed * bucket.rate)
        bucket.last_update = now

    def is_allowed(self, key: str, rate: float, capacity: float) -> Tuple[bool, float]:
        """Check if request is allowed. Returns (allowed, retry_after)."""
        bucket = self._get_bucket(key, rate, capacity)
        self._update_bucket(bucket)

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True, 0

        retry_after = (1 - bucket.tokens) / bucket.rate
        return False, retry_after

    def get_remaining(self, key: str, rate: float, capacity: float) -> Tuple[int, float]:
        """Get remaining tokens and reset time."""
        bucket = self._get_bucket(key, rate, capacity)
        self._update_bucket(bucket)
        return int(bucket.tokens), bucket.capacity


# Global rate limiter instance
rate_limiter = RateLimiter()
