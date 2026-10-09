# DEF (ex-V&M Lojinha) — guia do projeto para sessões do Claude

Catálogo de afiliados (Mercado Livre, Shopee, Amazon) com marca **DEF**
("catálogo de sobrevivência pós-sistema", estética pós-punk, verde neon
`#00ff41`, IBM Plex Mono). Flask + PostgreSQL + MinIO + Redis, React/Vite
atrás de Nginx 443, túnel Cloudflare, OCR externo (`info-scrap`), LLMs
(OpenAI `gpt-4o-mini`, Ollama via `hsmart`) e um pacote de agentes
LangGraph para postar no Instagram.

Este arquivo é a fonte de verdade. O diagnóstico detalhado, o plano por
fases e o checklist estão em `docs/estado-atual.html` (abra no navegador).
O plano de infraestrutura em nuvem (Terraform para GCP, AWS e Azure, com
custos e Δ código) está em `docs/infra-cloud.html` e no código em `infra/`
(ver `infra/README.md`; escrito em 2026-10-09, ainda não aplicado).
Revisão completa do código: **2026-10-08**, branch `dev-front`, HEAD
`2ffd05f` (2026-05-16, "aba de esportes"), árvore suja com 22 arquivos
modificados + `templates/secao5.html` novo (tudo sobre a tag ES/Esportes).

Repositório: `/home/v/Desktop/V_M`, remoto `github.com/SchultzVV/V_M`
(privado). `dev-front` está 44 commits à frente de `main`. O diretório
`/home/v/Documents/V_M` é um snapshot obsoleto de março: ignore.

---

## 1. O que o produto é

- Vitrine de ofertas de afiliado; o site não vende, redireciona com link de
  afiliado (ML `matt_tool`, Shopee `s.shopee.com.br`, Amazon `amzn.to`).
- Categorias (tag) e subcategorias (subtag): `CD` Casa & Decoração, `ME`
  Moda & Estilo, `E` Eletrônicos, `PET` PetShop, `ES` Esportes (nova, em
  andamento), `geral`. Subtags hardcoded em `frontend/src/data/subtags.ts`
  e nos scripts de prepare.
- Dois frontends convivem: **React SPA** (`frontend/`: `/`, `/produto/:id`,
  `/admin/login`, `/admin/dashboard`) e **Jinja** (`/catalogo` →
  `index.html`, `/secao1..5`, `/produto/<id>`, `/admin`, `/ai`). O Nginx
  manda `/catalogo|secao[1-4]|ai` para o Flask e todo o resto para o React.
- Visão-alvo (PRD, §4): Instagram → recomendação de conteúdo → menor preço
  entre ML/Shopee/Amazon → dados oficiais → post → site → Instagram.

---

## 2. Arquitetura ATUAL (verificada)

### 2.1 Serviços

| Serviço | Imagem | Porta host | Papel | Arquivo |
|---|---|---|---|---|
| `site` | build `services/site/Dockerfile` (py3.10 + Playwright) | 5555→5000, HTTPS com `certs/localhost.*` | Flask, 8 blueprints | compose base + dev |
| `db` | postgres:15 (`user/password/produtos_db`) | 5432 | tabela `products` | base |
| `minio` | `bitnamilegacy/minio:2025.7.23-debian-12-r5` (`minio/minio123`; `minio/minio` foi removido do Docker Hub e do quay.io em 2026, MinIO é source-only) | 9000 / 9001 | imagens, bucket por plataforma | base |
| `redis` | redis:7 | 6379 | cache, histórico dos agentes | base |
| `info-scrap` | `ghcr.io/schultzvv/info_scrap` | 8001→8000 | OCR de screenshot (preço promo) | base |
| `vector_db` | qdrant | 6333 | `price_history` (price oracle) | dev |
| `ollama` | ollama/ollama | 11434 | `qwen2.5:1.5b` (tag classifier) | dev |
| `hsmart` | `ghcr.io/schultzvv/hsmart` | 5005 | RAG/LLM p/ tag classifier e price oracle | dev |
| `nginx` | build `nginx/Dockerfile.nginx` | 80 / 443 | serve `frontend/dist`, proxy `/api /auth /webhook` → site, `/media` → minio | `docker-compose.react.yaml` |

