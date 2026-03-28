# Make Commands Reference

## Core Container Management

### Start/Stop
- `make up` — Start development environment (build + detach)
- `make down` — Stop and remove all containers + volumes
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
- `make frontend-dev` — Start dev server (localhost:5173 with proxy to 5000)
- `make frontend-build` — Production build
- `make frontend-build-prod` — Build React for production with Nginx
- `make frontend-clean` — Remove node_modules and dist

---

## Cloudflare Tunnel (🌐 Main public exposure)

### Main Tunnel Commands
- `make serve-cloudflare` ⭐ — **PRIMARY**: Backend + Nginx + Cloudflare tunnel + auto-configure OAuth
- `make serve-frontend-public` ⭐ — Frontend + Nginx + reuses Cloudflare tunnel from serve-cloudflare
- `make stop-cloudflare` — Stop active tunnel ONLY (keeps containers running)
- `make stop-frontend-public` — Stop frontend containers (preserves tunnel for backend)
- `make stop-all` — Stop everything (containers + tunnel)
- `make tunnel-info` — Show current tunnel URL (read-only, doesn't change)

### 🔑 Key Concepts
- **Single Tunnel Architecture**: One `cloudflared` process serves both backend AND frontend via Nginx reverse proxy
- **Tunnel Reuse**: `serve-frontend-public` automatically reuses the tunnel from `serve-cloudflare` if it's already running
- **Shared ML_REDIRECT_URI**: Both commands update the same redirect URI in .env (no conflicts)

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
