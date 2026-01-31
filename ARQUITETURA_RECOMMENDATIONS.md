# 🏗️ Arquitetura do Sistema de Recomendações

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT / FRONTEND                          │
│                      (Site, App, Instagram Bio)                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY :8000                             │
│                     (Roteamento + Logging)                           │
└──────┬──────────────┬──────────────┬──────────────┬─────────────────┘
       │              │              │              │
       │ HTTP         │ HTTP         │ HTTP         │ HTTP
       ▼              ▼              ▼              ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐
│   AUTH   │   │  INGEST  │   │ TRACKING │   │ RECOMMENDA-  │
│ SERVICE  │   │ SERVICE  │   │ SERVICE  │   │ TIONS SVC    │
│  :8001   │   │  :8002   │   │  :8003   │   │    :8005     │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └──────┬───────┘
     │              │              │                 │
     │              │              │                 │
     ▼              ▼              ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         POSTGRESQL :5432                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │
│  │  Users   │  │  Events  │  │ Profiles │  │   Products   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
     │              │                             │
     │              │                             │
     ▼              ▼                             ▼
┌──────────┐   ┌──────────────────────┐   ┌──────────────┐
│  REDIS   │   │       KAFKA          │   │   PROFILE    │
│  :6379   │   │       :9092          │   │   BUILDER    │
│          │   │                      │   │              │
│ (Cache)  │   │  Topics:             │   │ (Consumer +  │
│          │   │  - user-events       │   │  Batch Job)  │
│          │   │  - user-profiles     │   │              │
└──────────┘   └──────────────────────┘   └──────┬───────┘
                                                  │
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │   OPENAI     │
                                          │  Embeddings  │
                                          │              │
                                          └──────────────┘
```

## Fluxo de Dados

### 1️⃣ Autenticação (Auth Flow)

```
User → API Gateway → Auth Service → Instagram Graph API
                         │
                         ▼
                   PostgreSQL (users)
```

### 2️⃣ Ingest (Data Collection)

```
User → API Gateway → Ingest Service → Instagram Graph API
                         │                  (bio + captions)
                         ├─→ PostgreSQL (ingest_logs)
                         └─→ Redis (rate limit lock)
```

### 3️⃣ Tracking (Events)

```
User → API Gateway → Tracking Service → Kafka (user-events topic)
                                            │
                                            ▼
                                     Profile Builder
                                            │
                                            ▼
                                   PostgreSQL (events)
```

### 4️⃣ Profile Building (Batch/Stream)

```
Kafka (events) → Profile Builder → OpenAI (embeddings)
                      │                      │
                      ▼                      ▼
            PostgreSQL (profiles) ← Embedding Vector
                      │
                      └─→ Kafka (user-profiles topic)
```

### 5️⃣ Recommendations (Hot Path)

```
User → API Gateway → Recommendations Service
                            │
                            ├─→ Redis (cache) → HIT? → Return
                            │                     │
                            └─→ PostgreSQL ←──────┘
                                  (profiles + products)
                                  │
                                  ├─→ Similarity Calculation
                                  ├─→ Boosting (discount, clicks)
                                  ├─→ Ranking
                                  │
                                  └─→ Redis (cache result)
                                  └─→ Return to User
```

## Tecnologias

### Backend Services
- **FastAPI** - Framework web assíncrono
- **Pydantic** - Validação de dados
- **SQLAlchemy** - ORM para PostgreSQL

### Infraestrutura
- **PostgreSQL** - Banco de dados relacional
- **Redis** - Cache in-memory
- **Kafka** - Event streaming
- **Docker** - Containerização

### Machine Learning
- **OpenAI Embeddings** - text-embedding-3-small
- **NumPy** - Cálculo de similaridade (cosine)

### Integração
- **Instagram Graph API** - Coleta de dados
- **httpx** - Cliente HTTP assíncrono

## Padrões de Design

### Microsserviços
- Cada serviço tem responsabilidade única (SRP)
- Comunicação via REST/HTTP
- Desacoplamento via event bus (Kafka)

### Cache Strategy
- **Cache-Aside Pattern** (Lazy Loading)
- TTL: 1 hora (configurável)
- Invalidação sob demanda

### Event-Driven
- **Publisher/Subscriber** via Kafka
- Processamento assíncrono
- Garantia de entrega (at-least-once)

### API Gateway Pattern
- Ponto de entrada único
- Roteamento centralizado
- Logging e monitoramento

## Segurança

### Autenticação
- OAuth 2.0 com Instagram
- Tokens JWT (futuro)
- Scopes granulares

### Dados Sensíveis
- Tokens criptografados no banco
- Consentimento explícito do usuário
- Revogação de acesso

### Rate Limiting
- Instagram API: 200 req/hora
- Ingest cooldown: 1 hora
- Redis locks distribuídos

## Performance

### Targets
- **Recomendações**: < 150ms
- **Tracking**: < 50ms (fire-and-forget)
- **Ingest**: < 5s

### Otimizações
- Cache em múltiplas camadas
- Queries otimizadas (índices)
- Connection pooling
- Async/await everywhere

## Escalabilidade

### Horizontal Scaling
- Cada serviço pode escalar independentemente
- Load balancer na frente do API Gateway
- Kafka partitions para paralelismo

### Vertical Scaling
- PostgreSQL: Aumentar CPU/RAM
- Redis: Cluster mode
- Kafka: Adicionar brokers

## Monitoramento (Fase 2)

### Métricas
- Latência por endpoint
- Taxa de erro
- Cache hit rate
- Throughput de eventos

### Logs
- Estruturados (JSON)
- Centralizados (ELK/Loki)
- Correlation IDs

### Alertas
- Latência > target
- Error rate > 5%
- Serviço down