`make up` usa base+dev e o `site` tem `depends_on: hsmart` → sobe Qdrant,
Ollama e hsmart. Os targets `serve-*` contornam com `--no-deps db minio
redis site [nginx]`. Produção (`docker-compose.prd.yaml`) tem imagem
placeholder `<seu_usuario_github>` e nunca rodou. `.render.yaml` está todo
comentado. O `Dockerfile` da raiz copia `services/site/models.py`, que não
existe (build quebra; só o de `services/site/` é usado).

### 2.2 Exposição pública

Cloudflare **quick tunnel** (`scripts/tunnel-manager.sh`, URL
`*.trycloudflare.com` que muda a cada run e cai depois de algumas horas).
`serve-cloudflare` reescreve `ML_REDIRECT_URI` no `.env` a cada run.
`serve-cloudflare-fixed` está inoperante (`CF_HOSTNAME` sem domínio válido).
Não existe domínio próprio; `services/seo_service.py` gera sitemap/OG com
`https://seusite.com`. Isso bloqueia a Graph API do Instagram (precisa de
URL pública estável para as imagens) e o webhook do ML em produção.

### 2.3 Backend Flask (`services/site/main.py`, 8 blueprints)

| Blueprint | Rotas principais | Estado |
|---|---|---|
| `product_bp` | `GET /`, `/catalogo`, `/secao1..5`, `/produto/<id>`, `/admin`; `POST /add_product` (upsert por `platform+external_id`); `GET /api/homepage`, `/api/products?tag&subtag&search&page&limit` (paginado), `/api/products/<id>`, `/api/list_ids`; `DELETE /api/delete/<id>`; `/sitemap.xml`, `/robots.txt` | funciona; **sem autenticação** |
| `media_bp` | `GET /media/<bucket>/<path>`, `/media/ping` | funciona; `?token=` nunca é verificado |
| `ai_bp` | `GET /ai/`, `POST /ai/ask` (busca por keyword no banco + OpenAI `gpt-4o-mini`) | funciona; `tests/unit/test_ai_routes.py` testa rotas antigas (`/ingest-url`, `/query`) que não existem mais |
| `auth_bp` | `/auth/mercadolivre/login|callback|status|logout|refresh`; `POST /auth/admin/login` (default `admin/admin`), `/auth/token/validate` | OAuth ML funciona; único endpoint protegido por JWT é `/auth/token/validate` |
| `webhook_bp` | `POST /webhook/mercadolivre` (`topic=items`), `/webhook/shopee`, `/webhook/amazon` (stubs), `/webhook/test`, `GET /webhook/health` | **quebra**: `services/marketplace_service.py` usa a instância `db` de `database.py`, que nunca recebe `init_app` |
| `sync_bp` | `POST /sync/mercadolivre/product/<id>`, `/sync/mercadolivre/all` (mesmo bug), `/sync/mercadolivre/cheapest-all` (funciona), `/sync/shopee/*` e `/sync/amazon/*` (501) | parcial |
| `price_validator_bp` | `POST /validate-prices`, `GET /validate-prices/health` (sem prefixo; docs dizem `/price_validator/`) | funciona |
| `instagram_bp` | 9 rotas `/instagram/*` (§2.7) | registrado; fluxo quebrado |

Flask roda com `debug=True`; CORS liberado para `*.trycloudflare.com`;
`JWT_SECRET` e admin com defaults.

### 2.4 Modelo de dados (`services/site/models/product.py`, tabela única `products`)

