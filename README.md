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
