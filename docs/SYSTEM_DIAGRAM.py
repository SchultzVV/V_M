"""
DEF Site — Diagrama Completo do Sistema
Atualizado: 2026-04-15

Execute:  python3 docs/SYSTEM_DIAGRAM.py
"""

# ─────────────────────────────────────────────────────────────────────────────
# DIAGRAMA 1 — VISÃO GERAL DA ARQUITETURA
# ─────────────────────────────────────────────────────────────────────────────

OVERVIEW = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        DEF SITE — VISÃO GERAL DO SISTEMA                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

  FONTES EXTERNAS               PROCESSAMENTO                  SAÍDAS
  ─────────────────             ─────────────────              ──────────────

  Mercado Livre API ──┐
  Mercado Livre DOM ──┤         ┌───────────────┐
  Shopee (Playwright)─┤──────► │   PIPELINE    │──────────► PostgreSQL DB
  Amazon (Playwright)─┤         │  DE PRODUTO   │               │
  info-scrap (OCR)   ─┘         └───────────────┘               │
                                       │                         ▼
                                       │                    React Frontend
                                   /staging                 (via Nginx)
                                   JSON files                    │
                                       │                         ▼
   ML API Catálogo ─────────────►  make stage          Cloudflare Tunnel
   Playwright DOM  ─────────────►  (DB + MinIO)         (URL pública)
                                       │
                                       ▼
                               MinIO (imagens)
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │  AGENTES INSTAGRAM   │
                            │  (LangGraph)         │
                            └──────────────────────┘
                                       │
                                       ▼
                            Instagram (feed + story)
"""

# ─────────────────────────────────────────────────────────────────────────────
# DIAGRAMA 2 — PIPELINE DE PRODUTO (prepare → stage → site)
# ─────────────────────────────────────────────────────────────────────────────

PRODUCT_PIPELINE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║               PIPELINE DE PRODUTO  (prepare → stage → site)                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ENTRADA                    PREPARE                       STAGING
  ──────────────────         ──────────────────────        ──────────────
  make prepare-ml            prepare_ml_best.py
  URL=https://...       ─►   ┌───────────────────────┐
                             │ 1. Resolve link        │
  make prepare-shopee        │    (afiliado → MLB ID) │
  URL=https://...       ─►   │ 2. ML API Oficial:     │─── staging/
                             │    título, preço,      │    {tag}/{sub}/
  make prepare-amazon        │    imagens HQ          │    produto_ts.json
  URL=https://...       ─►   │ 3. Playwright DOM:     │         │
                             │    preço promo (regex) │         │
                             │    sem screenshot/OCR  │         ▼
                             │ 4. Download imagens    │    make stage
                             │    (/app/uploads/)     │         │
                             └───────────────────────┘         │
                                                                ▼
  BANCO (PostgreSQL)           MinIO (S3)               API Flask
  ─────────────────            ──────────────           ────────────
  products table  ◄──────────  imagens         ◄──────  stage_products.py
  • title                      /uploads/bucket          • upsert produto
  • price                                               • upload imagens
  • old_price                                           • marca .processed
  • link (afiliado)
  • external_id (MLB…)
  • disponivel
  • desconto
  • tags / subcategory
  • images (JSON)

   RESULTADO: produto visível no site (React frontend)
"""

# ─────────────────────────────────────────────────────────────────────────────
# DIAGRAMA 3 — ATUALIZAÇÃO DE PREÇOS (sem staging)
# ─────────────────────────────────────────────────────────────────────────────