`id` uuid str · `platform` · `external_id` (unique com platform) · `title`
· **`price` String** ("R$ 1.234,56") · `old_price` String · `image` Text
JSON · `link` · `tags` Text JSON (`["geral","E"]`) · `subcategory` String
· `created_at` / `updated_at` · aliases de webhook `nome`, `preco`,
`preco_original`, `desconto` Float, `descricao`, `imagens`, `disponivel`
Boolean. Preço válido = regex SQL `price ~ '[1-9]'`. Migrações manuais
(`scripts/migrate_add_tags.py`, `migrate_add_webhook_fields.py`,
`migrate_add_subcategory.py`), sem Alembic. **Duas instâncias
`SQLAlchemy()`** (`database.py` e `models/product.py`); só a segunda é
inicializada.

### 2.5 Esteira de produtos (o que existe de verdade)

```
URL (ML | Shopee | Amazon)
  │ make prepare-ml URL= | prepare-shopee URL= | prepare-amazon URL=
  │   ML:     API oficial (/items, /products, sale_price) + screenshot Playwright
  │           + OCR no info-scrap (preço promo) + link afiliado matt_tool
  │   Shopee: api/v4 não oficial + Playwright stealth + screenshot no HOST + OCR (frágil)
  │   Amazon: Playwright + OCR (sem PA-API, sem tag de afiliado)
  │   → pergunta categoria/subcategoria (ou FORCE_CATEGORY=geral|auto)
  ▼
services/site/uploads/<slug>/*.jpg  +  staging/<pasta-tag>/<subtag>/<slug>_<ts>.json
  │ make organize-tags | organize-tags-auto   (move JSON entre pastas por keywords)
  │ make verify-product-cheaper URL=          (menor vendedor no catálogo ML → cheaper_products.json)
  ▼
  │ make stage  → scripts/stage_products.py: MinIO bucket=<platform>, POST /add_product,
  │               staging/.processed; PULA JSON cujo price não tem dígito 1-9
  ▼
PostgreSQL products → /api/products → React (Nginx) | Jinja (/catalogo, /secaoN)
  │ manutenção: update-ml-prices, api-update URL=, reprepare-ml, verify-prices,
  │             fix-bad-links, reprice-all (APAGA produto com preço 0), price-oracle
```

Automático (sem cron, disparo manual):
- `make publish` / `prepare-and-publish` → `scripts/pipeline_publish.py`:
  lê `list_to_prepare_and_stage/links_to_publish.json` → prepare com
  `FORCE_CATEGORY=auto` → `organize_tags --auto` → `stage` →
  `update_ml_prices_right` → `tag_classifier --db` → arquiva em
  `staged/staged_links.json`.
- `make populate-mf [TAG= SUBTAG= LIMIT= DRY=1]` → `agents/ml_populator_agent.py`:
  busca mais vendidos no ML por tag/subtag (403 → scrape HTML), acha o
  vendedor mais barato, grava os links e chama `pipeline_publish`.
- `make check-n-populate` → `scripts/check_and_populate.py` no host.

Estado do staging em 2026-10-08: 74 JSONs, 59 em `.processed`, **62 com
preço inválido (`R$ 0.00`, `disponivel:false`)** gerados pelo
`populate-mf`; filas: 18 links Shopee em `links_to_publish.json`, 21 links
ML em `list_to_verify.json`.

### 2.6 Agentes de runtime (`services/site/agents/`)

