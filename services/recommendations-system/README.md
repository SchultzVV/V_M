# 🎯 Recommendations System - Unified Image

Sistema de recomendações personalizadas consolidado em uma **única imagem Docker**.

## 📦 O que está incluído

Esta imagem contém **6 serviços** integrados:

1. **API Gateway** (:8000) - Ponto de entrada unificado
2. **Auth Service** (:8001) - OAuth Instagram
3. **Ingest Service** (:8002) - Coleta dados do Instagram
4. **Tracking Service** (:8003) - Rastreamento de eventos
5. **Recommendations Service** (:8005) - Geração de recomendações
6. **Profile Builder** - Job batch/consumer (Kafka)

## 🚀 Build & Push para Registry

### 1. Build da imagem

```bash
cd services/recommendations-system
docker build -t recommendations-system:latest .
```

### 2. Tag para registry

```bash
# Para Docker Hub
docker tag recommendations-system:latest seuusuario/recommendations-system:latest

# Para registry privado
docker tag recommendations-system:latest registry.example.com/recommendations-system:latest
```

### 3. Push para registry

```bash
# Docker Hub
docker push seuusuario/recommendations-system:latest

# Registry privado
docker push registry.example.com/recommendations-system:latest
```

## 🔧 Usar no Site (docker-compose)

Adicione ao `docker-compose.yaml` do seu site:

```yaml
version: '3.8'

services:
  # Infraestrutura necessária
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: recommendations_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    networks:
      - app-network

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    depends_on:
      - zookeeper
    networks:
      - app-network

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    networks:
      - app-network

  # Sistema de Recomendações (IMAGEM ÚNICA)
  recommendations:
    image: seuusuario/recommendations-system:latest
    ports:
      - "8000:8000"  # API Gateway
      - "8001:8001"  # Auth
      - "8002:8002"  # Ingest
      - "8003:8003"  # Tracking
      - "8005:8005"  # Recommendations
    environment:
      SERVICE: all  # Inicia todos os serviços
      DATABASE_URL: postgresql://user:password@postgres:5432/recommendations_db
      REDIS_URL: redis://redis:6379/0
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      INSTAGRAM_APP_ID: ${INSTAGRAM_APP_ID}
      INSTAGRAM_APP_SECRET: ${INSTAGRAM_APP_SECRET}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
      - kafka
    networks:
      - app-network
    restart: unless-stopped

  # Seu site existente
  site:
    build: ./services/site
    ports:
      - "8080:8080"
    environment:
      RECOMMENDATIONS_API_URL: http://recommendations:8000
    depends_on:
      - recommendations
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

## 🎛️ Iniciar serviços específicos

Você pode iniciar apenas serviços específicos usando a variável `SERVICE`:

```yaml
# Apenas API Gateway
recommendations-api:
  image: seuusuario/recommendations-system:latest
  environment:
    SERVICE: api
  ports:
    - "8000:8000"

# Apenas Profile Builder
recommendations-builder:
  image: seuusuario/recommendations-system:latest
  environment:
    SERVICE: profile_builder
```

Serviços disponíveis:
- `all` - Todos os serviços (padrão)
- `api` - API Gateway apenas
- `auth` - Auth Service apenas
- `ingest` - Ingest Service apenas
- `tracking` - Tracking Service apenas
- `recommendations` - Recommendations Service apenas
- `profile_builder` - Profile Builder apenas

## 📡 Endpoints disponíveis

Quando o serviço estiver rodando, a API estará disponível em:

```
http://localhost:8000
```

### Principais endpoints:

```bash
# Health check
GET http://localhost:8000/health

# Autenticação Instagram
POST http://localhost:8000/auth/instagram

# Ingest de dados
POST http://localhost:8000/ingest

# Rastrear evento
POST http://localhost:8000/track

# Obter recomendações
GET http://localhost:8000/recommendations?user_id=X&limit=10
```

Documentação interativa: http://localhost:8000/docs

## 🔧 Variáveis de Ambiente

Obrigatórias:

```env
INSTAGRAM_APP_ID=your_app_id
INSTAGRAM_APP_SECRET=your_app_secret
OPENAI_API_KEY=your_openai_key
```

Opcionais (têm defaults):

```env
DATABASE_URL=postgresql://user:password@postgres:5432/recommendations_db
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_CACHE_TTL=3600
RECOMMENDATION_LATENCY_TARGET_MS=150
```

## 🧪 Testar localmente

```bash
# Build
docker build -t recommendations-system:latest .

# Run (todos os serviços)
docker run -p 8000:8000 -p 8001:8001 -p 8002:8002 -p 8003:8003 -p 8005:8005 \
  -e INSTAGRAM_APP_ID=your_id \
  -e INSTAGRAM_APP_SECRET=your_secret \
  -e OPENAI_API_KEY=your_key \
  -e DATABASE_URL=postgresql://user:password@host.docker.internal:5432/db \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  -e KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
  recommendations-system:latest

# Run (apenas API Gateway)
docker run -p 8000:8000 \
  -e SERVICE=api \
  recommendations-system:latest

# Health check
curl http://localhost:8000/health
```

## 📊 Logs

Os logs de todos os serviços aparecem no stdout do container:

```bash
docker logs -f <container_id>
```

## 🔍 Troubleshooting

### Container não inicia

Verifique as variáveis de ambiente e conexões com PostgreSQL, Redis e Kafka.

```bash
docker logs <container_id>
```

### Serviço específico com erro

Inicie os serviços individualmente para debug:

```bash
docker run -e SERVICE=auth recommendations-system:latest
```

### Health check falhando

Verifique se o PostgreSQL, Redis e Kafka estão acessíveis e saudáveis.

## 📝 Integração com o Site

No seu código Python do site:

```python
import httpx

RECOMMENDATIONS_API = "http://recommendations:8000"

async def get_recommendations(user_id: str, limit: int = 10):
    """Busca recomendações personalizadas"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{RECOMMENDATIONS_API}/recommendations",
            params={"user_id": user_id, "limit": limit},
            timeout=5.0
        )
        return response.json()

async def track_click(user_id: str, product_id: str):
    """Rastreia clique em produto"""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{RECOMMENDATIONS_API}/track",
            json={
                "user_id": user_id,
                "event_type": "click",
                "item_id": product_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

## 🎯 Arquitetura

```
┌─────────────────────────────────────────────────┐
│   Docker Container: recommendations-system      │
│                                                 │
│   ┌─────────────────────────────────────────┐  │
│   │  API Gateway :8000                      │  │
│   └──────────┬──────────────────────────────┘  │
│              │                                  │
│   ┌──────────┼──────────────┬─────────────┐    │
│   │          │              │             │    │
│   ▼          ▼              ▼             ▼    │
│ ┌────┐   ┌────┐        ┌────┐        ┌────┐   │
│ │Auth│   │Ing │        │Trk │        │Recs│   │
│ └────┘   └────┘        └────┘        └────┘   │
│   │          │              │             │    │
│   └──────────┴──────────────┴─────────────┘    │
│              │                                  │
│   ┌──────────▼───────────┐                     │
│   │  Profile Builder     │                     │
│   └──────────────────────┘                     │
└─────────────────────────────────────────────────┘
         │            │              │
    ┌────▼────┐  ┌────▼────┐    ┌───▼────┐
    │Postgres │  │  Redis  │    │ Kafka  │
    └─────────┘  └─────────┘    └────────┘
```

---

**Pronto para produção! 🚀**
