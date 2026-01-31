"""
Configurações compartilhadas do sistema
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configurações gerais do sistema"""
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@postgres:5432/recommendations_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hora
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_TOPIC_EVENTS: str = "user-events"
    KAFKA_TOPIC_PROFILES: str = "user-profiles"
    
    # Instagram API
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    INSTAGRAM_API_VERSION: str = "v18.0"
    INSTAGRAM_GRAPH_URL: str = "https://graph.instagram.com"
    
    # OpenAI / Embeddings
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    
    # Services URLs
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    INGEST_SERVICE_URL: str = "http://ingest-service:8002"
    TRACKING_SERVICE_URL: str = "http://tracking-service:8003"
    PROFILE_BUILDER_URL: str = "http://profile-builder:8004"
    RECOMMENDATIONS_SERVICE_URL: str = "http://recommendations-service:8005"
    
    # Performance
    RECOMMENDATION_LATENCY_TARGET_MS: int = 150
    MAX_RECOMMENDATIONS: int = 50
    
    # Rate Limiting
    INSTAGRAM_API_RATE_LIMIT: int = 200  # requests por hora
    INGEST_COOLDOWN_SECONDS: int = 3600  # 1 hora entre ingests
    
    # Security
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