| Agente | Faz | Invocado por | Estado |
|---|---|---|---|
| `BaseAgent` (`__init__.py`) | LangChain `ChatOpenAI(gpt-4o-mini)` + memória Redis | herança | instancia o LLM no `__init__` mesmo nos mocks: sem `OPENAI_API_KEY`, tudo em `/instagram/*` dá 500 |
| `ml_populator_agent` | ML search → cheapest → links → `pipeline_publish` | `make populate-mf` | funciona com token ML |
| `price_oracle_agent` | item/catálogo ML + DOM opcional + `price_history` (Qdrant) → LLM do `hsmart` decide preço → grava no banco | `make price-oracle` | funciona se hsmart/ollama estiverem de pé |
| `reprice_all` | passa o oracle em todos; **hard delete** de preço ≤ 0 | `make reprice-all` | funciona; destrutivo |
| `tag_classifier_agent` | keywords → hsmart → Ollama `qwen2.5:1.5b` | `make tag-classify-db`, etapa do pipeline | `--staging` ok; **`--db` é no-op** (filtra `Product.tag`/`subtag` inexistentes); não conhece ES |
| `product_decision_agent` | escolhe produto para postar | orquestrador | **MOCK** (pega o JSON mais recente); glob `staging/*.json` não recursivo → acha 0 produtos; marca `.posted` antes de postar, até em simulação |
| `product_enricher_agent` | legenda + hashtags | orquestrador | **MOCK** (template fixo); legenda sem link de afiliado |
| `instagram_poster_agent` | gera imagem 1080×1080 (Pillow/cv2) e publica | orquestrador | usa **`instagrapi`** (não oficial, usuário/senha); login real falha (`docs/instagram/INSTAGRAM_STATUS.md`) |
| `instagram_orchestrator` | LangGraph decide → enrich → post | `POST /instagram/post[/auto]`, `make instagram-post` | roda, mas com os defeitos acima |

`agents/*.agent.md` (backend, frontend, techlead, tunelador) são prompts
para agentes de IA de desenvolvimento, não runtime.

### 2.7 Instagram (o que existe)

Rotas: `POST /instagram/post`, `/post/auto?simulate=`, `/schedule` (grava
Redis, nenhum worker consome), `/test/image`; `GET /workflow`, `/history`,
`/analytics/<media_id>`, `/status`, `/test/agents`. Make:
`instagram-post|test|status|history`, `prepare-post-image`,
`stage-and-post`. Env exigido pelo código: `INSTAGRAM_USERNAME`,
`INSTAGRAM_PASSWORD`, `REDIS_URL`, `OPENAI_API_KEY` (nenhum `INSTAGRAM_*`
está no `.env` hoje). **Nenhuma linha de Graph API** no código; os docs
`INSTAGRAM_API_OFICIAL.md` e `SETUP_INSTAGRAM_BUSINESS.md` descrevem o
plano, não o código. Nada lê perfil, segue, ou publica stories/reels.

### 2.8 Recomendação de conteúdo (branch `origin/dev-recommendations`, 1 commit, 2026-01-31)

`services/recommendations-system/`: microserviços FastAPI (gateway 8000,
auth 8001, ingest 8002, tracking 8003, recommendations 8005,
profile_builder) com Postgres, Redis e **Kafka próprios**. Entrada: OAuth
Instagram Graph (`instagram_basic`, `instagram_content_publish`); `ingest`
lê bio + últimas 10 legendas **do próprio usuário autenticado**; embeddings
OpenAI `text-embedding-3-small` em coluna JSON do Postgres; cosseno em
numpy; score = 0,6·similaridade + 0,3·desconto + 0,1·cliques; fallback
"trending". É **scaffold**: nenhum serviço preenche o embedding, catálogo
é seed fictício, sem ponte com `products`, `tracking/stats` é TODO, e
duplica `shared/*.py` da raiz. Não toca `services/site` nem `frontend`.

### 2.9 Variáveis de ambiente (`.env`, não versionado; só nomes)

Em uso: `DATABASE_URL`/`POSTGRES_*`, `MINIO_*`, `MEDIA_TOKEN`, `REDIS_HOST/PORT`,
`ML_APP_ID`, `ML_CLIENT_SECRET`, `ML_REDIRECT_URI`, `MERCADO_LIVRE_AFFILIATE_ID`,
`ML_SELLER_ID`, `ML_UTM_*`, `ML_PRICE_OCR_VERIFY_IDS`, `OPENAI_API_KEY`,
`OPENAI_EMBEDDING_MODEL`, `HSMART_URL`, `HSMART_*_URL`, `QDRANT_URL`,
`CF_HOSTNAME`, `NGROK_*`, `CORS_ORIGINS`, `GITHUB_USERNAME/TOKEN`, `FLASK_ENV`,
`PORT`, `LOG_LEVEL`, `DEBUG`. Esperadas pelo código e ausentes:
`INSTAGRAM_USERNAME/PASSWORD` (instagrapi), `JWT_SECRET`, `ADMIN_USERNAME/PASSWORD`.
Planejadas (Graph API): `META_APP_ID/SECRET`, `IG_USER_ID`, `IG_ACCESS_TOKEN`,
`PUBLIC_BASE_URL`.