PRICE_UPDATE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║              ATUALIZAÇÃO DE PREÇOS  (direto no banco, sem staging)           ║
╚══════════════════════════════════════════════════════════════════════════════╝

  make update-prices-ml-right          make update-ml-prices
  (recomendado — mais completo)        (legado — só catálogo API)
         │                                       │
         ▼                                       ▼
  update_ml_prices_right.py           update_ml_prices.py
  ┌───────────────────────────┐       ┌─────────────────────────┐
  │                           │       │                         │
  │  ETAPA A — ML API         │       │  GET /items/{id}        │
  │  /items/{id}              │       │  catalog_product_id     │
  │  /products/{cat}/items    │       │  GET catalog listings   │
  │  → título, estoque,       │       │  find_cheapest()        │
  │    preço de, cheapest     │       │  → price, link          │
  │    seller, frete          │       │                         │
  │                           │       │  ⚠️  NÃO captura:       │
  │  ETAPA B — Playwright DOM │       │  promoção Pix, cupons,  │
  │  (headless, sem screenshot│       │  preço riscado exibido  │
  │  sem info-scrap)          │       └──────────┬──────────────┘
  │  Camada 1: meta tags      │                  │
  │  Camada 2: CSS selectors  │                  ▼
  │  Camada 3: inner_text     │         session.commit()
  │  + regex split-line       │         → imediato no site ✅
  │  + Pix price detection    │
  │  + masking de parcelas    │
  │                           │
  │  ETAPA C — _decide_prices │
  │  • dom_price >> api =     │
  │    preço original riscado │
  │  • pix_price < api =      │
  │    usa Pix como price     │
  │  • old_price: DOM→API→DB  │
  │  • desconto calculado     │
  │                           │
  └───────────┬───────────────┘
              │
              ▼
       session.commit()
       → imediato no site ✅

  CAMPOS ATUALIZADOS:
    price, old_price, link (afiliado), title, disponivel, desconto, updated_at

  OPÇÕES:
    --dry-run     simula sem salvar
    --id MLB…     produto específico
    --no-browser  só API (sem Playwright)
"""

# ─────────────────────────────────────────────────────────────────────────────
# DIAGRAMA 4 — INFRAESTRUTURA E CONTAINERS
# ─────────────────────────────────────────────────────────────────────────────

INFRASTRUCTURE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                     INFRAESTRUTURA — CONTAINERS DOCKER                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  MODO 1 — Backend-only  (make serve-cloudflare)                         │
  │                                                                         │
  │  Cloudflare Tunnel ──► Flask :5555 ──► PostgreSQL :5432                 │
  │                                    ──► MinIO      :9000/:9001           │
  │                                    ──► Redis      :6379                 │
  │                                    ──► Qdrant     :6333                 │
  │                                    ──► ingestion  :5003                 │
  │                                    ──► retrieval  :5004                 │
  │                                    ──► info-scrap :8000 (OCR)           │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  MODO 2 — Frontend completo  (make serve-frontend-public)               │
  │                                                                         │
  │  Cloudflare Tunnel ──► Nginx :443/:80                                   │
  │                         │                                               │
  │                         ├──► /api/* ──► Flask :5555 (proxy_pass)       │
  │                         ├──► /media/* ─► MinIO :9000 (proxy_pass)      │
  │                         └──► /* ──────► React SPA (dist/ estático)     │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  MODO 3 — Local  (make frontup)                                         │
  │                                                                         │
  │  https://localhost ──► Nginx :443 ──► Flask :5555                       │
  │                                   ──► React SPA                         │
  └─────────────────────────────────────────────────────────────────────────┘

  CONTAINERS:
  ┌─────────────────┬──────────────────┬──────────────────────────────────┐
  │ Container       │ Porta            │ Função                           │
  ├─────────────────┼──────────────────┼──────────────────────────────────┤
  │ site            │ 5555→5000        │ Flask API (backend principal)    │
  │ postgres-dev    │ 5432             │ Banco de dados principal         │
  │ minio-dev       │ 9000, 9001       │ Object storage (imagens)        │
  │ redis           │ 6379             │ Cache + memória agentes          │
  │ vector_db       │ 6333             │ Qdrant — embeddings semânticos   │
  │ ingestion_svc   │ 5003             │ Ingestão vetorial (RAG)          │
  │ retrieval_svc   │ 5004             │ Recuperação semântica (RAG)      │
  │ info-scrap      │ 8000             │ OCR de imagens (Shopee/Amazon)   │
  │ nginx-react     │ 80, 443          │ Proxy reverso + React SPA        │
  └─────────────────┴──────────────────┴──────────────────────────────────┘

  VOLUMES:
    pgdata       → dados PostgreSQL (persistente)
    minio_data   → imagens MinIO (persistente)
    /app/staging → JSONs de produto pré-publicação (bind mount)
    /app/uploads → imagens baixadas dos marketplaces (bind mount)
"""

