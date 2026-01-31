# Integrando Recommendations System no Site

## 1. No seu docker-compose do site

Adicione o serviço de recomendações:

```yaml
services:
  # ... seus outros serviços (site, postgres, etc)
  
  recommendations:
    image: registry.seu-dominio.com/recommendations-system:latest
    # OU para build local:
    # build:
    #   context: ./services/recommendations-system
    #   dockerfile: Dockerfile
    container_name: recommendations-system
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/recommendations_db
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - INSTAGRAM_APP_ID=${INSTAGRAM_APP_ID}
      - INSTAGRAM_APP_SECRET=${INSTAGRAM_APP_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SERVICE=all  # Inicia todos os serviços
    ports:
      - "8000:8000"  # API Gateway
      - "8001:8001"  # Auth Service (opcional - apenas se precisar acessar direto)
      - "8005:8005"  # Recommendations Service (opcional)
    depends_on:
      - postgres
      - redis
      - kafka
    networks:
      - sua-rede
    restart: unless-stopped

  # Adicione Redis se não tiver
  redis:
    image: redis:7-alpine
    container_name: redis-cache
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - sua-rede

  # Adicione Kafka se não tiver
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    networks:
      - sua-rede

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    networks:
      - sua-rede

volumes:
  redis_data:

networks:
  sua-rede:
    driver: bridge
```

## 2. Usar a API no seu código Python

```python
import httpx

# URL do serviço de recomendações
RECOMMENDATIONS_URL = "http://recommendations:8000"

# Obter recomendações para um usuário
async def get_recommendations(user_id: str, limit: int = 10):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{RECOMMENDATIONS_URL}/recommendations",
            params={"user_id": user_id, "limit": limit},
            timeout=5.0
        )
        return response.json()

# Rastrear evento de clique
async def track_click(user_id: str, product_id: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{RECOMMENDATIONS_URL}/track",
            json={
                "user_id": user_id,
                "event_type": "click",
                "item_id": product_id
            }
        )

# Autenticar usuário com Instagram
async def auth_instagram(code: str, redirect_uri: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RECOMMENDATIONS_URL}/auth/instagram",
            json={
                "code": code,
                "redirect_uri": redirect_uri
            }
        )
        return response.json()
```

## 3. Exemplo de uso em rotas FastAPI

```python
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter()

@router.get("/products/recommended")
async def get_recommended_products(user_id: str):
    """Endpoint que retorna produtos recomendados"""
    
    # Obter recomendações
    recommendations = await get_recommendations(user_id, limit=10)
    
    # Processar e retornar
    return {
        "products": recommendations["items"],
        "personalized": not recommendations.get("cache_hit", False)
    }

@router.post("/products/{product_id}/click")
async def track_product_click(product_id: str, user_id: str):
    """Rastreia quando usuário clica em um produto"""
    
    # Rastrear clique
    await track_click(user_id, product_id)
    
    return {"status": "tracked"}
```

## 4. Build e Push para Registry

```bash
# Build da imagem
cd services/recommendations-system
docker build -t seu-registry.com/recommendations-system:latest .

# Push para registry
docker push seu-registry.com/recommendations-system:latest

# OU use o script
./build.sh
```

## 5. Variáveis de Ambiente Necessárias

Adicione no seu `.env`:

```bash
# Instagram API
INSTAGRAM_APP_ID=seu_app_id
INSTAGRAM_APP_SECRET=seu_app_secret

# OpenAI
OPENAI_API_KEY=sua_chave_openai

# URLs (se necessário customizar)
RECOMMENDATIONS_SERVICE_URL=http://recommendations:8000
```

## 6. Inicializar Banco de Dados

Primeira vez que subir, execute:

```bash
# Entrar no container
docker exec -it recommendations-system bash

# Rodar script de inicialização
python -c "from shared.database import init_db; init_db()"

# Sair
exit
```

## 7. Health Check

Verifique se está funcionando:

```bash
curl http://localhost:8000/health
```

Resposta esperada:
```json
{
  "status": "healthy",
  "services": {
    "auth": "healthy",
    "ingest": "healthy",
    "tracking": "healthy",
    "recommendations": "healthy"
  }
}
```

## 8. Documentação da API

Acesse: http://localhost:8000/docs

## Troubleshooting

### Serviço não inicia
```bash
# Ver logs
docker logs recommendations-system -f

# Verificar variáveis de ambiente
docker exec recommendations-system env | grep -E 'INSTAGRAM|OPENAI|DATABASE'
```

### Erro de conexão com banco
```bash
# Verificar se PostgreSQL está acessível
docker exec recommendations-system pg_isready -h postgres -p 5432
```

### Erro de conexão com Redis
```bash
# Verificar Redis
docker exec recommendations-system redis-cli -h redis ping
```
