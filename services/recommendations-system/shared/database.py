"""
Database utilities compartilhados
"""
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Float, Boolean, JSON, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from shared.config import settings
from shared.schemas import ConsentStatus, EventType

Base = declarative_base()

# ============= SQLAlchemy Models =============

class UserModel(Base):
    """User model no banco"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    instagram_id = Column(String, unique=True, nullable=False, index=True)
    consent_status = Column(SQLEnum(ConsentStatus), default=ConsentStatus.PENDING)
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(DateTime)
    scopes = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EventModel(Base):
    """Event model no banco"""
    __tablename__ = "events"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    event_type = Column(SQLEnum(EventType), nullable=False)
    item_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata = Column(JSON)
    processed = Column(Boolean, default=False, index=True)


class ProfileModel(Base):
    """User profile model no banco"""
    __tablename__ = "profiles"
    
    user_id = Column(String, primary_key=True)
    embedding_text = Column(Text)
    embedding_vector = Column(JSON)  # Lista de floats
    click_stats = Column(JSON, default=dict)
    impression_stats = Column(JSON, default=dict)
    last_updated = Column(DateTime, default=datetime.utcnow)


class ProductModel(Base):
    """Product model no banco"""
    __tablename__ = "products"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    discount = Column(Float)
    embedding_vector = Column(JSON)  # Lista de floats
    category = Column(String, index=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class IngestLogModel(Base):
    """Log de ingests realizados"""
    __tablename__ = "ingest_logs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    instagram_id = Column(String)
    profile_data = Column(JSON)
    captions_count = Column(Integer)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # success, error, rate_limited


# ============= Database Connection =============

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializa o banco de dados"""
    Base.metadata.create_all(bind=engine)
