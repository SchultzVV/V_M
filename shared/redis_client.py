"""
Redis utilities para cache
"""
import redis
import json
from typing import Optional, Any
from datetime import timedelta
from shared.config import settings


class RedisCache:
    """Cliente Redis para cache"""
    
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        try:
            value = self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Define valor no cache"""
        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            serialized = json.dumps(value, default=str)
            return self.client.setex(key, ttl, serialized)
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Remove valor do cache"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False
    
    def get_many(self, keys: list[str]) -> dict:
        """Obtém múltiplos valores"""
        try:
            values = self.client.mget(keys)
            return {
                key: json.loads(val) if val else None 
                for key, val in zip(keys, values)
            }
        except Exception as e:
            print(f"Redis MGET error: {e}")
            return {}
    
    def set_many(self, data: dict, ttl: Optional[int] = None) -> bool:
        """Define múltiplos valores"""
        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            pipe = self.client.pipeline()
            for key, value in data.items():
                serialized = json.dumps(value, default=str)
                pipe.setex(key, ttl, serialized)
            pipe.execute()
            return True
        except Exception as e:
            print(f"Redis MSET error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que seguem o padrão"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis CLEAR_PATTERN error: {e}")
            return 0


# Instância global
cache = RedisCache()


# Chaves de cache padronizadas
def cache_key_recommendations(user_id: str) -> str:
    """Chave para recomendações de usuário"""
    return f"rec:user:{user_id}"


def cache_key_segment_recommendations(segment: str) -> str:
    """Chave para recomendações de segmento"""
    return f"rec:segment:{segment}"


def cache_key_profile(user_id: str) -> str:
    """Chave para perfil de usuário"""
    return f"profile:{user_id}"


def cache_key_ingest_lock(user_id: str) -> str:
    """Chave para lock de ingest"""
    return f"ingest:lock:{user_id}"
