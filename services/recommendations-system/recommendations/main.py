"""
Recommendations Service - Gera recomendações personalizadas
"""
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import numpy as np

from shared.schemas import (
    RecommendationRequest, RecommendationResponse, RecommendationItem
)
from shared.database import get_db, ProfileModel, ProductModel
from shared.redis_client import cache, cache_key_recommendations, cache_key_segment_recommendations
from shared.config import settings

app = FastAPI(title="Recommendations Service", version="1.0.0")


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calcula similaridade de cosseno entre dois vetores"""
    if not vec1 or not vec2:
        return 0.0
    
    a = np.array(vec1)
    b = np.array(vec2)
    
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def calculate_score(
    similarity: float,
    discount: Optional[float],
    click_count: int = 0
) -> float:
    """
    Calcula score híbrido do produto
    
    Fórmula:
    score = similarity * 0.6 + discount_boost * 0.3 + popularity_boost * 0.1
    """
    # Base: similaridade
    base_score = similarity * 0.6
    
    # Boost por desconto
    discount_boost = 0.0
    if discount and discount > 0:
        discount_boost = min(discount / 100, 0.5) * 0.3
    
    # Boost por popularidade (clicks)
    popularity_boost = min(click_count / 100, 1.0) * 0.1
    
    return base_score + discount_boost + popularity_boost


@app.on_event("startup")
async def startup_event():
    """Inicializa serviço"""
    print("✅ Recommendations Service started")


@app.get("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    limit: int = 10,
    segment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Gera recomendações personalizadas
    
    Flow:
    1. Tenta cache (Redis)
    2. Se não encontrar, busca perfil do usuário
    3. Calcula similaridade com produtos
    4. Aplica boosting (desconto, popularidade)
    5. Rankeia e retorna top N
    6. Salva no cache
    
    Target: < 150ms latência
    """
    start_time = datetime.utcnow()
    cache_hit = False
    
    # 1. Tentar cache
    cache_key = cache_key_recommendations(user_id)
    cached = cache.get(cache_key)
    
    if cached:
        cache_hit = True
        return RecommendationResponse(
            user_id=user_id,
            items=[RecommendationItem(**item) for item in cached["items"]],
            cache_hit=True,
            generated_at=datetime.fromisoformat(cached["generated_at"])
        )
    
    # 2. Buscar perfil do usuário
    profile = db.query(ProfileModel).filter(
        ProfileModel.user_id == user_id
    ).first()
    
    if not profile or not profile.embedding_vector:
        # Fallback: recomendações genéricas (segment ou trending)
        return await get_generic_recommendations(segment, limit, db)
    
    user_embedding = profile.embedding_vector
    
    # 3. Buscar produtos
    products = db.query(ProductModel).limit(1000).all()
    
    if not products:
        raise HTTPException(status_code=404, detail="No products available")
    
    # 4. Calcular scores
    recommendations = []
    
    for product in products:
        if not product.embedding_vector:
            continue
        
        similarity = cosine_similarity(user_embedding, product.embedding_vector)
        
        # Pegar click count do perfil
        click_count = profile.click_stats.get(product.id, 0)
        
        score = calculate_score(similarity, product.discount, click_count)
        
        # Gerar reason
        reason = f"Match {int(similarity * 100)}%"
        if product.discount and product.discount > 0:
            reason += f" + {int(product.discount)}% OFF"
        
        recommendations.append(RecommendationItem(
            product_id=product.id,
            score=score,
            reason=reason,
            metadata={
                "title": product.title,
                "price": product.price,
                "discount": product.discount,
                "category": product.category
            }
        ))
    
    # 5. Rankear
    recommendations.sort(key=lambda x: x.score, reverse=True)
    top_recommendations = recommendations[:limit]
    
    # 6. Cachear
    cache_data = {
        "user_id": user_id,
        "items": [item.model_dump() for item in top_recommendations],
        "generated_at": datetime.utcnow().isoformat()
    }
    cache.set(cache_key, cache_data, ttl=settings.REDIS_CACHE_TTL)
    
    # Calcular latência
    latency = (datetime.utcnow() - start_time).total_seconds() * 1000
    print(f"⚡ Recommendations latency: {latency:.2f}ms (target: {settings.RECOMMENDATION_LATENCY_TARGET_MS}ms)")
    
    return RecommendationResponse(
        user_id=user_id,
        items=top_recommendations,
        cache_hit=False,
        generated_at=datetime.utcnow()
    )


async def get_generic_recommendations(
    segment: Optional[str],
    limit: int,
    db: Session
) -> RecommendationResponse:
    """
    Recomendações genéricas (fallback)
    
    Usa segment se fornecido, senão retorna trending
    """
    if segment:
        cache_key = cache_key_segment_recommendations(segment)
        cached = cache.get(cache_key)
        
        if cached:
            return RecommendationResponse(
                user_id="generic",
                items=[RecommendationItem(**item) for item in cached["items"]],
                cache_hit=True,
                generated_at=datetime.fromisoformat(cached["generated_at"])
            )
        
        # Buscar produtos do segmento
        products = db.query(ProductModel).filter(
            ProductModel.category == segment
        ).order_by(ProductModel.discount.desc()).limit(limit).all()
    else:
        # Trending: produtos com maior desconto
        products = db.query(ProductModel).order_by(
            ProductModel.discount.desc()
        ).limit(limit).all()
    
    items = [
        RecommendationItem(
            product_id=p.id,
            score=p.discount or 0.5,
            reason=f"{int(p.discount or 0)}% OFF" if p.discount else "Trending",
            metadata={
                "title": p.title,
                "price": p.price,
                "category": p.category
            }
        )
        for p in products
    ]
    
    return RecommendationResponse(
        user_id="generic",
        items=items,
        cache_hit=False,
        generated_at=datetime.utcnow()
    )


@app.post("/recommendations/invalidate/{user_id}")
async def invalidate_cache(user_id: str):
    """Invalida cache de recomendações do usuário"""
    cache_key = cache_key_recommendations(user_id)
    deleted = cache.delete(cache_key)
    
    return {
        "user_id": user_id,
        "cache_invalidated": deleted
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "recommendations"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
