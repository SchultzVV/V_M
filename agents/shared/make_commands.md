# Make Commands Reference

## Core Container Management

### Start/Stop
- `make up` — Start development environment (build + detach)
- `make down` — Stop and remove all containers (preserves volumes/db)
- `make down-purge` — ⚠️ DESTRÓI VOLUMES — apaga banco, minio e redis permanentemente
- `make logs` — Tail Flask logs in real-time
- `make shell` — Bash shell into site container
- `make psql` — PostgreSQL CLI in postgres container

### Rebuild
- `make restart-site` — Restart only site container
- `make rebuild-site` — Full rebuild of site image
- `make rebuild-info-scrap` — Rebuild info-scrap service

---

## Frontend Development

### Setup & Build
- `make frontend-install` — Install npm dependencies
- `make frontend-dev` — Start dev server (localhost:5173 with HTTPS proxy to 443/Nginx)
- `make frontend-build` — Production build (React SPA → `frontend/dist/`)
- `make frontend-build-prod` — Build React for production with Nginx
- `make frontend-clean` — Remove node_modules and dist

### Local Full-Stack Test
- `make frontup` ⭐ — Sobe site COMPLETO para testes locais: build React + Nginx + Backend

---

## Cloudflare Tunnel (🌐 Main public exposure)

### Main Tunnel Commands
- `make serve-cloudflare` ⭐ — Backend + Nginx 443 + Cloudflare tunnel + auto-OAuth ML
- `make serve-cloudflare-fixed` ⭐ — Túnel com URL FIXA (requer `CF_HOSTNAME` no .env)
- `make serve-frontend-public` ⭐ — React + Nginx 443 + reutiliza tunnel já ativo
- `make stop-cloudflare` — Para túnel (preserva containers)
- `make stop-frontend-public` — Para Nginx/React (preserva tunnel)
- `make stop-all` — Para tudo: containers + tunnel
- `make tunnel-info` — Mostra URL do túnel ativo (sem alterar nada)

### Setup de Túnel Permanente
- `make install-cloudflared` — Instala cloudflared no host
- `make setup-cloudflare-fixed` — Cria túnel nomeado permanente (executar 1x)

### Alternative Tunnel
- `make serve-ngrok` — Tunnel via ngrok (requer NGROK_SUBDOMAIN no .env)
- `make stop-ngrok` — Para ngrok

### 🔑 Conceitos chave
- **Entrada única**: Nginx 443 → React SPA + proxy `/api/*`, `/auth/*`, `/sync/*`, etc. → Flask 5000
- **Túnel compartilhado**: `serve-frontend-public` reutiliza o mesmo tunnel de `serve-cloudflare`
- **DNS resolver via Docker**: Nginx re-resolve IP do Flask em até 10s após restart — sem 502 persistente
- **Health check**: `GET /health` retorna 200 (Nginx direto, sem Flask)

---

## Data Pipeline — Produto por URL

- `make prepare-ml URL=https://...` ⭐ — Prepara produto ML: API + OCR de preço
- `make prepare-ml` — Lote via `list_to_verify.json`
- `make prepare-shopee URL=https://...` — Prepara produto Shopee: Playwright + OCR
- `make prepare-amazon URL=https://...` — Prepara produto Amazon: Playwright + OCR
- `make prepare-all` — Lote de produtos via `list_to_prepare.json`

---

## Data Pipeline — Fluxo Automatizado

### Pipeline Completo (mais usado)
- `make populate-mf` ⭐ — Busca mais vendidos ML → cheapest → prepare → stage
  - `TAG=PET` `SUBTAG=gatos` `LIMIT=5` `DRY=1`
  - Exemplo: `make populate-mf TAG=CD SUBTAG=banheiro LIMIT=3`

- `make publish` ⭐ — Lê `links_to_publish.json` → prepare → LLM tags → stage → archive
  - `DRY=1` `NO_PRICE=1` `NO_TAG=1`

- `make prepare-and-publish` ⭐ — Lê links → prepare → organize → stage → update preços
  - `DRY=1` `FILE=caminho` `NO_PRICE=1` `NO_STAGE=1`