# ─────────────────────────────────────────────────────────────────────────────
# DIAGRAMA 5 — AGENTES INSTAGRAM (LangGraph)
# ─────────────────────────────────────────────────────────────────────────────

INSTAGRAM_AGENTS = """
╔══════════════════════════════════════════════════════════════════════════════╗
║              AGENTES INSTAGRAM  (LangGraph — services/site/agents/)          ║
╚══════════════════════════════════════════════════════════════════════════════╝

  TRIGGER
  ────────────────────────────────────────────────────────────────────────────
  make instagram-post   ──►  POST /instagram/post   ──►  orchestrator.run()
  make stage-and-post   ──►  stage + post em sequência

  ORQUESTRADOR — instagram_orchestrator.py (LangGraph StateGraph)
  ──────────────────────────────────────────────────────────────────────────

           ┌─────────────────────────────────────────────────┐
           │             InstagramPostOrchestrator            │
           │                 (LangGraph)                      │
           └──────────┬──────────────┬──────────────┬────────┘
                      │              │              │
                      ▼              ▼              ▼
          ┌────────────────┐ ┌─────────────┐ ┌────────────────┐
          │ AGENTE 1       │ │ AGENTE 2    │ │ AGENTE 3       │
          │ DECISOR        │ │ ENRIQUECEDOR│ │ POSTADOR       │
          │                │ │             │ │                │
          │ product_       │ │ product_    │ │ instagram_     │
          │ decision_      │ │ enricher_   │ │ poster_        │
          │ agent.py       │ │ agent.py    │ │ agent.py       │
          └───────┬────────┘ └──────┬──────┘ └───────┬────────┘
                  │                 │                 │
          Analisa /staging  Gera legenda LLM   Gera imagem (CV2)
          Filtra por tags   Hashtags           Posta (instagrapi)
          Verifica .posted  CTA                Regista histórico
          LLM decide        enriquecido →      → Instagram API
                │                 │
                └────────► Redis (cache + memória)

  REDIS / ESTADO:
    agent:product_decision:memory        → histórico decisor (list, 100 items)
    cache:product_enricher:{md5}         → cache enriquecimento 24h
    instagram:post_history               → histórico posts (list, 1000 items)
    insta_staging/.posted                → arquivo texto (evita duplicação)
"""

# ─────────────────────────────────────────────────────────────────────────────
# DIAGRAMA 6 — FLUXO DE TRABALHO DIÁRIO
# ─────────────────────────────────────────────────────────────────────────────

DAILY_WORKFLOW = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        FLUXO DE TRABALHO DIÁRIO                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

  1. SUBIR AMBIENTE
  ─────────────────
  make serve-cloudflare          ← backend + túnel + auto-OAuth ML
  make serve-frontend-public     ← completo (React + Nginx + túnel + OAuth)

  2. ADICIONAR PRODUTO
  ────────────────────
  make prepare-ml URL=https://mercadolivre.com.br/...
  make prepare-shopee URL=https://shopee.com.br/...
  make prepare-amazon URL=https://amazon.com.br/...
  make stage                       ← publica no banco (aparece no site)

  3. ATUALIZAR PREÇOS (banco direto — sem staging)
  ─────────────────────────────────────────────────
  make update-prices-ml-right      ← todos os produtos (API + DOM regex)
  make update-prices-ml-right ID=MLB…  ← produto único
  make update-prices-ml-right DRY=1   ← simula

  4. MANUTENÇÃO
  ─────────────
  make organize-tags               ← reclassifica categorias
  make reprepare-ml                ← refaz prepare de todos os MLs
  make restage                     ← republica todos os JSONs do staging
  make staging-dedup               ← remove JSONs duplicados
  make clear-minio                 ← limpa imagens MinIO

  5. INSTAGRAM
  ─────────────
  make instagram-post              ← posta produto no feed + story
  make stage-and-post              ← publica no site E posta

  6. MONITORAMENTO
  ─────────────────
  make check-tokens                ← verifica OAuth ML
  make tunnel-info                 ← URL do túnel ativo
  make logs                        ← logs do Flask em tempo real