Tokens OAuth do ML ficam em `services/site/config/ml_tokens.json` — **o
arquivo está rastreado no git e com diff pendente**. Ver §7.

---

## 3. Comandos mecânicos — runbook do operador (funciona HOJE)

Pré-requisitos: Docker, `make`, `jq`, `cloudflared`, `.env` preenchido,
acesso ao GHCR para `info-scrap` (e `hsmart` se usar `make up`).

```bash
# 0. Subir backend + túnel (sem a stack LLM) e checar o token do ML
make serve-cloudflare            # sobe db minio redis site, abre túnel, imprime link de autorização ML
make check-tokens                # access/refresh presentes? se não, abra o link impresso acima
make serve-frontend-public       # opcional: build React + Nginx 443 no mesmo túnel
make links                       # URLs ativas (site, API, callback ML, MinIO console)

# 1. Preparar um produto (interativo: pede categoria 1-6 e subcategoria)
make prepare-ml     URL="https://meli.la/xxxx"            # ML: API + OCR; gera staging/<tag>/<sub>/<slug>_<ts>.json
make prepare-shopee URL="https://s.shopee.com.br/xxxx"    # precisa de DISPLAY no host p/ screenshot; frágil
make prepare-amazon URL="https://amzn.to/xxxx"            # scraping + OCR
#    Lote ML sem perguntas (categoria = geral): edite list_to_prepare_and_stage/list_to_verify.json e rode
make prepare-ml

# 2. Conferir/corrigir
cat services/site/staging/<pasta>/<arquivo>.json           # price precisa ter dígito 1-9, senão o stage pula
make verify-product-cheaper URL="https://meli.la/xxxx"     # opcional: menor vendedor no ML
make organize-tags                                         # reclassifica por título; pergunta nos casos duvidosos

# 3. Publicar no site
make stage                       # MinIO + POST /add_product + .processed; roda staging_dedup
#    republicar tudo: make restage   |   ver: https://localhost (Nginx) ou https://localhost:5555 (Flask)

# 4. Remover/ajustar
#    /admin (Jinja, sem senha) → Excluir   |   DELETE /api/delete/<id>
make update-ml-prices DRY=1      # vendedor mais barato p/ todos os ML (DRY=1 só simula)
make api-update URL=...          # atualiza um produto ML

# 5. Instagram (NÃO use em produção: instagrapi está bloqueado e viola os termos)
make instagram-test              # simula; hoje falha por glob não recursivo e OPENAI_API_KEY obrigatória

# Perigosos
make down-purge                  # apaga banco, MinIO e Redis
make reprice-all                 # apaga produtos com preço 0
make prd-down                    # usa -v: apaga volumes
```

Regras do operador: um comando por produto; `FORCE_CATEGORY=CD|ME|E|PET|ES|geral|auto`
no ambiente torna o prepare não-interativo; nunca editar `staging/.processed`
à mão exceto para forçar republicação; preço com `R$` e dígitos; conferir
`make check-tokens` antes de qualquer `prepare-ml`.

### 3.1 Comandos-alvo (Fase 1 — ainda NÃO existem)

Uma CLI `def` (ou `vm`) não-interativa, mesma função para humano e agente:

```bash
def produto preparar <url> --tag E --subtag tv [--plataforma auto]   # = prepare-* sem perguntas
def produto publicar [--arquivo x.json | --todos]                      # = stage
def produto listar [--tag E] [--invalidos]                             # inclui preços zerados
def produto remover <id> [--apagar-imagens]
def produto checar                                                      # imagens no MinIO, preço, tag, subtag
def preco caçar "<tema>" [--plataformas ml,shopee,amazon]               # Fase 2
def post aprovar|rejeitar <post_id>                                     # Fase 3
def insta publicar <product_id>                                         # Fase 3, Graph API
```