### Price Oracle (LLM-assisted)
- `make price-oracle` — Coleta fontes → LLM decide → publica
  - `FILE=links.json` ou `LINK=https://...` ou `ML_ID=MLB123` `[DRY=1]` `[NO_PUBLISH=1]`

---

## Organização & Publicação

- `make organize-tags` ⭐ — Reorganiza tags por título (interativo, pergunta baixa confiança)
- `make organize-tags-auto` — Auto-tag silencioso (não pergunta)
- `make tag-classify-db` — LLM classifica tag+subtag dos produtos no banco `[DRY=1] [ID=uuid]`
- `make stage` ⭐ — Publica staging no DB + MinIO
- `make restage` — Re-publica TODOS os JSONs do staging (ignora .processed)
- `make check-stage` — Verifica imagens no staging antes de publicar
- `make staging-fix-perms` — Corrige permissões dos arquivos staging

---

## Atualização de Preços & Links

- `make update-ml-prices` ⭐ — Busca vendedor mais barato para todos os produtos ML
  - `DRY=1` simula, `ID=MLB...` filtra por produto
- `make reprice-all` — Revisa todos os produtos: atualiza preços + remove itens zerados
  - `[DRY=1] [ZERO_ONLY=1] [BATCH=N]`
- `make verify-product-cheaper` ⭐ — Verifica se link ML é o menor preço do catálogo
  - `FILE=...` ou `URL=...`
- `make verify-prices` — Verifica preços zerados via OCR + Tesseract
- `make api-update URL=...` — Atualiza preço/disponibilidade de produto ML
- `make shopee-update URL=...` — Atualiza preço/disponibilidade Shopee
- `make fix-bad-links` — Corrige links ML que apontam para item_id errado `[DRY=1]`

### Re-scrape
- `make reprepare-ml` ⭐ — Refaz prepare (API+OCR+imgs) de todos os produtos, mantém tags
- `make reprepare-associate-ml` ⭐ — Reprepare COM link de afiliado (OCR mais preciso)

---

## Instagram Automation

- `make instagram-post` ⭐ — Posta produto no Instagram (feed + story automáticos)
- `make instagram-test` — Simula post sem publicar
- `make prepare-post-image` ⭐ — Gera imagem 1080x1080 `FILE=path.json` ou `--all`
- `make instagram-status` — Status do sistema Instagram (tokens, permissões)
- `make instagram-history` — Histórico de posts (últimos 10)
- `make stage-and-post` — Publica no site E posta no Instagram em sequência

---

## AI / RAG / Vector DB

- `make init-qdrant` — Cria as 4 coleções Qdrant do projeto (idempotente)

---

## Testes & Validação

- `make test` — Todos os testes
- `make test-unit` — Testes unitários
- `make test-integration` — Testes de integração
- `make test-info-scrap` — Testa OCR/scraping
- `make test-affiliate` — Testa gerador de links de afiliado ML
- `make test-price-validator` — Testa módulo price_validator completo
- `make test-api` — Testa chamada à API ML com token atual
- `make check-tokens` — Mostra tokens OAuth salvos no container
- `make links` — Exibe todos os links importantes

---

## Banco de Dados / Migrações

- `make migrate-tags` — Adiciona coluna tags
- `make migrate-webhook` — Adiciona campos de webhook
- `make migrate-subcategory` — Adiciona coluna subcategory

---

## Produção (GHCR)

- `make build-prd-site` — Build imagem de produção
- `make push-ghcr` — Build + push para GitHub Container Registry
- `make prd-up` — Sobe produção local
- `make prd-up-ghcr` — Sobe produção usando imagem GHCR
- `make prd-down` — Para produção
- `make prd-logs` — Logs em produção

---

## Manutenção

- `make staging-dedup` — Remove JSONs duplicados do staging (mantém o mais novo)
- `make clear-minio` — Remove TODAS as imagens do MinIO (com confirmação)
- `make clear-minio-force` — Remove TODAS as imagens do MinIO (sem confirmação)
- `make prune` — Remove containers, volumes e imagens não utilizados
- `make clean-images` — Remove TODAS as imagens Docker

