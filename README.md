# DEF Site

Plataforma de afiliados e comparação de produtos com scraping automático, publicação de conteúdo e arquitetura de agentes de IA baseados em **LangGraph**. O sistema coleta produtos de múltiplas plataformas (Mercado Livre, Shopee, Amazon), organiza os dados em um pipeline de staging, publica no site e — em breve — delega todo esse fluxo a agentes autônomos com raciocínio encadeado via LLM.

---

## 🚀 Quick Start

### Subir o ambiente com ngrok

```bash
make serve-ngrok
```

Isso vai:
- ✅ Subir todos os containers (PostgreSQL, Redis, MinIO, site)
- ✅ Iniciar túnel ngrok
- ✅ Gerar URL pública para webhooks do Mercado Livre

### Adicionar produto automaticamente

```bash
# 1. Preparar produto do Mercado Livre
make prepare-ml URL="https://produto.mercadolivre.com.br/MLB-..."

# 2. Preparar produto da Shopee
make prepare-shopee URL="https://s.shopee.com.br/..."

# 3. Preparar produto da Amazon
make prepare-amazon URL="https://amzn.to/..."

# 4. Publicar no site (+ dedup automático de staging)
make stage
```

**Pronto-3 /home/v/Desktop/V_M/README.md && echo "---TAIL---" && tail -3 /home/v/Desktop/V_M/README.md* O produto está no site com imagens, preço e categoria detectados automaticamente.

Para todos os comandos: `make help`

---

## 📚 Documentação

- [Conceito e Arquitetura](docs/conceito.md)
- [Agentes — Visão Geral](docs/DefineMe-agents.md)
- [Scripts de Automação](docs/DefineMe-scripts.md)
- [OAuth Mercado Livre](docs/integrações/OAUTH_MERCADOLIVRE.md)
- [Webhooks](docs/integrações/WEBHOOKS.md)
- [Instagram API](docs/instagram/INSTAGRAM_API_OFICIAL.md)

---

## Como subir o ambiente

Para desenvolvimento utilize:

```bash
make up
```

Para executar usando a imagem publicada no GitHub Container Registry:

```bash
make prd-up-ghcr
```

### Acessando a página de IA

Com o ambiente no ar abra `http://localhost:5000/ai`.
Nela você encontra:

- **Formulário de Ingestão**: informe uma URL e clique em **Ingerir URL** para que o serviço `ingestion_service` processe o conteúdo.
- **Chat de Perguntas**: envie perguntas que serão encaminhadas ao `retrieval_service` e veja as respostas em uma caixa de histórico.

### Testando via curl

```bash
curl -X POST http://localhost:5000/ingest-url \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://exemplo.com"}'

curl -X POST http://localhost:5000/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "qual o preço do produto X?"}'
```

### Executando testes

```bash
make test-unit
```

---

## Product staging pipeline

O fluxo completo de um produto — desde a URL até aparecer no site — passa por quatro camadas de infraestrutura: **filesystem local (staging)**, **MinIO (object storage)**, **PostgreSQL (banco relacional)** e **Redis (cache/filas)**. O diagrama abaixo mostra cada etapa:

```mermaid
flowchart LR
    A[URL do produto\nML / Shopee / Amazon] --> B[prepare_*.py\nAPI + OCR + Playwright]
    B --> C[staging/categoria/sub/\nproduto_YYYYMMDD_HHMMSS.json]
    C --> D[staging_dedup.sh\nRemove versões antigas]
    D --> E[stage_products.py]
    E --> F[Upload imagens\nMinIO]
    E --> G[POST /add_product\nFlask API]
    G --> H[save_product\nPostgreSQL]
    H --> I[Redis\nCache de listagens\nFilas de tarefas]
    I --> J[/api/products\nFrontend]
```

### O que fica em cada serviço

| Serviço | O que armazena | Detalhes |
|---|---|---|
| **Staging (filesystem)** | JSONs temporários dos produtos | `services/site/staging/{categoria}/{sub}/{slug}_{ts}.json` |
| **MinIO** | Imagens dos produtos (originais + otimizadas) | Bucket `produtos`, paths `/imagens/{slug}/` |
| **PostgreSQL** | Registro completo de cada produto | Tabela `produtos` — veja campos abaixo |
| **Redis** | Cache de listagens da API, pub/sub para webhooks | TTL configurável, canal `produto_events` |

