# 📦 Sistema de Recomendações - Imagem Docker Única

## ✅ O que foi criado

Todo o sistema de recomendações personalizadas foi **consolidado em uma única pasta** pronto para ser transformado em uma **imagem Docker única**.

### 📂 Localização

```
services/recommendations-system/
```

### 🎯 Estrutura Final

```
services/recommendations-system/
├── api/                    # API Gateway (:8000)
│   ├── __init__.py
│   └── main.py
├── auth/                   # Auth & Consent Service (:8001)
│   ├── __init__.py
│   └── main.py
├── ingest/                 # Ingest Service (:8002)
│   ├── __init__.py
│   └── main.py
├── tracking/               # Tracking Service (:8003)
│   ├── __init__.py
│   └── main.py
├── recommendations/        # Recommendations Service (:8005)
│   ├── __init__.py
│   └── main.py
├── profile_builder/        # Profile Builder (Kafka consumer)
│   ├── __init__.py
│   └── main.py
├── shared/                 # Módulos compartilhados
│   ├── config.py          # Configurações
│   ├── database.py        # Models SQLAlchemy
│   ├── schemas.py         # Pydantic schemas
│   ├── redis_client.py    # Cliente Redis
│   ├── kafka_client.py    # Cliente Kafka
│   └── __init__.py
├── main.py                 # Entry point principal
├── Dockerfile              # 🔥 Dockerfile único
├── requirements.txt        # Dependências consolidadas
├── build.sh               # Script de build & push
├── .dockerignore
├── README.md              # Documentação completa
└── docker-compose.site-integration.yaml  # Exemplo para o site
```

## 🚀 Como usar

### 1. Build da imagem

```bash
cd services/recommendations-system

# Build local
./build.sh

# Build e push para registry
export DOCKER_USER="seuusuario"
export DOCKER_REGISTRY="docker.io"  # ou registry privado
./build.sh --push
```

### 2. Integração no site

Adicione ao `docker-compose.yaml` do site:

```yaml
services:
  recommendations:
    image: seuusuario/recommendations-system:latest
    ports:
      - "8000:8000"
    environment:
      SERVICE: all  # Todos os serviços
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
```

### 3. Usar no código do site

```python
import httpx

RECOMMENDATIONS_API = "http://recommendations:8000"

# Obter recomendações
async def get_recommendations(user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{RECOMMENDATIONS_API}/recommendations",
            params={"user_id": user_id, "limit": 10}
        )
        return response.json()

# Rastrear clique
async def track_click(user_id: str, product_id: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{RECOMMENDATIONS_API}/track",
            json={
                "user_id": user_id,
                "event_type": "click",
                "item_id": product_id
            }
        )
```

## 📊 Serviços incluídos

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| **API Gateway** | 8000 | Ponto de entrada unificado |
| **Auth Service** | 8001 | OAuth Instagram |
| **Ingest Service** | 8002 | Coleta dados do Instagram |
| **Tracking Service** | 8003 | Rastreia eventos (clicks, impressões) |
| **Recommendations Service** | 8005 | Gera recomendações personalizadas |
| **Profile Builder** | - | Job batch/consumer Kafka |

## 🎛️ Variáveis de ambiente

### Obrigatórias

```env
INSTAGRAM_APP_ID=seu_app_id
INSTAGRAM_APP_SECRET=seu_app_secret
OPENAI_API_KEY=sua_chave_openai
```

### Opcionais (têm defaults)

```env
SERVICE=all                           # all, api, auth, ingest, tracking, recommendations, profile_builder
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_CACHE_TTL=3600
RECOMMENDATION_LATENCY_TARGET_MS=150
```

## 🧪 Testar localmente

```bash
# Build
docker build -t recommendations-system:latest .

# Run
docker run -p 8000:8000 \
  -e INSTAGRAM_APP_ID=your_id \
  -e INSTAGRAM_APP_SECRET=your_secret \
  -e OPENAI_API_KEY=your_key \
  recommendations-system:latest

# Health check
curl http://localhost:8000/health
```

## 📦 Push para registry

### Docker Hub

```bash
export DOCKER_USER="seuusuario"
./build.sh --push
```

### Registry privado

```bash
export DOCKER_REGISTRY="registry.example.com"
export DOCKER_USER="team"
./build.sh --push
```

Imagem ficará disponível em:
- Docker Hub: `docker.io/seuusuario/recommendations-system:latest`
- Registry privado: `registry.example.com/team/recommendations-system:latest`

## 🔗 Endpoints principais

```bash
# Documentação interativa
http://localhost:8000/docs

# Health check
GET /health

# Autenticação
POST /auth/instagram
GET /auth/status/{user_id}
POST /auth/revoke/{user_id}

# Ingest
POST /ingest

# Tracking
POST /track
POST /track/batch

# Recomendações
GET /recommendations?user_id=X&limit=10
POST /recommendations/invalidate/{user_id}
```

## 💡 Benefícios da abordagem

✅ **Imagem única** - Fácil de versionar e distribuir  
✅ **Registry pronto** - Push e pull simplificados  
✅ **Flexível** - Pode rodar todos os serviços ou apenas alguns  
✅ **Isolado** - Não interfere com outros serviços do site  
✅ **Escalável** - Pode ser replicado facilmente  
✅ **Documentado** - README completo com exemplos  

## 🎯 Próximos passos

1. Configure as credenciais do Instagram e OpenAI
2. Build a imagem: `./build.sh`
3. Push para registry: `./build.sh --push`
4. Integre no docker-compose do site
5. Use os endpoints no seu código

## 📝 Arquivos importantes

- **README.md** - Documentação completa do sistema
- **Dockerfile** - Imagem Docker otimizada
- **build.sh** - Script para build e push
- **docker-compose.site-integration.yaml** - Exemplo de integração
- **main.py** - Entry point que inicia todos os serviços

---

**Sistema pronto para produção! 🚀**
