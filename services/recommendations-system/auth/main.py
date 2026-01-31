"""
Auth & Consent Service - Gerencia OAuth e consentimento do Instagram
"""
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import httpx
import uuid

from shared.schemas import (
    InstagramAuthRequest, InstagramAuthResponse, 
    ConsentStatusResponse, ConsentStatus
)
from shared.database import get_db, UserModel, init_db
from shared.config import settings

app = FastAPI(title="Auth & Consent Service", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    """Inicializa banco de dados"""
    init_db()
    print("✅ Auth Service started")


@app.post("/auth/instagram", response_model=InstagramAuthResponse)
async def authenticate_instagram(
    auth_request: InstagramAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Autentica usuário via Instagram OAuth
    
    Flow:
    1. User autoriza app no Instagram
    2. Instagram redireciona com code
    3. Trocamos code por access_token
    4. Armazenamos token e consentimento
    """
    try:
        # Trocar code por access_token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"{settings.INSTAGRAM_GRAPH_URL}/oauth/access_token",
                data={
                    "client_id": settings.INSTAGRAM_APP_ID,
                    "client_secret": settings.INSTAGRAM_APP_SECRET,
                    "grant_type": "authorization_code",
                    "redirect_uri": auth_request.redirect_uri,
                    "code": auth_request.code
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Instagram auth failed: {token_response.text}"
                )
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            user_id_ig = token_data.get("user_id")
            
            # Obter dados do usuário
            user_response = await client.get(
                f"{settings.INSTAGRAM_GRAPH_URL}/{user_id_ig}",
                params={
                    "fields": "id,username",
                    "access_token": access_token
                }
            )
            
            user_data = user_response.json()
            instagram_id = user_data.get("id")
        
        # Criar ou atualizar usuário no banco
        user = db.query(UserModel).filter(
            UserModel.instagram_id == instagram_id
        ).first()
        
        if not user:
            user = UserModel(
                id=str(uuid.uuid4()),
                instagram_id=instagram_id,
                consent_status=ConsentStatus.GRANTED,
                access_token=access_token,
                expires_at=datetime.utcnow() + timedelta(days=60),
                scopes=["instagram_basic", "instagram_content_publish"],
                created_at=datetime.utcnow()
            )
            db.add(user)
        else:
            user.access_token = access_token
            user.consent_status = ConsentStatus.GRANTED
            user.expires_at = datetime.utcnow() + timedelta(days=60)
            user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        return InstagramAuthResponse(
            user_id=user.id,
            instagram_id=instagram_id,
            access_token=access_token,
            expires_at=user.expires_at,
            scopes=user.scopes
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Auth error: {str(e)}")


@app.get("/auth/status/{user_id}", response_model=ConsentStatusResponse)
async def get_consent_status(user_id: str, db: Session = Depends(get_db)):
    """Verifica status do consentimento do usuário"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verificar se token expirou
    if user.expires_at and user.expires_at < datetime.utcnow():
        user.consent_status = ConsentStatus.EXPIRED
        db.commit()
    
    return ConsentStatusResponse(
        user_id=user.id,
        instagram_id=user.instagram_id,
        consent_status=user.consent_status,
        scopes=user.scopes,
        granted_at=user.created_at if user.consent_status == ConsentStatus.GRANTED else None,
        expires_at=user.expires_at,
        revoked_at=None
    )


@app.post("/auth/revoke/{user_id}")
async def revoke_consent(user_id: str, db: Session = Depends(get_db)):
    """Revoga consentimento do usuário"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.consent_status = ConsentStatus.REVOKED
    user.access_token = None
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"status": "revoked", "user_id": user_id}


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "auth"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