### Campos de um produto no banco

Cada produto publicado carrega os seguintes dados:

```
id, slug, titulo, descricao, preco, preco_antigo, disponivel,
categoria, subcategoria, tags[], plataforma (ML/Shopee/Amazon),
url_original, url_afiliado, imagens[], thumbnail,
avaliacao, num_avaliacoes, vendedor,
schema_org (JSON-LD para SEO),
criado_em, atualizado_em
```

### staging_dedup — deduplicação automática

O script [`scripts/staging_dedup.sh`](scripts/staging_dedup.sh) é chamado automaticamente após o `make stage`. Ele:
- Varre todos os subdiretórios de `staging/`
- Agrupa JSONs pelo **slug** (nome sem o sufixo `_YYYYMMDD_HHMMSS`)
- Remove todas as versões antigas, mantém apenas a mais recente
- Roda também de forma isolada via `make staging-dedup`

---

## Escalabilidade futura

- Substituir `requests` por **gRPC** para comunicação entre serviços.
- Adicionar **WebSocket** para notificações em tempo real.
- Processar ingestão de forma assíncrona com **Redis Queue** ou **Celery**.
- Migrar o frontend para **React** ou **HTMX** com suporte a polling.
- Disponibilizar facilmente via túnel com `make serve-cloudflare`.

---

## 🤖 Arquitetura de Agentes (LangGraph)

O próximo nível da plataforma substitui a execução manual dos scripts Make por **agentes autônomos** que raciocinam sobre qual ferramenta chamar, validam o resultado via **LLM-as-judge** e tomam decisões encadeadas. Toda a orquestração usa **LangGraph** com nós de estado explícito.

### Princípio geral

Cada agente é um **grafo de estados LangGraph**. Os nós representam ações (chamar um comando Make/shell, consultar o banco, chamar a LLM). As arestas representam decisões (resultado válido? redirecionar? reclassificar?). A LLM atua como juíza avaliando saídas intermediárias — nunca como executor direto.

```
URL / Gatilho
     │
     ▼
[Agente] ──tool_call──► Make / .sh / API
     │
     ▼
[LLM Judge] ──válido?──► próximo nó
                └──inválido──► retry / fallback
```

---

### 🟢 Agente Postador

**Responsabilidade:** receber qualquer URL de produto e publicá-lo no site do começo ao fim, sem saber de antemão em qual plataforma está.

**Fluxo:**
1. Recebe a URL (ML, Shopee ou Amazon — plataforma desconhecida)
2. Dispara **os 3 scripts** `prepare-ml`, `prepare-shopee`, `prepare-amazon` em paralelo
3. Dois retornarão mensagem de erro/plataforma errada; um retorna JSON de produto válido
4. LLM-judge analisa as 3 saídas e determina qual contém o produto real
5. LLM sugere **categoria** e **subcategoria** com base no título/descrição do produto
6. Executa `make stage` → `scripts/staging_dedup.sh`
7. Registra resultado no banco e notifica o Agente Panfleteiro

**Ferramentas (tools):** `prepare_ml`, `prepare_shopee`, `prepare_amazon`, `make_stage`, `staging_dedup`, `classify_product` (LLM)

---

### 🟡 Agente Supervisão

**Responsabilidade:** monitorar preço e disponibilidade dos produtos já publicados, agindo de forma autônoma ou por sinalização.

**Fluxo:**
1. Ativado por **schedule** (cron/APScheduler) ou por **flag** `needs_check = true` no banco
2. Consulta PostgreSQL para produtos elegíveis (desatualizados ou sinalizados)
3. Para cada produto: chama `make api-update` ou `make shopee-update` conforme plataforma
4. LLM-judge compara `{preco_antes, disponivel_antes}` vs. resultado atual — mudança relevante?
5. Se sim: atualiza banco, invalida cache Redis, aciona Agente Panfleteiro (queda > 10%)
6. Se indisponível: marca produto como inativo no banco

