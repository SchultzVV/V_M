"""
Ingest Service - Coleta dados do Instagram (bio + captions)
"""
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import httpx
import uuid

from shared.schemas import (
    IngestRequest, IngestResponse, InstagramProfile, InstagramCaption
)
from shared.database import get_db, UserModel, IngestLogModel, init_db
from shared.config import settings
from shared.redis_client import cache, cache_key_ingest_lock

app = FastAPI(title="Ingest Service", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    """Inicializa banco de dados"""
    init_db()
    print("✅ Ingest Service started")


async def check_rate_limit(user_id: str) -> bool:
    """Verifica se pode fazer ingest (cooldown)"""
    lock_key = cache_key_ingest_lock(user_id)
    
    if cache.exists(lock_key):
        return False
    
    # Define lock com TTL
    cache.set(lock_key, {"locked_at": datetime.utcnow().isoformat()}, 
              ttl=settings.INGEST_COOLDOWN_SECONDS)
    return True


@app.post("/ingest", response_model=IngestResponse)
async def ingest_instagram_data(
    request: IngestRequest,
    db: Session = Depends(get_db)
):
    """
    Coleta dados do Instagram do usuário
    
    Rate-limited: 1 ingest por hora por usuário
    
    Coleta:
    - Perfil (bio, username, followers)
    - Últimas 10 captions
    """
    # Verificar rate limit
    if not await check_rate_limit(request.user_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limited. Wait {settings.INGEST_COOLDOWN_SECONDS}s between ingests"
        )
    
    # Buscar usuário e token
    user = db.query(UserModel).filter(UserModel.id == request.user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.access_token:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Verificar se token ainda é válido
    if user.expires_at and user.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. Buscar perfil
            profile_response = await client.get(
                f"{settings.INSTAGRAM_GRAPH_URL}/{user.instagram_id}",
                params={
                    "fields": "id,username,biography,followers_count,follows_count",
                    "access_token": user.access_token
                },
                timeout=10.0
            )
            
            if profile_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch profile: {profile_response.text}"
                )
            
            profile_data = profile_response.json()
            
            profile = InstagramProfile(
                instagram_id=profile_data.get("id"),
                username=profile_data.get("username"),
                bio=profile_data.get("biography"),
                followers_count=profile_data.get("followers_count"),
                following_count=profile_data.get("follows_count")
            )
            
            # 2. Buscar posts recentes
            media_response = await client.get(
                f"{settings.INSTAGRAM_GRAPH_URL}/{user.instagram_id}/media",
                params={
                    "fields": "id,caption,timestamp,like_count",
                    "limit": 10,
                    "access_token": user.access_token
                },
                timeout=10.0
            )
            
            captions = []
            if media_response.status_code == 200:
                media_data = media_response.json()
                
                for media in media_data.get("data", []):
                    if media.get("caption"):
                        captions.append(InstagramCaption(
                            media_id=media.get("id"),
                            caption=media.get("caption", ""),
                            timestamp=datetime.fromisoformat(
                                media.get("timestamp").replace("Z", "+00:00")
                            ),
                            like_count=media.get("like_count")
                        ))
            
            # Salvar log de ingest
            ingest_log = IngestLogModel(
                id=str(uuid.uuid4()),
                user_id=user.id,
                instagram_id=user.instagram_id,
                profile_data=profile.model_dump(),
                captions_count=len(captions),
                ingested_at=datetime.utcnow(),
                status="success"
            )
            db.add(ingest_log)
            db.commit()
            
            return IngestResponse(
                user_id=user.id,
                profile=profile,
                captions=captions,
                ingested_at=datetime.utcnow()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        # Log erro
        ingest_log = IngestLogModel(
            id=str(uuid.uuid4()),
            user_id=user.id,
            instagram_id=user.instagram_id,
            profile_data=None,
            captions_count=0,
            ingested_at=datetime.utcnow(),
            status=f"error: {str(e)}"
        )
        db.add(ingest_log)
        db.commit()
        
        raise HTTPException(status_code=500, detail=f"Ingest error: {str(e)}")


@app.get("/ingest/history/{user_id}")
async def get_ingest_history(
    user_id: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Retorna histórico de ingests do usuário"""
    logs = db.query(IngestLogModel).filter(
        IngestLogModel.user_id == user_id
    ).order_by(
        IngestLogModel.ingested_at.desc()
    ).limit(limit).all()
    
    return {
        "user_id": user_id,
        "logs": [
            {
                "id": log.id,
                "ingested_at": log.ingested_at,
                "status": log.status,
                "captions_count": log.captions_count
            }
            for log in logs
        ]
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "ingest"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
