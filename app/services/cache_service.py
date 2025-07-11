"""Caching service for the CPCC Enrollment API."""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
import redis.asyncio as redis
from redis.exceptions import RedisError

from app.config import settings
from app.core.exceptions import CacheError
from app.core.logging import LoggerMixin
from app.models.enrollment import EnrollmentResponse


class CacheService(LoggerMixin):
    """Redis-based caching service."""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._connection_lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_connection()
    
    async def _ensure_connection(self) -> None:
        """Ensure Redis connection is established."""
        if self._redis is None:
            async with self._connection_lock:
                if self._redis is None:
                    try:
                        self._redis = redis.from_url(
                            settings.redis_url,
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_timeout=5
                        )
                        # Test connection
                        await self._redis.ping()
                        self.logger.info("Successfully connected to Redis")
                    except Exception as e:
                        self.log_error(e, "Redis connection")
                        raise CacheError(f"Failed to connect to Redis: {str(e)}", "connection")
    
    async def _close_connection(self) -> None:
        """Close Redis connection."""
        if self._redis:
            try:
                await self._redis.close()
                self._redis = None
                self.logger.info("Redis connection closed")
            except Exception as e:
                self.log_error(e, "Redis connection close")
    
    def _generate_cache_key(self, subjects: List[str], term: Optional[str] = None, **kwargs) -> str:
        """Generate a cache key for enrollment data."""
        # Sort subjects for consistent keys
        sorted_subjects = sorted([s.upper().strip() for s in subjects])
        key_parts = ["enrollment", ":".join(sorted_subjects)]
        
        if term:
            key_parts.append(f"term:{term}")
        
        # Add other parameters
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}:{value}")
        
        return ":".join(key_parts)
    
    async def get_enrollment_data(
        self, 
        subjects: List[str], 
        term: Optional[str] = None,
        **kwargs
    ) -> Optional[EnrollmentResponse]:
        """Get cached enrollment data."""
        try:
            await self._ensure_connection()
            
            cache_key = self._generate_cache_key(subjects, term, **kwargs)
            
            self.logger.debug(f"Checking cache for key: {cache_key}")
            
            cached_data = await self._redis.get(cache_key)
            
            if cached_data:
                try:
                    data = json.loads(cached_data)
                    enrollment_response = EnrollmentResponse(**data)
                    
                    # Check if cache is still valid
                    if enrollment_response.cache_expires_at > datetime.utcnow():
                        self.logger.info(f"Cache hit for subjects: {subjects}")
                        return enrollment_response
                    else:
                        # Cache expired, remove it
                        await self._redis.delete(cache_key)
                        self.logger.info(f"Cache expired for subjects: {subjects}")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    self.log_error(e, "cache data parsing")
                    # Remove corrupted cache entry
                    await self._redis.delete(cache_key)
            
            self.logger.info(f"Cache miss for subjects: {subjects}")
            return None
            
        except RedisError as e:
            self.log_error(e, "cache retrieval")
            # Don't raise exception, just return None to allow fallback
            return None
        except Exception as e:
            self.log_error(e, "cache retrieval")
            return None
    
    async def cache_enrollment_data(
        self, 
        enrollment_data: EnrollmentResponse,
        subjects: List[str],
        term: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        **kwargs
    ) -> bool:
        """Cache enrollment data."""
        try:
            await self._ensure_connection()
            
            cache_key = self._generate_cache_key(subjects, term, **kwargs)
            ttl = ttl_seconds or settings.cache_ttl_seconds
            
            # Update cache timestamps
            now = datetime.utcnow()
            enrollment_data.cached_at = now
            enrollment_data.cache_expires_at = now + timedelta(seconds=ttl)
            
            # Serialize data
            cache_data = enrollment_data.model_dump_json()
            
            # Store in Redis with TTL
            await self._redis.setex(cache_key, ttl, cache_data)
            
            self.logger.info(
                f"Cached enrollment data for subjects: {subjects}",
                cache_key=cache_key,
                ttl_seconds=ttl,
                sections_count=len(enrollment_data.sections)
            )
            
            return True
            
        except RedisError as e:
            self.log_error(e, "cache storage")
            return False
        except Exception as e:
            self.log_error(e, "cache storage")
            return False
    
    async def invalidate_cache(self, pattern: str = "enrollment:*") -> int:
        """Invalidate cache entries matching a pattern."""
        try:
            await self._ensure_connection()
            
            # Get all keys matching pattern
            keys = await self._redis.keys(pattern)
            
            if keys:
                # Delete all matching keys
                deleted_count = await self._redis.delete(*keys)
                self.logger.info(f"Invalidated {deleted_count} cache entries with pattern: {pattern}")
                return deleted_count
            else:
                self.logger.info(f"No cache entries found for pattern: {pattern}")
                return 0
                
        except RedisError as e:
            self.log_error(e, "cache invalidation")
            raise CacheError(f"Failed to invalidate cache: {str(e)}", "invalidation")
        except Exception as e:
            self.log_error(e, "cache invalidation")
            raise CacheError(f"Unexpected error during cache invalidation: {str(e)}", "invalidation")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            await self._ensure_connection()
            
            # Get Redis info
            info = await self._redis.info()
            
            # Count enrollment cache keys
            enrollment_keys = await self._redis.keys("enrollment:*")
            
            stats = {
                "connected": True,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": info.get("db0", {}).get("keys", 0) if "db0" in info else 0,
                "enrollment_cache_keys": len(enrollment_keys),
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
            
            return stats
            
        except RedisError as e:
            self.log_error(e, "cache stats")
            return {
                "connected": False,
                "error": str(e)
            }
        except Exception as e:
            self.log_error(e, "cache stats")
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        """Check if cache service is healthy."""
        try:
            await self._ensure_connection()
            await self._redis.ping()
            return True
        except Exception:
            return False
    
    async def clear_all_cache(self) -> bool:
        """Clear all cache data (use with caution)."""
        try:
            await self._ensure_connection()
            await self._redis.flushdb()
            self.logger.warning("All cache data cleared")
            return True
        except Exception as e:
            self.log_error(e, "cache clear")
            return False
    
    async def set_cache_ttl(self, key: str, ttl_seconds: int) -> bool:
        """Set TTL for an existing cache key."""
        try:
            await self._ensure_connection()
            result = await self._redis.expire(key, ttl_seconds)
            return bool(result)
        except Exception as e:
            self.log_error(e, "cache TTL update")
            return False
    
    async def get_cache_key_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific cache key."""
        try:
            await self._ensure_connection()
            
            exists = await self._redis.exists(key)
            if not exists:
                return None
            
            ttl = await self._redis.ttl(key)
            size = await self._redis.memory_usage(key) if hasattr(self._redis, 'memory_usage') else None
            
            return {
                "exists": True,
                "ttl_seconds": ttl,
                "memory_usage_bytes": size
            }
            
        except Exception as e:
            self.log_error(e, "cache key info")
            return None


# Global cache service instance
cache_service = CacheService()