---

## 4. PRD — visão alvo e distância até ela

### 4.1 Objetivo

Transformar um sinal de interesse (perfil/post do Instagram) em produto
publicado no site e divulgado no Instagram, com o menor preço entre ML,
Shopee e Amazon, dados de fontes oficiais, trilha de decisão e aprovação
humana antes de publicar.

### 4.2 Fluxo-alvo × estado real

| # | Etapa | Hoje |
|---|---|---|
| 1 | Operador segue um perfil e registra `@username` | não existe (o scaffold de recomendação lê o perfil do **próprio** usuário) |
| 2 | Observador coleta posts/legendas/hashtags permitidos pela API | não existe |
| 3 | Recomendador extrai intenções de produto com score e tag | scaffold desconectado na branch `dev-recommendations` |
| 4 | Caça ao menor preço entre ML, Shopee e Amazon | só ML × vendedores ML (`price_validator`, `update_ml_prices`) |
| 5 | Ficha oficial do vencedor | ML sim (API + OCR); Shopee e Amazon por scraping |
| 6 | Composição do post (staging JSON + legenda + tag) | prepare gera o JSON; legenda é template mock sem link |
| 7 | Gate humano | não existe (`organize-tags` pergunta tag, só isso) |
| 8 | Publicar no site | **funciona** (`make stage`) |
| 9 | Publicar no Instagram mencionando o site | instagrapi bloqueado; Graph API não implementada; sem URL pública estável |
| 10 | Acompanhar preço/estoque | webhook ML quebrado; `update-ml-prices` manual; sem cron |

### 4.3 Requisitos funcionais

- RF1 Cadastro mecânico por comandos não-interativos (§3.1).
- RF2 Preço numérico (`price_cents`, `old_price_cents`, `currency`); strings só na saída.
- RF3 Fila `posts` com estados `rascunho → aprovado → publicado_site → publicado_instagram → arquivado`.
- RF4 PriceHunter com adaptador por plataforma (ML oficial; Amazon PA-API se elegível; Shopee Affiliate API) e normalização de preço + frete.
- RF5 Instagram só pela Graph API (conta Business + Página + app Meta), imagem em URL HTTPS pública estável.
- RF6 Toda decisão de agente em `agent_runs` (entrada, candidatos, escolha, motivo).
- RF7 Autenticação em toda rota de escrita; admin sem default.
- RF8 Nenhum segredo versionado.

### 4.4 Restrições das APIs (conferir doc atual antes de implementar)

- **Instagram Graph API** não segue perfis, não lista seguidos nem lê o
  feed de recomendações. Leitura de terceiros só por *Business Discovery*
  (alvo Business/Creator) e busca por hashtag. Publicação em dois passos
  (container → publish) com imagem pública HTTPS, limite diário (~25),
  token longo expira em ~60 dias. **`instagrapi` viola os termos** e já
  está bloqueado na conta.
- **Mercado Livre**: busca e item exigem token (já há OAuth com refresh);
  link de afiliado via `matt_tool` (já feito) ou `/teams/{seller}/affiliate_link`.
- **Amazon PA-API** só com conta Associates com vendas qualificadas; senão manual.
- **Shopee**: Affiliate Open API exige credenciais aprovadas; scraping quebra.

### 4.5 Não-objetivos

Checkout próprio, estoque próprio, multiusuário com papéis, app mobile,
automação social (likes/follows/DMs), Kafka ou microserviços antes de o
monólito estar limpo.

---

## 5. Catálogo de agentes alvo e o que já existe de cada um

