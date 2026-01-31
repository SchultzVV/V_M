"""
API Gateway - Ponto de entrada unificado para todos os serviços
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from datetime import datetime

from shared.config import settings
from shared.schemas import (
    InstagramAuthRequest, IngestRequest, TrackingEvent, RecommendationRequest
)

app = FastAPI(
    title="Instagram Personalized Promos - API Gateway",
    version="1.0.0",
    description="Gateway unificado para sistema de recomendações personalizadas"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= Middleware de Logging =============

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging de requests"""
    start_time = datetime.utcnow()
    
    response = await call_next(request)
    
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    print(f"📡 {request.method} {request.url.path} - {response.status_code} - {duration:.2f}ms")
    
    return response


# ============= Auth Routes =============

@app.post("/auth/instagram")
async def auth_instagram(auth_request: InstagramAuthRequest):
    """Proxy para Auth Service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.AUTH_SERVICE_URL}/auth/instagram",
                json=auth_request.model_dump(),
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")


@app.get("/auth/status/{user_id}")
async def get_auth_status(user_id: str):
    """Proxy para Auth Service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.AUTH_SERVICE_URL}/auth/status/{user_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")


@app.post("/auth/revoke/{user_id}")
async def revoke_auth(user_id: str):
    """Proxy para Auth Service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.AUTH_SERVICE_URL}/auth/revoke/{user_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")


# ============= Ingest Routes =============

@app.post("/ingest")
async def ingest_data(ingest_request: IngestRequest):
    """Proxy para Ingest Service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.INGEST_SERVICE_URL}/ingest",
                json=ingest_request.model_dump(),
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Ingest service error: {str(e)}")


@app.get("/ingest/history/{user_id}")
async def get_ingest_history(user_id: str, limit: int = 10):
    """Proxy para Ingest Service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.INGEST_SERVICE_URL}/ingest/history/{user_id}",
                params={"limit": limit},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Ingest service error: {str(e)}")


# ============= Tracking Routes =============

@app.post("/track")
async def track_event(event: TrackingEvent):
    """Proxy para Tracking Service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.TRACKING_SERVICE_URL}/track",
                json=event.model_dump(),
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Tracking service error: {str(e)}")


@app.post("/track/batch")
async def track_batch(events: list[TrackingEvent]):
    """Proxy para Tracking Service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.TRACKING_SERVICE_URL}/track/batch",
                json=[e.model_dump() for e in events],
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Tracking service error: {str(e)}")


# ============= Recommendations Routes =============

@app.get("/recommendations")
async def get_recommendations(
    user_id: str,
    limit: int = 10,
    segment: str = None
):
    """Proxy para Recommendations Service"""
    async with httpx.AsyncClient() as client:
        try:
            params = {"user_id": user_id, "limit": limit}
            if segment:
                params["segment"] = segment
            
            response = await client.get(
                f"{settings.RECOMMENDATIONS_SERVICE_URL}/recommendations",
                params=params,
                timeout=5.0  # Strict timeout para garantir latência
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Recommendations timeout (>{settings.RECOMMENDATION_LATENCY_TARGET_MS}ms)"
            )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Recommendations service error: {str(e)}")


@app.post("/recommendations/invalidate/{user_id}")
async def invalidate_recommendations(user_id: str):
    """Proxy para Recommendations Service"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.RECOMMENDATIONS_SERVICE_URL}/recommendations/invalidate/{user_id}",
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Recommendations service error: {str(e)}")


# ============= Health & Info =============

@app.get("/health")
async def health_check():
    """Health check de todos os serviços"""
    services = {
        "auth": settings.AUTH_SERVICE_URL,
        "ingest": settings.INGEST_SERVICE_URL,
        "tracking": settings.TRACKING_SERVICE_URL,
        "recommendations": settings.RECOMMENDATIONS_SERVICE_URL
    }
    
    statuses = {}
    
    async with httpx.AsyncClient() as client:
        for name, url in services.items():
            try:
                response = await client.get(f"{url}/health", timeout=5.0)
                statuses[name] = "healthy" if response.status_code == 200 else "unhealthy"
            except Exception:
                statuses[name] = "unreachable"
    
    overall_status = "healthy" if all(s == "healthy" for s in statuses.values()) else "degraded"
    
    return {
        "status": overall_status,
        "services": statuses,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Info sobre a API"""
    return {
        "name": "Instagram Personalized Promos API",
        "version": "1.0.0",
        "description": "Sistema de recomendações personalizadas usando Instagram",
        "endpoints": {
            "auth": "/auth/*",
            "ingest": "/ingest",
            "tracking": "/track",
            "recommendations": "/recommendations"
        },
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
