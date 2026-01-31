"""
Shared schemas para todos os serviços do sistema de recomendação
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ConsentStatus(str, Enum):
    """Status de consentimento do usuário"""
    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class EventType(str, Enum):
    """Tipos de eventos rastreados"""
    IMPRESSION = "impression"
    CLICK = "click"
    PURCHASE = "purchase"


# ============= Auth & Consent =============

class InstagramAuthRequest(BaseModel):
    """Request para autenticação Instagram"""
    code: str
    redirect_uri: str


class InstagramAuthResponse(BaseModel):
    """Response da autenticação"""
    user_id: str
    instagram_id: str
    access_token: str
    expires_at: datetime
    scopes: List[str]


class ConsentStatusResponse(BaseModel):
    """Status do consentimento do usuário"""
    user_id: str
    instagram_id: str
    consent_status: ConsentStatus
    scopes: List[str]
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


# ============= Ingest =============

class InstagramProfile(BaseModel):
    """Perfil do Instagram coletado"""
    instagram_id: str
    username: str
    bio: Optional[str] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None


class InstagramCaption(BaseModel):
    """Caption de post do Instagram"""
    media_id: str
    caption: str
    timestamp: datetime
    like_count: Optional[int] = None


class IngestRequest(BaseModel):
    """Request para ingest de dados do Instagram"""
    user_id: str


class IngestResponse(BaseModel):
    """Response do ingest"""
    user_id: str
    profile: InstagramProfile
    captions: List[InstagramCaption]
    ingested_at: datetime


# ============= Tracking =============

class TrackingEvent(BaseModel):
    """Evento de tracking"""
    user_id: str
    event_type: EventType
    item_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


class TrackingResponse(BaseModel):
    """Response do tracking"""
    event_id: str
    status: str


# ============= Profile Builder =============

class UserProfile(BaseModel):
    """Perfil consolidado do usuário"""
    user_id: str
    embedding_text: str
    embedding_vector: Optional[List[float]] = None
    click_stats: dict = Field(default_factory=dict)
    impression_stats: dict = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ProfileBuildRequest(BaseModel):
    """Request para construção de perfil"""
    user_id: str
    force_rebuild: bool = False


# ============= Recommendations =============

class RecommendationItem(BaseModel):
    """Item recomendado"""
    product_id: str
    score: float
    reason: str
    metadata: Optional[dict] = None


class RecommendationRequest(BaseModel):
    """Request para recomendações"""
    user_id: str
    limit: int = 10
    segment: Optional[str] = None
    filters: Optional[dict] = None


class RecommendationResponse(BaseModel):
    """Response de recomendações"""
    user_id: str
    items: List[RecommendationItem]
    cache_hit: bool = False
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============= Database Models =============

class User(BaseModel):
    """Modelo de usuário"""
    id: str
    instagram_id: str
    consent_status: ConsentStatus
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Event(BaseModel):
    """Modelo de evento"""
    id: str
    user_id: str
    event_type: EventType
    item_id: str
    timestamp: datetime
    metadata: Optional[dict] = None
    processed: bool = False


class Product(BaseModel):
    """Modelo de produto"""
    id: str
    title: str
    description: str
    price: float
    discount: Optional[float] = None
    embedding_vector: Optional[List[float]] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