---

## Quick Reference

| Tarefa | Comando |
|--------|---------|
| Subir dev | `make up` |
| Frontend local | `make frontend-dev` |
| Full-stack local | `make frontup` |
| **Expor público** | `make serve-cloudflare` |
| **URL fixa** | `make serve-cloudflare-fixed` |
| **Preparar produto** | `make prepare-ml URL=...` |
| **Pipeline completo** | `make populate-mf TAG=... SUBTAG=...` |
| **Publicar staging** | `make stage` |
| **Organizar tags** | `make organize-tags` |
| **Postar Instagram** | `make instagram-post` |
| **Atualizar preços** | `make update-ml-prices` |

---

## Cloudflare Tunnel (🌐 Main public exposure)

### Main Tunnel Commands
- `make serve-cloudflare` ⭐ — **PRIMARY**: Backend + Nginx 443 + Cloudflare tunnel + auto-configure OAuth
- `make serve-frontend-public` ⭐ — Frontend + Nginx 443 (React build) + reuses Cloudflare tunnel from serve-cloudflare
- `make stop-cloudflare` — Stop active tunnel ONLY (keeps containers running)
- `make stop-frontend-public` — Stop frontend containers (preserves tunnel for backend)
- `make stop-all` — Stop everything (containers + tunnel)
- `make tunnel-info` — Show current tunnel URL (read-only, doesn't change)

### 🔑 Key Concepts
- **Single Tunnel Architecture**: One `cloudflared` process serves both backend AND frontend via Nginx reverse proxy
- **Tunnel Reuse**: `serve-frontend-public` automatically reuses the tunnel from `serve-cloudflare` if it's already running
- **Shared ML_REDIRECT_URI**: Both commands update the same redirect URI in .env (no conflicts)
- **Nginx DNS resolver**: After `make restage` or Flask restart, Nginx picks up the new Flask IP within 10s automatically — no Nginx restart needed
- **Health check**: `GET /health` on Nginx returns 200 OK (used by Docker). No Flask dependency.

### Permanent Tunnel (Custom domain)
- `make setup-cloudflare-fixed` — Create permanent named tunnel (one-time setup)
- `make serve-cloudflare-fixed` — Use permanent tunnel (requires CF_HOSTNAME in .env)

### Alternative Tunnel
- `make serve-ngrok` — Tunnel via ngrok (requires NGROK_SUBDOMAIN in .env)
- `make stop-ngrok` — Stop ngrok tunnel

### Setup
- `make install-cloudflared` — Install cloudflared binary

---

## Frontend + Tunnel (React)

- `make serve-frontend-public` ⭐ — Start React + Nginx + Cloudflare tunnel
- `make stop-frontend-public` — Stop React stack

---

## Product Preparation (Data Pipeline)

### Prepare from URL
- `make prepare-ml` ⭐ — **PRIMARY**: Prepare ML product (API + OCR pricing)
  - Usage: `make prepare-ml URL=https://...`
  - Or uses: list_to_verify.json if no URL

- `make prepare-shopee` — Prepare Shopee product (API + Playwright + OCR)
  - Usage: `make prepare-shopee URL=https://...`

- `make prepare-amazon` — Prepare Amazon product (Playwright + OCR)
  - Usage: `make prepare-amazon URL=https://...`

### Batch Preparation
- `make prepare-all` — Prepare batch of products from list_to_prepare.json

### Re-prepare (Sync & Update)
- `make reprepare-ml` ⭐ — Re-scrape all ML products (keeps tags, does stage)
- `make reprepare-associate-ml` — Re-scrape ML with affiliate link (more accurate OCR)

---

## Product Organization & Publishing

### Tag Organization
- `make organize-tags` ⭐ — **PRIMARY**: Smart tag organization (interactive, prompts for low-confidence)
- `make organize-tags-auto` — Auto-tag silently (non-interactive)

### Publishing
- `make stage` ⭐ — **PRIMARY**: Publish prepared products to DB + MinIO
- `make restage` — Re-publish ALL staging JSONs to DB (useful after code fix)

### Checks
- `make check-stage` — Verify images in staging before publishing
- `make staging-fix-perms` — Fix permissions for staging files

---

## Product Updates

### Price & Availability
- `make update-ml-prices` ⭐ — Find cheapest seller for all products
  - Options: `DRY=1` (simulate), `ID=MLB...` (filter)

- `make api-update` — Update single product (price/availability)
  - Usage: `make api-update URL=https://...`

- `make shopee-update` — Update Shopee product (price/availability)
  - Usage: `make shopee-update URL=https://...`

### Verification
- `make verify-product-cheaper` ⭐ — Check if link is lowest price
  - Usage: `make verify-product-cheaper FILE=...` or `URL=...`

---

## Instagram Automation

### Post Operations
- `make instagram-post` ⭐ — Post product to Instagram (feed + story auto)
- `make instagram-test` — Simulate post without publishing
- `make prepare-post-image` — Generate 1080x1080 post image
  - Usage: `make prepare-post-image FILE=path.json` or `--all` flag

### Status & History
- `make instagram-status` — Check Instagram system status (tokens, permissions)
- `make instagram-history` — Show last 10 posts

### Combined
- `make stage-and-post` — Publish to site AND post to Instagram in sequence

---

## Testing & Validation

### Tests
- `make test` — Run all tests
- `make test-unit` — Unit tests
- `make test-integration` — Integration tests
- `make test-info-scrap` — Test OCR/scraping service
- `make test-affiliate` — Test ML affiliate link generator
- `make test-price-validator` — Test price validator module

### API Testing
- `make test-api` — Test Mercado Livre API with current token

### Utilities
- `make check-tokens` — Show saved OAuth tokens in container
- `make links` — Show all important links (Cloudflare, ML, Instagram, site)

---

## Database Migrations

- `make migrate-tags` — Add tags column
- `make migrate-webhook` — Add webhook fields
- `make migrate-subcategory` — Add subcategory column

---

## Production Deployment

### Build & Push
- `make build-prd-site` — Build production image
- `make push-ghcr` — Push to GitHub Container Registry

### Run Production
- `make prd-up` — Start production environment
- `make prd-down` — Stop production environment
- `make prd-logs` — Tail production logs
- `make prd-up-ghcr` — Start production using GHCR image

---

## Maintenance & Cleanup

### MinIO (Image storage)
- `make clear-minio` — Remove ALL MinIO images (with confirmation)
- `make clear-minio-force` — Remove ALL MinIO images (no confirmation)

### Docker
- `make prune` — Remove unused containers, volumes, images
- `make clean-images` — Remove ALL Docker images (careful!)

### Staging
- `make staging-dedup` — Remove duplicate JSONs (keep newest)

---

## Help

- `make help` — Show full help menu with all targets

---

## Most Important Commands (Quick Reference)

| Task | Command |
|------|---------|
| Start dev | `make up` |
| Frontend dev | `make frontend-dev` |
| **Public API** | `make serve-cloudflare` |
| **Read product** | `make prepare-ml URL=...` |
| **Organize tags** | `make organize-tags` |
| **Publish products** | `make stage` |
| **Post to Instagram** | `make instagram-post` |
| **Update prices** | `make update-ml-prices` |

---

## Command Patterns

### With Arguments
```bash
make prepare-ml URL=https://mercadolivre.com.br/...
make api-update URL=https://mercadolivre.com.br/...
make verify-product-cheaper FILE=product.json
make update-ml-prices DRY=1 ID=MLB...
```

### Show Status
```bash
make logs              # See what's running
make check-tokens      # Verify OAuth tokens
make tunnel-info       # Show tunnel URL
make links             # All important links
```

### Batch Operations
```bash
make reprepare-ml      # Re-scrape all products
make organize-tags     # Organize all tags
make stage             # Publish all staging
```
