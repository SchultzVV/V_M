# 🎯 Instagram Personalized Promos - Sistema de Recomendações

Sistema de recomendação personalizado que usa **Instagram como fonte de enriquecimento** para personalizar ofertas de produtos.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway :8000                     │
│                     (Ponto de entrada único)                 │
└────────┬─────────────┬──────────────┬──────────────┬────────┘
         │             │              │              │
    ┌────▼────┐  ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │  Auth   │  │ Ingest  │   │ Track   │   │  Recs   │
    │ Service │  │ Service │   │ Service │   │ Service │
    │  :8001  │  │  :8002  │   │  :8003  │   │  :8005  │
    └────┬────┘  └────┬────┘   └────┬────┘   └────┬────┘
         │            │              │              │
    ┌────▼────────────▼──────────────▼──────────────▼────┐
    │             PostgreSQL (Users, Events, Profiles)    │
    └─────────────────────────────────────────────────────┘
         │            │              │              │
    ┌────▼────┐  ┌────▼────┐   ┌────▼────┐        │
    │  Redis  │  │  Kafka  │   │ Profile │        │
    │  Cache  │  │  Events │   │ Builder │        │
    └─────────┘  └─────────┘   └─────────┘        │
                                      │            │
                                 ┌────▼────────────▼────┐
                                 │ OpenAI Embeddings     │
                                 └───────────────────────┘
```

## 🎯 Objetivo do MVP

Provar valor de **personalização** (CTR > baseline) usando:

✅ Texto do Instagram (com consentimento)  
✅ Eventos próprios (cliques, impressões)  
✅ Ranking simples + cache  
✅ Zero scraping ilegal  
✅ Zero overengineering

**Target de latência:** < 150ms para recomendações

---

## 📦 Serviços

### 1. **Auth & Consent Service** (:8001)
- OAuth Instagram Graph API
- Gerencia consentimento do usuário
- Armazena tokens de acesso

**Endpoints:**
- `POST /auth/instagram` - Autenticar usuário
- `GET /auth/status/{user_id}` - Status do consentimento
- `POST /auth/revoke/{user_id}` - Revogar consentimento

### 2. **Ingest Service** (:8002)
- Coleta bio + últimas captions do Instagram
- Rate-limited (1 ingest/hora por usuário)
- Respeita consentimento

**Endpoints:**
- `POST /ingest` - Coletar dados do Instagram
- `GET /ingest/history/{user_id}` - Histórico de ingests

### 3. **Tracking Service** (:8003)
- Rastreia eventos: IMPRESSION, CLICK, PURCHASE
- Publica eventos no Kafka
- Assíncrono e rápido

**Endpoints:**
- `POST /track` - Rastrear evento
- `POST /track/batch` - Rastrear múltiplos eventos

### 4. **Profile Builder** (batch/consumer)
- Consome eventos do Kafka
- Gera embeddings usando OpenAI
- Agrega estatísticas de cliques
- Pode rodar em modo batch ou consumer

### 5. **Recommendations Service** (:8005)
- Ranking híbrido (similaridade + boost)
- Cache Redis (hot path)
- Latência < 150ms

**Endpoints:**
- `GET /recommendations?user_id=X` - Obter recomendações
- `POST /recommendations/invalidate/{user_id}` - Invalidar cache

### 6. **API Gateway** (:8000)
- Ponto de entrada unificado
- Roteamento para serviços
- Logging e monitoramento

---

## 🚀 Setup & Execução

### Pré-requisitos

- Docker & Docker Compose
- Credenciais do Instagram App
- OpenAI API Key

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com suas credenciais
```

### 2. Iniciar todos os serviços

```bash
docker-compose -f docker-compose.recommendations.yaml up --build
```

Isso vai iniciar:
- PostgreSQL (porta 5432)
- Redis (porta 6379)
- Kafka + Zookeeper (porta 9092)
- 5 microserviços (portas 8000-8005)

### 3. Verificar saúde dos serviços

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

### 4. Acessar documentação interativa

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📖 Fluxo de Uso

### 1️⃣ Autenticar usuário no Instagram

```bash
# Usuário autoriza no Instagram e obtém code
POST http://localhost:8000/auth/instagram
{
  "code": "instagram_auth_code",
  "redirect_uri": "http://localhost:8000/auth/callback"
}

# Response:
{
  "user_id": "uuid-123",
  "instagram_id": "17841...",
  "access_token": "IGQ...",
  "expires_at": "2026-03-31T..."
}
```

### 2️⃣ Coletar dados do Instagram (ingest)

```bash
POST http://localhost:8000/ingest
{
  "user_id": "uuid-123"
}

# Response:
{
  "user_id": "uuid-123",
  "profile": {
    "instagram_id": "17841...",
    "username": "johndoe",
    "bio": "Fashion lover 👗 Tech enthusiast 💻",
    "followers_count": 1500
  },
  "captions": [
    {
      "media_id": "...",
      "caption": "New sneakers! Love the style",
      "timestamp": "2026-01-30T..."
    }
  ],
  "ingested_at": "2026-01-31T..."
}
```