| Agente alvo | Existe hoje | Reaproveitar | Falta |
|---|---|---|---|
| Operador (humano) | `organize-tags`, `/admin` | — | gate de aprovação de post |
| InstagramObserver | nada | `recommendations-system/ingest` como referência de Graph | business discovery/hashtags por username registrado |
| ContentRecommender | scaffold na branch | fórmula de score, embeddings OpenAI | ligar a `products`, preencher embeddings, rodar no monólito |
| PriceHunter | `price_validator/` (ML), `update_ml_prices*.py` | adaptador ML pronto | adaptadores Shopee/Amazon, normalização, comparação entre plataformas |
| ProductData | `prepare_ml_best.py`, `api_prepare_ml.py` | API + OCR | consolidar em um módulo com flags; Shopee/Amazon oficiais |
| PostComposer | `product_enricher_agent` (mock), `prepare_publish_images.py` | gerador de imagem 1080² | LLM real, link de afiliado e do site na legenda |
| SitePublisher | `stage_products.py` | **pronto** | validação de preço antes de pular silenciosamente |
| InstagramPublisher | `instagram_poster_agent` (instagrapi) | fluxo de imagem | reescrever sobre Graph API |
| PriceWatcher | `/webhook/mercadolivre`, `update-ml-prices`, `price_oracle` | lógica de cheapest | consertar `db` do webhook, cron, soft delete |
| Auditor | histórico Redis dos agentes | — | tabela `agent_runs` e relatório |

---

## 6. Plano de organização (resumo; detalhes e checklist em `docs/estado-atual.html`)

| Fase | Objetivo | Pronto quando |
|---|---|---|
| **F0 Segurança e base** | tirar segredos do git (`config/ml_tokens.json`, `cert.pem.bak`, `key.pem.bak`, `legacy/misc/key.pem`, credenciais em `docs/instagram/SETUP_INSTAGRAM_BUSINESS.md`) e rotacionar; consertar `marketplace_service` (instância `db`), target órfão do Makefile, `tag_classifier --db`, glob do decisor, `secao5` no Nginx; `make up` sem hsmart por padrão (profile `llm`); CI rodando pytest de verdade; apagar `legacy/`, docs duplicados e os MDs de diagnóstico da raiz | `git grep` sem token; `make up` sobe só site/db/minio/redis/info-scrap; `make test-unit` verde local e no CI |
| **F1 Operação manual mecânica** | CLI `def produto *` não-interativa; um único script de prepare por plataforma (aposentar `api_prepare_ml`, `auto_prepare_ml`, `generate_staging_json`, `shopee_prepare`, `update_ml_prices` antigo); `price_cents` via Flask-Migrate; auth nas rotas de escrita e admin por env; React admin com endpoints que existem; limpar os 62 JSONs zerados | operador sobe produto do zero em ≤ 5 min só com comandos documentados; agente usa os mesmos comandos |
| **F2 Menor preço e fontes oficiais** | PriceHunter multi-plataforma sobre `price_validator`; webhook ML consertado e registrado; Amazon PA-API ou manual; Shopee Affiliate API ou manual; `PriceWatcher` com cron; soft delete | dado um tema, retorna o mais barato entre as três com ficha oficial; preço atualiza sozinho |
| **F3 Instagram oficial** | domínio fixo (Cloudflare named tunnel + `CF_HOSTNAME` válido) para imagens públicas; conta Business + Página + app Meta; `InstagramPublisher` sobre Graph API; enricher com LLM real e link; decisor lendo o banco; tabela `posts` + `def post aprovar` | post aprovado sai no site e no Instagram com link e menção; zero `instagrapi` |
| **F4 Recomendação de conteúdo** | observer por username/hashtag + recomendador dentro do monólito (reaproveitar fórmula e embeddings do scaffold; sem Kafka) alimentando o PriceHunter | de um perfil registrado nascem intenções → candidatos → rascunhos |
| **F5 Loop com auditoria** | agendador, limites diários, `agent_runs`, refresh de tokens, métricas de clique | ciclo roda sozinho e todo post tem trilha legível |

---

## 7. Regras para o agente de código (Claude)

- Leia este arquivo e `docs/estado-atual.html` antes de mexer. Trabalhe só
  em `/home/v/Desktop/V_M`.