"""

# ─────────────────────────────────────────────────────────────────────────────
# DIAGRAMA 7 — ESTRUTURA DE ARQUIVOS PRINCIPAIS
# ─────────────────────────────────────────────────────────────────────────────

FILE_STRUCTURE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                       ESTRUTURA DE ARQUIVOS PRINCIPAIS                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

  V_M/
  ├── Makefile                          ← todos os comandos make
  ├── docker-compose.yaml               ← containers base
  ├── docker-compose.dev.yaml           ← override dev (portas expostas)
  ├── docker-compose.react.yaml         ← overlay Nginx + React
  │
  ├── frontend/                         ← React + Vite + Tailwind
  │   └── src/
  │
  ├── nginx/
  │   ├── Dockerfile.nginx
  │   └── nginx-react.conf              ← proxy /api, /media, SPA fallback
  │
  ├── services/site/                    ← Flask backend
  │   ├── main.py
  │   ├── database.py
  │   ├── models/product.py             ← Product SQLAlchemy model
  │   ├── routes/
  │   │   ├── product_routes.py         ← GET /api/products
  │   │   ├── sync_routes.py            ← POST /sync/mercadolivre/...
  │   │   ├── instagram_routes.py       ← POST /instagram/post
  │   │   └── price_validator_routes.py ← POST /validate-prices
  │   ├── agents/                       ← Agentes LangGraph (Instagram)
  │   │   ├── instagram_orchestrator.py
  │   │   ├── product_decision_agent.py
  │   │   ├── product_enricher_agent.py
  │   │   └── instagram_poster_agent.py
  │   └── scripts/
  │       ├── prepare_ml_best.py        ← prepare ML (API + Playwright DOM)
  │       ├── shopee_prepare_best.py    ← prepare Shopee (Playwright + OCR)
  │       ├── amazon_prepare_best.py    ← prepare Amazon (Playwright + OCR)
  │       ├── stage_products.py         ← publica staging → DB + MinIO
  │       ├── update_ml_prices.py       ← atualiza preços (API catálogo)
  │       ├── update_ml_prices_right.py ← atualiza preços (API + DOM regex) ⭐
  │       ├── reprepare_all_ml.py       ← batch reprepare ML
  │       ├── organize_tags.py          ← reclassificação de categorias
  │       └── price_validator/          ← módulo validação de preços
  │           ├── ml_api.py             ← GET /items, /products/catalog
  │           ├── price_service.py      ← Listing, find_cheapest()
  │           ├── affiliate.py          ← gera links matt_tool
  │           └── url_parser.py         ← extrai MLB ID de qualquer URL
  │
  ├── shared/
  │   ├── agno_container.py             ← container DI (Agno framework)
  │   ├── langchain_container.py        ← LangChain / LangGraph DI
  │   └── conversation_memory.py        ← memória de conversação RAG
  │
  └── vector_db/                        ← Qdrant storage (embeddings)
      └── collections/
"""

if __name__ == "__main__":
    sections = [
        ("VISÃO GERAL", OVERVIEW),
        ("PIPELINE DE PRODUTO", PRODUCT_PIPELINE),
        ("ATUALIZAÇÃO DE PREÇOS", PRICE_UPDATE),
        ("INFRAESTRUTURA", INFRASTRUCTURE),
        ("AGENTES INSTAGRAM", INSTAGRAM_AGENTS),
        ("FLUXO DE TRABALHO DIÁRIO", DAILY_WORKFLOW),
        ("ESTRUTURA DE ARQUIVOS", FILE_STRUCTURE),
    ]
    for title, content in sections:
        print(f"\n{'═' * 78}")
        print(f"  {title}")
        print(f"{'═' * 78}")
        print(content)