### 3️⃣ Construir perfil (executar profile builder)

```bash
# Rodar em modo batch (manualmente ou via cron)
docker exec profile-builder python main.py batch

# Ou deixar rodando em modo consumer (já está no docker-compose)
```

### 4️⃣ Rastrear eventos

```bash
# Quando usuário vê produtos
POST http://localhost:8000/track
{
  "user_id": "uuid-123",
  "event_type": "impression",
  "item_id": "product-456"
}

# Quando usuário clica
POST http://localhost:8000/track
{
  "user_id": "uuid-123",
  "event_type": "click",
  "item_id": "product-456"
}
```

### 5️⃣ Obter recomendações personalizadas

```bash
GET http://localhost:8000/recommendations?user_id=uuid-123&limit=10

# Response (< 150ms):
{
  "user_id": "uuid-123",
  "items": [
    {
      "product_id": "product-789",
      "score": 0.87,
      "reason": "Match 85% + 20% OFF",
      "metadata": {
        "title": "Wireless Headphones",
        "price": 199.90,
        "discount": 20
      }
    }
  ],
  "cache_hit": false,
  "generated_at": "2026-01-31T..."
}
```

---

## 🧪 Dados de Teste

### Adicionar produtos de exemplo

```python
# Script para popular banco com produtos
import psycopg2
import json

conn = psycopg2.connect("postgresql://user:password@localhost:5432/recommendations_db")
cur = conn.cursor()

# Inserir produtos
products = [
    ("prod-1", "Wireless Headphones", "High quality sound", 199.90, 20, "electronics"),
    ("prod-2", "Running Shoes", "Comfortable and stylish", 149.90, 15, "fashion"),
    ("prod-3", "Smartwatch", "Track your fitness", 299.90, 25, "electronics"),
]

for p in products:
    cur.execute("""
        INSERT INTO products (id, title, description, price, discount, category, tags)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (*p, json.dumps([])))

conn.commit()
```

---

## 📊 KPIs do MVP

| Métrica | Target | Como Medir |
|---------|--------|------------|
| **Latência de recomendações** | < 150ms | Logs do serviço |
| **CTR personalizado vs genérico** | > baseline | A/B test (fase 2) |
| **Cobertura de personalização** | > 80% | % usuários com perfil |
| **Taxa de ingest com sucesso** | > 95% | Logs do ingest service |

---

## 🛠️ Desenvolvimento

### Rodar serviço individualmente

```bash
# Auth Service
cd services/auth-service
pip install -r requirements.txt
DATABASE_URL=postgresql://... uvicorn main:app --reload --port 8001

# Ingest Service
cd services/ingest-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

### Acessar banco de dados

```bash
docker exec -it postgres-db psql -U user -d recommendations_db

# Ver usuários
SELECT * FROM users;

# Ver eventos
SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;

# Ver perfis
SELECT user_id, last_updated, click_stats FROM profiles;
```

### Acessar Redis

```bash
docker exec -it redis-cache redis-cli

# Ver chaves
KEYS rec:*

# Ver valor
GET rec:user:uuid-123
```

### Acessar Kafka

```bash
# Listar tópicos
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Consumir eventos
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic user-events \
  --from-beginning
```

---

## 📝 Próximos Passos (Fase 2)

- [ ] A/B testing framework
- [ ] GraphQL API (além de REST)
- [ ] Anti coupon leakage (rate-limit avançado)
- [ ] Observabilidade (Prometheus, Grafana)
- [ ] Feature store mais robusto
- [ ] Webhooks para eventos do Instagram
- [ ] Multi-tenancy
- [ ] ML models mais sofisticados

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/amazing`)
3. Commit suas mudanças (`git commit -m 'Add amazing feature'`)
4. Push para a branch (`git push origin feature/amazing`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto é proprietário e confidencial.

---

## 💡 Decisões de Arquitetura

### Por que microsserviços?

✅ **Escalabilidade independente** - Recommendations pode escalar diferente do Ingest  
✅ **Deploy isolado** - Bug em um serviço não afeta outros  
✅ **Clareza** - Cada serviço tem responsabilidade única  
✅ **Tecnologias diferentes** - Cada serviço pode usar stack ideal

### Por que Kafka?

✅ **Desacoplamento** - Serviços não precisam se conhecer  
✅ **Resiliência** - Eventos não são perdidos  
✅ **Replay** - Pode reprocessar eventos históricos  
✅ **Scale** - Milhões de eventos/seg no futuro

### Por que Redis?

✅ **Hot path** - Cache de recomendações em memória  
✅ **Latência** - Sub-milisegundo  
✅ **Rate limiting** - Locks distribuídos para ingest

### Por que OpenAI Embeddings?

✅ **Simplicidade** - Não precisa treinar modelo  
✅ **Qualidade** - Estado da arte  
✅ **Rapidez** - Para MVP, perfeito  
💡 **Futuro** - Pode trocar por modelo próprio depois

---

**Feito com 💙 por V_M Team**