**Ferramentas:** `api_update_ml`, `shopee_update`, `amazon_check`, `db_query`, `redis_invalidate`

---

### 🟠 Agente Panfleteiro

**Responsabilidade:** gerar material visual promocional (feed card, story card) para cada produto publicado ou com preço atualizado.

**Fluxo:**
1. Ativado pelo Agente Postador (pós-stage) ou Agente Supervisão (queda de preço significativa)
2. Recupera dados completos do produto no PostgreSQL (imagens MinIO, preço, título, avaliação)
3. Chama scripts de geração de imagem com sobreposição de preço e badge de desconto
4. LLM-judge avalia qualidade do copy e do layout — aprova ou solicita regeneração (máx. 3 tentativas)
5. Salva assets no MinIO e entrega paths ao Agente Instagram

**Ferramentas:** `generate_feed_card`, `generate_story_card`, `fetch_product_db`, `minio_upload`, `llm_copy_judge`

---

### 🔵 Agente Instagram

**Responsabilidade:** gerenciar toda a presença no Instagram — publicação de feed, Reels, Stories e caixa de mensagens (DMs + comentários).

**Fluxo de publicação:**
1. Recebe assets e metadados do Agente Panfleteiro
2. Três sub-agentes decidem em paralelo:
   - **Agente Postador** (sub): define formato (feed/Reels/Story) e escreve o copy/legenda
   - **Agente Midiático** (sub): seleciona trilha sonora para Reels a partir de biblioteca livre
   - **Agente Agenciador** (sub): valida contexto do produto, timing e público-alvo
3. Grafo principal integra as decisões e publica via Meta Graph API
4. Cada novo produto publicado no site dispara automaticamente uma postagem

**Caixa de mensagens:**
- Lê DMs e comentários via Meta Webhooks
- LLM responde dúvidas sobre preço/disponibilidade consultando o banco em tempo real
- Encaminha casos complexos para revisão humana

**Deploy — container isolado:**

O Agente Instagram roda em sua **própria imagem Docker** (`services/instagram-agent/`), expondo endpoints REST consumidos pelo hub de agentes. Esse isolamento garante:
- Escalabilidade independente (tokens Meta têm limites por IP/container)
- Ciclo de vida e secrets próprios sem impactar o site principal
- Facilidade de atualização das integrações Meta

```
services/
  site/                  ← produto principal (Flask)
  instagram-agent/       ← agente Instagram isolado
    Dockerfile
    main.py              ← FastAPI: /publish, /inbox, /status
    graph/               ← grafos LangGraph + sub-agentes
      postador.py
      midiatico.py
      agenciador.py
      main_graph.py
    requirements.txt
```

---

## ✅ Checklist da Missão Agentes

### Fase 0 — Fundação (infra dos agentes)
- [ ] Criar `services/agents/` com `__init__.py`, `base_agent.py`, `tools/`
- [ ] Definir `AgentState` TypedDict: `url, platform, product_data, errors, judge_verdict, next_action`
- [ ] Implementar `tools/make_runner.py` — wrapper que executa Make/shell e captura stdout/stderr
- [ ] Implementar `tools/db_reader.py` — leitura de produtos via SQLAlchemy
- [ ] Implementar `tools/redis_client.py` — invalidação de cache e pub/sub
- [ ] Adicionar dependências: `langgraph`, `langchain`, `langchain-openai`, `apscheduler`
- [ ] Definir variáveis de ambiente: `OPENAI_API_KEY`, `AGENT_MODEL`, `AGENT_JUDGE_MODEL`
- [ ] Criar `docker-compose.agents.yaml` para subir agentes em containers separados

### Fase 1 — Agente Postador
- [ ] Criar `agents/postador/graph.py` com nós: `dispatch_prepare → judge_platform → classify_product → run_stage → run_dedup → finalize`
- [ ] Nó `dispatch_prepare`: dispara `prepare-ml`, `prepare-shopee`, `prepare-amazon` e coleta as 3 saídas
- [ ] Nó `judge_platform`: LLM avalia qual das 3 saídas contém produto real vs. erro de plataforma errada
- [ ] Nó `classify_product`: LLM sugere categoria + subcategoria pelo título/descrição
- [ ] Nó `run_stage`: chama `make stage` via `make_runner`
- [ ] Nó `run_dedup`: chama `scripts/staging_dedup.sh`
- [ ] Nó `finalize`: grava log de ingestão no banco, notifica Agente Panfleteiro
- [ ] Endpoint `POST /agents/postador/run` (FastAPI) recebendo `{"url": "..."}`
- [ ] Testes unitários dos nós com mocks dos comandos Make
- [ ] Teste end-to-end com URL real de cada plataforma