- **Segredos**: nunca commitar `services/site/config/ml_tokens.json`,
  `config/instagram_session.json`, `*.pem`, `.env*`. Antes do próximo
  commit, tirar `ml_tokens.json` do índice (`git rm --cached`) e adicionar
  ao `.gitignore`; avisar o usuário para rotacionar `ML_CLIENT_SECRET` e os
  tokens no DevCenter.
- Não edite `legacy/`, `*.bak`, `*copy*`, nem os MDs de diagnóstico da raiz
  (`DIAGNOSTICO_*`, `SOLUCAO_*`, `IMPLEMENTACAO_*`, `ORGANIZE_TAGS_*`,
  `RESTAGE_*`, `DEBUG_*`, `OPCAO_B_SUMMARY.sh`): são lixo a arquivar na F0.
- Mudança de esquema só com migração versionada (Flask-Migrate a partir da
  F1) e atualização da §2.4. Não confiar em `create_all`.
- Preço: nenhum campo string novo; novos campos em centavos.
- Comandos novos: não-interativos com flags; interativo só como wrapper;
  todo comando de operador entra na §3 e no `make help`.
- Integrações só por API oficial. **Proibido** `instagrapi` em código novo,
  scraping ligado por padrão, ou qualquer automação de follow/like/DM.
- Antes de concluir: `make test-unit` (consertar `test_ai_routes.py` na F0)
  e, se tocou em rota, teste com `app.test_client()`.
- Commits em português, prefixados pela fase (`F0: tira ml_tokens.json do git`).
  A árvore está suja com o trabalho da tag ES: não misturar com a F0;
  commitar o ES primeiro (sem o `ml_tokens.json`).
- Ao fechar uma fase: atualizar §2, §3 e marcar o checklist do HTML.

---

## 8. Mapa de documentação: no que confiar

| Confiável | Desatualizado ou contraditório |
|---|---|
| `README.md` (fluxo diário e make targets), `Makefile` (`make help`), `agents/MAPA_AGENTES.md` (lista de agentes; mas atribui LLM/Graph que são mock/instagrapi), `agents/shared/endpoints.md` (rotas IG certas; prefixos `/price_validator` e `/ai/ingest-url` errados), `docs/instagram/INSTAGRAM_STATUS.md` (honesto), `CRITICAS.md` (ainda válido), `docs/conceito.md` (marca) | `docs/instagram/RESUMO_INSTAGRAM.md` ("100% funcional"), `INSTAGRAM_AUTO_POST.md`, `docs/scripts/CHECKLIST_IMPLEMENTACAO.md` ("pronto para produção"), `docs/DefineMe-scripts.md` (targets inexistentes), `docs/DefineMe-agents.md`, `docs/integrações/INTEGRACAO_SHOPEE.md` ("totalmente funcional"), `IMPLEMENTACAO_OPCAO_B.md`, `IMPLEMENTACAO_TUNNEL_COMPARTILHADO.md`, `SOLUCAO_502_*`, `docs/marca/conceito.md` e `docs/conceito eng_visual.md` (cópias idênticas de `docs/conceito.md`) |

---

## 9. Glossário

- **Tag / subtag**: categoria e subcategoria; pasta de staging =
  `casa-decoracao`, `moda-estilo`, `eletronicos`, `petshop`, `esportes`, `geral`.
- **Staging JSON**: `platform, external_id, title, price, oldPrice,
  images_local, images, link, tag, subcategory, disponivel, criado_em,
  via_webhook` (+ `schema_org` nos prepares novos).
- **`.processed`**: lista de JSONs já publicados; `make restage` ignora.
- **info-scrap**: serviço externo de OCR (`:8001`) usado para ler o preço
  promocional em screenshots.
- **hsmart**: serviço externo de RAG/LLM (Ollama) usado pelo tag classifier
  e pelo price oracle; não é necessário para o site.
- **matt_tool**: parâmetro de afiliado do Mercado Livre anexado aos links.
- **DEF**: nome atual da marca; o código ainda diz "V&M" em vários lugares.
