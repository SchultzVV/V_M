"""
Exemplo de integração do sistema de recomendações no site
"""
import httpx
from typing import List, Optional
from datetime import datetime


class RecommendationsClient:
    """Cliente para integrar com o sistema de recomendações"""
    
    def __init__(self, base_url: str = "http://recommendations:8000"):
        self.base_url = base_url
        self.timeout = 5.0
    
    async def get_recommendations(
        self, 
        user_id: str, 
        limit: int = 10,
        segment: Optional[str] = None
    ) -> dict:
        """
        Obtém recomendações personalizadas para o usuário
        
        Args:
            user_id: ID do usuário
            limit: Quantidade de recomendações
            segment: Segmento/categoria para filtrar
            
        Returns:
            Dict com items, cache_hit, generated_at
        """
        async with httpx.AsyncClient() as client:
            params = {"user_id": user_id, "limit": limit}
            if segment:
                params["segment"] = segment
            
            response = await client.get(
                f"{self.base_url}/recommendations",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def track_impression(self, user_id: str, product_id: str) -> dict:
        """Rastreia quando produto é exibido para usuário"""
        return await self._track_event(user_id, product_id, "impression")
    
    async def track_click(self, user_id: str, product_id: str) -> dict:
        """Rastreia quando usuário clica em produto"""
        return await self._track_event(user_id, product_id, "click")
    
    async def track_purchase(self, user_id: str, product_id: str) -> dict:
        """Rastreia quando usuário compra produto"""
        return await self._track_event(user_id, product_id, "purchase")
    
    async def _track_event(
        self, 
        user_id: str, 
        product_id: str, 
        event_type: str
    ) -> dict:
        """Rastreia evento genérico"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/track",
                json={
                    "user_id": user_id,
                    "event_type": event_type,
                    "item_id": product_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def track_batch_impressions(
        self, 
        user_id: str, 
        product_ids: List[str]
    ) -> dict:
        """Rastreia múltiplas impressões de uma vez"""
        async with httpx.AsyncClient() as client:
            events = [
                {
                    "user_id": user_id,
                    "event_type": "impression",
                    "item_id": product_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                for product_id in product_ids
            ]
            
            response = await client.post(
                f"{self.base_url}/track/batch",
                json=events,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def auth_instagram(self, code: str, redirect_uri: str) -> dict:
        """Autentica usuário via Instagram OAuth"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/instagram",
                json={
                    "code": code,
                    "redirect_uri": redirect_uri
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_auth_status(self, user_id: str) -> dict:
        """Verifica status de autenticação do usuário"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/auth/status/{user_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def ingest_instagram_data(self, user_id: str) -> dict:
        """
        Coleta dados do Instagram do usuário
        Rate-limited: 1x por hora
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/ingest",
                json={"user_id": user_id},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def invalidate_cache(self, user_id: str) -> dict:
        """Invalida cache de recomendações do usuário"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/recommendations/invalidate/{user_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    async def health_check(self) -> dict:
        """Verifica saúde do sistema"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()


# ============= Exemplo de uso em rotas FastAPI =============

from fastapi import APIRouter, HTTPException, BackgroundTasks

router = APIRouter()
recs_client = RecommendationsClient()


@router.get("/api/v1/recommendations/{user_id}")
async def get_user_recommendations(
    user_id: str,
    limit: int = 10,
    category: str = None
):
    """Endpoint do site que retorna recomendações"""
    try:
        recommendations = await recs_client.get_recommendations(
            user_id=user_id,
            limit=limit,
            segment=category
        )
        
        return {
            "success": True,
            "data": recommendations["items"],
            "from_cache": recommendations.get("cache_hit", False)
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail="Recommendations service unavailable")


@router.get("/api/v1/products")
async def list_products(
    user_id: str = None,
    background_tasks: BackgroundTasks = None
):
    """Lista produtos com recomendações se usuário autenticado"""
    
    # Buscar produtos do banco
    products = get_products_from_db()  # Sua função
    
    if user_id:
        try:
            # Obter recomendações
            recs = await recs_client.get_recommendations(user_id, limit=5)
            recommended_ids = [item["product_id"] for item in recs["items"]]
            
            # Marcar produtos recomendados
            for product in products:
                product["is_recommended"] = product["id"] in recommended_ids
            
            # Rastrear impressões em background
            product_ids = [p["id"] for p in products[:20]]  # Primeiros 20 visíveis
            if background_tasks:
                background_tasks.add_task(
                    recs_client.track_batch_impressions,
                    user_id,
                    product_ids
                )
        
        except Exception as e:
            print(f"Erro ao obter recomendações: {e}")
            # Continua sem recomendações
    
    return {"products": products}


@router.post("/api/v1/products/{product_id}/view")
async def track_product_view(product_id: str, user_id: str):
    """Rastreia quando usuário visualiza detalhes do produto"""
    try:
        await recs_client.track_impression(user_id, product_id)
        return {"status": "tracked"}
    except Exception as e:
        # Não faz raise - tracking não deve quebrar fluxo
        print(f"Erro ao rastrear visualização: {e}")
        return {"status": "failed"}


@router.post("/api/v1/products/{product_id}/click")
async def track_product_click(product_id: str, user_id: str):
    """Rastreia quando usuário clica no produto"""
    try:
        await recs_client.track_click(user_id, product_id)
        return {"status": "tracked"}
    except Exception as e:
        print(f"Erro ao rastrear clique: {e}")
        return {"status": "failed"}


@router.post("/api/v1/orders")
async def create_order(order_data: dict, background_tasks: BackgroundTasks):
    """Cria pedido e rastreia compra"""
    
    # Criar pedido (sua lógica)
    order = create_order_in_db(order_data)
    
    # Rastrear compras em background
    user_id = order_data["user_id"]
    for item in order_data["items"]:
        background_tasks.add_task(
            recs_client.track_purchase,
            user_id,
            item["product_id"]
        )
    
    return {"order": order}


@router.get("/api/v1/auth/instagram/callback")
async def instagram_callback(code: str):
    """Callback do OAuth Instagram"""
    try:
        # Autenticar via recommendations system
        auth_result = await recs_client.auth_instagram(
            code=code,
            redirect_uri="https://seu-site.com/api/v1/auth/instagram/callback"
        )
        
        # Salvar user_id na sessão
        user_id = auth_result["user_id"]
        
        # Agendar coleta de dados do Instagram
        # (pode ser feito em background ou posteriormente)
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "Autenticado com sucesso!"
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na autenticação: {str(e)}")


# Função helper (exemplo)
def get_products_from_db():
    """Busca produtos do seu banco de dados"""
    # Sua implementação aqui
    return []


def create_order_in_db(order_data):
    """Cria pedido no seu banco"""
    # Sua implementação aqui
    return {}
