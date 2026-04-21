# MAPA DE AGENTES — V_M

> Visão geral de todos os agentes do sistema, suas responsabilidades, ferramentas e fluxos de colaboração.

---

## Índice

1. [Agentes de Orquestração](#agentes-de-orquestracao)
2. [Agentes Especialistas](#agentes-especialistas)
3. [Agentes de Pipeline](#agentes-de-pipeline)
   - ml_populator · product_decision · product_enricher · instagram_poster · instagram_orchestrator · tag_classifier · price_oracle · reprice_all
4. [Fluxo de Colaboração](#fluxo-de-colaboracao)
5. [Mapa de Ferramentas por Agente](#mapa-de-ferramentas-por-agente)

---

## Agentes de Orquestração

### `techlead`
**Arquivo:** `agents/techlead.agent.md`
**Perfil:** Staff+ Tech Lead — não codifica diretamente; planeja, delega, decide arquitetura.

| Responsabilidade | Detalhes |
|---|---|
| Quebrar tarefas complexas | Divide em subtarefas para `backend`, `frontend`, `tunelador` |
| Decisões arquiteturais | Nginx 443 como entry point, dois frontends, pipelines |
| Consistência do sistema | Garante que endpoints.md, ports.md, services.md estejam sincronizados |
| Prevenir dívida técnica | Revisão de blueprints, DRY principle |
| Orquestrar pipeline de dados | `populate-mf → price-oracle → tag-classify-db → publish` |

**Ferramentas / Inputs:**
- `agents/shared/endpoints.md` — Contrato de API
- `agents/shared/make_commands.md` — Comandos disponíveis
- `agents/shared/services.md` — Arquitetura de serviços
- `agents/shared/ports.md` — Mapa de portas

---

## Agentes Especialistas

### `backend`
**Arquivo:** `agents/backend.agent.md`
**Perfil:** Senior Flask Engineer — API, banco, integrações, segurança.

| Responsabilidade | Detalhes |
|---|---|
| Endpoints Flask | 8 blueprints: `product_bp`, `auth_bp`, `sync_bp`, `webhook_bp`, `instagram_bp`, `price_validator_bp`, `media_bp`, `ai_bp` |
| Banco de dados | PostgreSQL 5432 — migrations, SQLAlchemy, `unaccent` extension |
| API `/api/products` | Retorna `{items, total, page, pages, limit}` — paginado |
| Busca accent-insensitive | `func.unaccent()` (Postgres) + `_strip_accents()` (Python NFD) |
| OAuth Mercado Livre | `ML_REDIRECT_URI` via Cloudflare tunnel |
| Integrações externas | ML API, Shopee, Amazon, Instagram Graph API |
| Cache | Redis 6379 — listagens, pub/sub |
| Armazenamento de mídia | MinIO (bucket `products`) — acessado via `/media/*` |
| RAG / Vector DB | Qdrant 6333 — `ai_bp` blueprint |
| Templates Jinja2 | `services/site/templates/` — `index.html`, `secao1-4.html` (site live) |

**Ferramentas (stack):**
```
Flask 3.x        PostgreSQL+unaccent  SQLAlchemy  Redis  MinIO
Qdrant           unicodedata (NFD)    JWT         OAuth2
info-scrap:8001  ingestion:5003       retrieval:5004
```

**Arquivos-chave:**
- `services/site/main.py` — app factory, `unaccent` activation
- `services/site/routes/product_routes.py` — paginação + busca acento-insensível
- `services/site/static/def-design.css` — design system (section-dividers)
- `services/site/templates/index.html` — agrupamento por tag com dividers
- `services/site/templates/secao1-4.html` — agrupamento por subtag

---

### `frontend`
**Arquivo:** `agents/frontend.agent.md`
**Perfil:** Senior React Engineer — UI/UX, componentes, estado, integração com API.

| Responsabilidade | Detalhes |
|---|---|
| **Dois Frontends** | |
| Jinja2 (live site) | `services/site/templates/` — HTML + vanilla JS + def-design.css. É o que os usuários veem |
| React SPA (admin) | `frontend/` — Vite + React 18 + TS + Tailwind + Zustand. Build em `frontend/dist/` |
| Section dividers | Sticky dividers por tag (index.html) e subtag (secao1-4.html) — `position: sticky; top: 0; grid-column: 1/-1` |
| Padrão de API | `data.items \|\| data` — compatível com resposta paginada `{items, total, page, pages, limit}` |
| Design system | DEF brutalism: `--neon-green #00ff41`, `--black-deep #0a0a0a`, zero border-radius, IBM Plex Mono |

**Ferramentas (stack):**
```
Jinja2 + vanilla JS    def-design.css (CSS tokens)    IBM Plex Mono + Inter
React 18 + TypeScript  Vite          Tailwind CSS     Zustand
Vitest                 PostCSS
```

**Arquivos-chave:**
- `services/site/static/def-design.css` — tokens CSS, `.section-divider`
- `services/site/templates/index.html` — `TAG_META`, `TAG_ORDER`, `displayProducts()`
- `services/site/templates/secao1-4.html` — `SUBCAT_META`, `SUBCAT_ORDER`, `filterBySubcategory()`
- `frontend/src/` — React SPA

---

### `tunelador`
**Arquivo:** `agents/tunelador.agent.md`
**Perfil:** DevOps Engineer — tunnels, Nginx, OAuth, portas, exposição pública.

| Responsabilidade | Detalhes |
|---|---|
| Entry point público | Nginx 443 (HTTPS) — `nginx-react` container |
| Cloudflare Tunnel | cloudflared → Nginx 443 → Flask 5000 |
| OAuth redirect URI | `ML_REDIRECT_URI` configurado para URL pública do tunnel |
| Roteamento Nginx | `/*` → React/Jinja2; `/api/*`, `/auth/*`, `/media/*` → Flask |
| Saúde dos serviços | `make tunnel-info`, monitoramento de portas |
| Métodos de tunnel | Method 1: Loop fixo; Method 2: Daemon; Method 3: React+Nginx |

**Ferramentas:**
```
cloudflared    Nginx (nginx-react container)    docker-compose
.env           OAuth2 ML                        make tunnel-info
```

**Portas do sistema:**
| Porta | Serviço | Visibilidade |
|---|---|---|
| 443 | Nginx (HTTPS) | Público via Cloudflare |
| 5000 | Flask (interno) | Apenas Docker network |
| 5555 | Flask direto | Debug local apenas |
| 5173 | React Vite dev | Local apenas |
| 5432 | PostgreSQL | Apenas Docker network |
| 6379 | Redis | Apenas Docker network |
| 6333/6334 | Qdrant | Apenas Docker network |
| 9000/9001 | MinIO | Apenas Docker network |
| 8001 | info-scrap | Apenas Docker network |

---

## Agentes de Pipeline

Todos os agentes Python vivem em `services/site/agents/`. Há uma `BaseAgent` abstrata que todos herdam.

**Base:** `services/site/agents/__init__.py` — `BaseAgent(ABC)` com LLM (LangChain + OpenAI), Redis cache, e interface `run()` padrão.

---

### `ml_populator_agent`
**Arquivo:** `services/site/agents/ml_populator_agent.py`
**Acionado por:** `make populate-mf`
**Função:** Popula o site com produtos do ML, tag por tag, subtag por subtag.

| Etapa | Ação |
|---|---|
| 1. Busca ML | `GET /sites/MLB/search?q={query}&sort=sold_quantity` → top 5 mais vendidos |
| 2. Dedup | Verifica se `external_id` já existe no banco |
| 3. Cheapest seller | Para cada produto, encontra o vendedor mais barato |
| 4. Affiliate link | Gera link de afiliado para o mais barato |
| 5. Prepare + Stage | Baixa imagens, insere PostgreSQL (staging) + upload MinIO |

**Ferramentas:** ML API, MinIO, PostgreSQL, `info-scrap:8001`

---

### `product_decision_agent`
**Arquivo:** `services/site/agents/product_decision_agent.py`
**Instanciado por:** `instagram_orchestrator`
**Função:** Seleciona o melhor produto do staging para postar no Instagram.

| Critério | Descrição |
|---|---|
| LLM scoring | Usa LangChain + OpenAI para ranquear candidatos do staging |
| Inputs | Arquivos JSON em `/app/staging/`, histórico Redis |
| Output | Produto selecionado com justificativa para o próximo nó do grafo |

**Ferramentas:** PostgreSQL, Redis (cache), LangChain, OpenAI, LangGraph state

---

### `product_enricher_agent`
**Arquivo:** `services/site/agents/product_enricher_agent.py`
**Instanciado por:** `instagram_orchestrator`
**Função:** Enriquece os dados do produto e prepara descrição otimizada para Instagram.

| Ação | Descrição |
|---|---|
| Enriquecimento | Gera título, descrição, hashtags com LLM |
| Otimização IG | Copywriting para caption do Instagram |
| Cache | Salva resultado no Redis para evitar reprocessamento |

**Ferramentas:** LangChain, OpenAI, Redis

---

### `instagram_poster_agent`
**Arquivo:** `services/site/agents/instagram_poster_agent.py`
**Instanciado por:** `instagram_orchestrator`
**Função:** Gera imagem com OpenCV e posta automaticamente no Instagram.

| Ação | Descrição |
|---|---|
| Geração de imagem | `InstagramImageGenerator` (cv2) — composição com produto, preço, marca |
| Post IG | Instagram Graph API — upload + publish |
| Feedback | Retorna post ID e métricas para o estado do grafo |

**Ferramentas:** OpenCV (cv2), Instagram Graph API, Redis

---

### `instagram_orchestrator`
**Arquivo:** `services/site/agents/instagram_orchestrator.py`
**Acionado por:** `make instagram-post` (via `instagram_bp`)
**Função:** Orquestrador LangGraph — conecta os 3 agentes acima em fluxo coordenado.

```
LangGraph StateGraph:
  decision_agent → enricher_agent → poster_agent → END

Estado compartilhado (InstagramPostState):
  - produto selecionado
  - dados enriquecidos
  - resultado da postagem
  - mensagens LLM (Annotated list com operador +)
```

**Ferramentas:** LangGraph, Redis, `ProductDecisionAgent`, `ProductEnricherAgent`, `InstagramPosterAgent`

---

### `tag_classifier_agent`
**Arquivo:** `services/site/agents/tag_classifier_agent.py`
**Acionado por:** `make tag-classify` (staging) / `make tag-classify-db` (banco)
**Função:** Classifica tag + subtag de produtos usando LLM (Ollama via `retrieval_service:5004`).

| Modo | Descrição |
|---|---|
| `--staging` (padrão) | Processa JSONs em `/app/staging/` |
| `--db` | Processa produtos do banco sem tag ou com tag "geral" |
| `--product-id ID` | Produto específico pelo ID |
| `--dry-run` | Mostra decisão sem aplicar |

**Ferramentas:** LLM via `retrieval_service:5004` (Ollama/hsmart), PostgreSQL, JSON staging files

---

### `price_oracle_agent`
**Arquivo:** `services/site/agents/price_oracle_agent.py`
**Acionado por:** `make price-oracle`
**Função:** Consolida até 4 fontes de preço e decide preço atual + desconto real via LLM.

| Fonte | Descrição |
|---|---|
| ML API | Preço atual do anúncio |
| Catálogo ML | Preço de catálogo / referência |
| DOM/Pix | Preço raspado da página (via info-scrap) |
| Histórico Qdrant | Preços anteriores (coleção `price_history`) |
| LLM decisor | `retrieval_service:5004` (Ollama) decide preço final |

**Ferramentas:** ML API, `info-scrap:8001`, Qdrant (`price_history`), Redis, `retrieval_service:5004`

---

### `reprice_all`
**Arquivo:** `services/site/agents/reprice_all.py`
**Acionado por:** `make reprice-all`
**Função:** Revisita todos os produtos publicados, atualiza preço via Price Oracle e limpa produtos com preço zerado.

| Flag | Ação |
|---|---|
| `--dry-run` | Mostra o que mudaria sem aplicar |
| `--fix-zero-only` | Apenas remove produtos com preço 0/vazio |
| `--batch-size N` | Processa N produtos por vez |

**Ferramentas:** `price_oracle_agent`, PostgreSQL, Redis

---

## Fluxo de Colaboração

### Fluxo: Nova Feature no Site
```
Usuário → @techlead
    ├── Análise arquitetural
    ├── Se envolve API → delega para @backend
    ├── Se envolve UI/templates → delega para @frontend
    └── Se envolve tunnel/deploy → delega para @tunelador
```

### Fluxo: Pipeline Completa (ML → Instagram)
```
make populate-mf
    → ml_populator_agent (ML busca → cheapest → MinIO + PostgreSQL)
      ↓
make price-oracle
    → price_oracle_agent (4 fontes → Qdrant price_history)
      ↓
make tag-classify-db
    → tag_classifier_agent (LLM → tag + subtag no banco)
      ↓
make prepare-and-publish
    → prepare_ml_best → stage_products (imagens MinIO, DB staging→published)
      ↓
make instagram-post
    → instagram_orchestrator (LangGraph):
        decision_agent → enricher_agent → poster_agent → Instagram
```

### Fluxo: Debug de Infra
```
Problema de acesso público → @tunelador
    ├── Tunnel morto? → make stop-all && make serve-cloudflare
    ├── 502 Bad Gateway? → Nginx → Flask connection
    └── OAuth falhou? → ML_REDIRECT_URI desatualizado
```

---

## Mapa de Ferramentas por Agente

| Ferramenta | `backend` | `frontend` | `tunelador` | `ml_populator` | `decision` | `enricher` | `poster` | `orchestrator` | `tag_classifier` | `price_oracle` | `reprice_all` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| PostgreSQL | ✅ | — | — | ✅ | ✅ | — | — | — | ✅ | ✅ | ✅ |
| Redis | ✅ | — | — | — | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| MinIO | ✅ | — | — | ✅ | — | — | — | — | — | — | — |
| Qdrant | ✅ | — | — | — | — | — | — | — | — | ✅ | — |
| ML API | ✅ | — | — | ✅ | — | — | — | — | — | ✅ | — |
| LangChain/OpenAI | — | — | — | — | ✅ | ✅ | — | ✅ | — | — | — |
| LangGraph | — | — | — | — | — | — | — | ✅ | — | — | — |
| Ollama (retrieval:5004) | — | — | — | — | — | — | — | — | ✅ | ✅ | — |
| Instagram Graph API | ✅ | — | — | — | — | — | ✅ | ✅ | — | — | — |
| OpenCV (cv2) | — | — | — | — | — | — | ✅ | — | — | — | — |
| info-scrap:8001 | ✅ | — | — | ✅ | — | — | — | — | — | ✅ | — |
| Nginx | — | — | ✅ | — | — | — | — | — | — | — | — |
| cloudflared | — | — | ✅ | — | — | — | — | — | — | — | — |
| OAuth2 ML | ✅ | — | ✅ | — | — | — | — | — | — | — | — |

---

## Conhecimento Compartilhado (`agents/shared/`)

| Arquivo | Conteúdo | Quem usa |
|---|---|---|
| `endpoints.md` | Todos os endpoints da API com request/response shape | Todos |
| `make_commands.md` | Todos os targets do Makefile explicados | Todos |
| `services.md` | Arquitetura de serviços, Nginx, dois frontends | Todos |
| `ports.md` | Mapa completo de portas, entry point Nginx 443 | backend, tunelador |

---

*Última atualização: sincronizado com arquitetura atual (Nginx 443, paginação de API, section dividers, busca accent-insensitive)*