### Fase 2 — Agente Supervisão
- [ ] Criar `agents/supervisao/graph.py` com nós: `list_candidates → check_product → judge_change → update_db → notify`
- [ ] Nó `list_candidates`: consulta PostgreSQL por `needs_check=true` ou `atualizado_em < now() - interval`
- [ ] Nó `check_product`: chama `api-update` ou `shopee-update` conforme `plataforma` do produto
- [ ] Nó `judge_change`: LLM compara preço/disponibilidade antes vs. agora e decide ação
- [ ] Nó `update_db`: atualiza `preco`, `disponivel`, `atualizado_em` no PostgreSQL
- [ ] Nó `notify`: invalida Redis; aciona Panfleteiro se queda de preço > 10%
- [ ] Configurar scheduler (APScheduler) para execução periódica automática
- [ ] Flag `needs_check` no banco + endpoint `POST /products/{id}/flag-check`
- [ ] Testes: simular mudança de preço e verificar pipeline completo

### Fase 3 — Agente Panfleteiro
- [ ] Criar `agents/panfleteiro/graph.py` com nós: `fetch_product → generate_assets → judge_quality → deliver`
- [ ] Nó `fetch_product`: lê produto completo do PostgreSQL (imagens MinIO, preço, título)
- [ ] Nó `generate_assets`: chama scripts de imagem (feed card 1080×1080, story card 1080×1920)
- [ ] Nó `judge_quality`: LLM avalia copy e layout — aprova ou regenera (máx. 3 tentativas)
- [ ] Nó `deliver`: salva assets no MinIO, notifica Agente Instagram com paths e metadados
- [ ] Suporte a badge de desconto baseado na variação percentual de preço
- [ ] Testes: gerar assets para produto de teste e validar output gerado

### Fase 4 — Agente Instagram (container isolado)
- [ ] Criar `services/instagram-agent/` com FastAPI + LangGraph
- [ ] `Dockerfile` próprio (`python:3.12-slim`) sem dependências do site principal
- [ ] Sub-grafo `graph/postador.py` — decide formato e escreve copy/legenda
- [ ] Sub-grafo `graph/midiatico.py` — seleciona trilha sonora para Reels
- [ ] Sub-grafo `graph/agenciador.py` — valida contexto do produto e timing de publicação
- [ ] Grafo principal `graph/main_graph.py` — orquestra os 3 sub-agentes e executa publicação
- [ ] Endpoint `POST /publish` — recebe assets + metadados e publica (feed / Reels / Story)
- [ ] Endpoint `GET /inbox` — lê DMs e comentários recentes via Meta Webhooks
- [ ] Endpoint `POST /inbox/reply` — LLM responde DMs consultando banco de produtos
- [ ] Endpoint `GET /status` — health check + token Meta válido?
- [ ] Adicionar `instagram-agent` ao `docker-compose.yaml` como serviço separado
- [ ] Secrets isolados: `META_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ID`, `META_APP_SECRET`
- [ ] Webhook handler para eventos de DM e comentário em tempo real
- [ ] Testes de integração com Meta Graph API (modo sandbox)

### Fase 5 — Orquestração e Observabilidade
- [ ] Criar `services/agents-hub/` — API central que roteia chamadas para cada agente
- [ ] Dashboard de status: jobs rodando, últimas execuções, erros, decisões LLM
- [ ] Logging estruturado em JSON para todas as decisões LLM (audit trail completo)
- [ ] Tracing com LangSmith ou Langfuse para visualizar grafos de execução
- [ ] Rate limiting e retry policy nos `tool_calls` de cada agente
- [ ] Documentação OpenAPI automática dos endpoints de cada agente
