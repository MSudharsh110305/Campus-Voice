"""
Token bucket rate limiter implementation.
"""

import time
import asyncio
from typing import Dict
from src.utils.exceptions import RateLimitExceededError


class TokenBucket:
    """Token bucket for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
        
        Returns:
            True if tokens were consumed, False otherwise
        """
        async with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
        
        Returns:
            Wait time in seconds
        """
        async with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    Supports multiple rate limit rules per key.
    """
    
    def __init__(self):
        """Initialize rate limiter"""
        self.buckets: Dict[str, TokenBucket] = {}
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
    
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        tokens: int = 1
    ) -> bool:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier (e.g., user_id, IP)
            max_requests: Maximum requests in window
            window_seconds: Time window in seconds
            tokens: Number of tokens to consume
        
        Returns:
            True if allowed, False otherwise
        """
        # Cleanup old buckets periodically
        await self._cleanup_if_needed()
        
        # Create bucket key
        bucket_key = f"{key}:{max_requests}:{window_seconds}"
        
        # Get or create bucket
        if bucket_key not in self.buckets:
            refill_rate = max_requests / window_seconds
            self.buckets[bucket_key] = TokenBucket(max_requests, refill_rate)
        
        bucket = self.buckets[bucket_key]
        return await bucket.consume(tokens)
    
    async def enforce_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        tokens: int = 1
    ):
        """
        Enforce rate limit, raise exception if exceeded.
        
        Args:
            key: Unique identifier
            max_requests: Maximum requests in window
            window_seconds: Time window in seconds
            tokens: Number of tokens to consume
        
        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        allowed = await self.check_rate_limit(key, max_requests, window_seconds, tokens)
        
        if not allowed:
            bucket_key = f"{key}:{max_requests}:{window_seconds}"
            bucket = self.buckets.get(bucket_key)
            
            if bucket:
                wait_time = await bucket.get_wait_time(tokens)
                raise RateLimitExceededError(
                    f"Rate limit exceeded. Please try again in {int(wait_time)} seconds"
                )
            else:
                raise RateLimitExceededError()
    
    async def _cleanup_if_needed(self):
        """Cleanup old buckets if needed"""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_old_buckets()
            self.last_cleanup = now
    
    async def _cleanup_old_buckets(self):
        """Remove buckets that haven't been used recently"""
        current_time = time.time()
        keys_to_remove = []
        
        for key, bucket in self.buckets.items():
            # Remove if not used in last hour and fully refilled
            if (current_time - bucket.last_refill > 3600 and
                bucket.tokens >= bucket.capacity * 0.9):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.buckets[key]
    
    def clear(self):
        """Clear all rate limit buckets"""
        self.buckets.clear()
    
    def clear_key(self, key: str):
        """Clear rate limits for specific key"""
        keys_to_remove = [k for k in self.buckets.keys() if k.startswith(key)]
        for k in keys_to_remove:
            del self.buckets[k]


# Global rate limiter instance
rate_limiter = RateLimiter()


__all__ = ["RateLimiter", "TokenBucket", "rate_limiter"]
