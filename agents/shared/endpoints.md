# Flask API Endpoints

## Product Management

### Browse & Details (Jinja2 HTML — serves the live site)
- `GET /` — Homepage: todos os produtos, agrupados por tag (CD, ME, E, PET) com section-dividers
- `GET /secao1` — Casa & Decoração (TAG=CD), com subcategorias e section-dividers por subcategoria
- `GET /secao2` — Moda & Estilo (TAG=ME), com subcategorias
- `GET /secao3` — Eletrônicos (TAG=E), com subcategorias
- `GET /secao4` — PetShop (TAG=PET), com subcategorias
- `GET /produto/<product_id>` — Product detail page (SEO + Schema.org)

### Product API
- `GET /api/products` — Lista produtos com paginação e filtros (JSON)
  - Query params: `tag`, `subtag`, `search`, `page` (default 1), `limit` (default 50, max 100)
  - `search` é accent-insensitive via PostgreSQL `unaccent()` + Python NFD strip
  - Resposta: `{items: Product[], total: int, page: int, pages: int, limit: int}`
  - ⚠️ Retorna OBJETO, não array — use `data.items || data` para compatibilidade
- `GET /api/products/<product_id>` — Get single product (JSON)
- `GET /api/list_ids` — List all product IDs
- `POST /add_product` — Add new product (form submission)
- `DELETE /api/delete/<product_id>` — Delete product

### Media Proxying
- `GET /minio_proxy/<bucket>/<path:filename>` — Direct image proxy
- `GET /media/<bucket>/<path:filename>` — Media file serving
- `GET /media/ping` — Media service health check

### Health Check (Nginx)
- `GET /health` — Nginx health check endpoint (returns `200 OK`, plain text, no Flask involved)

### Admin & SEO
- `GET /admin` — Admin dashboard
- `GET /sitemap.xml` — XML sitemap for search engines
- `GET /robots.txt` — Robots file for search engines

---

## Authentication (prefix: `/auth`)

### Mercado Livre OAuth
- `GET /auth/mercadolivre/login` — Start OAuth flow
- `GET /auth/mercadolivre/callback` — OAuth callback handler
- `GET /auth/mercadolivre/status` — Check ML authentication status
- `POST /auth/mercadolivre/logout` — Logout from ML
- `POST /auth/mercadolivre/refresh` — Refresh ML access token

### Admin & Token
- `POST /auth/admin/login` — Admin authentication
- `POST /auth/token/validate` — Validate JWT token

---

## Product Synchronization (prefix: `/sync`)

### Mercado Livre Sync
- `POST /sync/mercadolivre/product/<external_id>` — Sync single ML product
- `POST /sync/mercadolivre/all` — Sync all ML products
- `GET /sync/mercadolivre/status` — Get ML sync status
- `POST /sync/mercadolivre/cheapest-all` — Find cheapest seller for all products

### Other Marketplaces
- `POST /sync/shopee/product/<external_id>` — Sync Shopee product
- `POST /sync/amazon/product/<external_id>` — Sync Amazon product

---

## Webhooks (prefix: `/webhook`)

- `GET /webhook/health` — Webhook service health check
- `POST /webhook/mercadolivre` — ML product update webhook
- `POST /webhook/shopee` — Shopee product webhook
- `POST /webhook/amazon` — Amazon product webhook
- `POST /webhook/test` — Test webhook endpoint

---

## Instagram Automation (prefix: `/instagram`)

### Post Operations
- `POST /instagram/post` — Create Instagram post
- `POST /instagram/post/auto` — Auto-post with AI filters
- `POST /instagram/schedule` — Schedule post for later
- `POST /instagram/test/image` — Test image generation

### Status & History
- `GET /instagram/workflow` — Get workflow status
- `GET /instagram/history` — Post history
- `GET /instagram/status` — Instagram system status
- `GET /instagram/analytics/<media_id>` — Get post analytics
- `GET /instagram/test/agents` — Test AI agents

---

## Price Validation (prefix: `/price_validator`)

- `POST /price_validator/validate-prices` — Validate product prices
- `GET /price_validator/validate-prices/health` — Health check

---

## AI & RAG (prefix: `/ai`)

- `GET /ai` — AI system status
- `POST /ai/ingest-url` — Ingest URL content into vector DB
- `POST /ai/query` — Query AI system with semantic search

---

## Endpoint Summary

| Category | Count | Key Operations |
|----------|-------|-----------------|
| Products | 11 | List, details, add, delete |
| Auth | 7 | ML OAuth, admin login, token validation |
| Sync | 6 | ML, Shopee, Amazon product sync |
| Webhooks | 5 | ML, Shopee, Amazon event listeners |
| Instagram | 9 | Post, schedule, analytics, history |
| Price Validator | 2 | Validate prices, health |
| AI/RAG | 3 | Ingest, query, status |
| **Total** | **43** | - |

---

## Important Notes

- All routes under blueprints are prefixed (e.g., `/auth/...`, `/sync/...`)
- Product ID format varies by source (ML: `MLB...`, Shopee: `shopee_...`, Amazon: `asin_...`)
- OAuth redirect URI must match tunnel URL (configured by `make serve-cloudflare`)
- Webhooks expect specific JSON payloads per marketplace
- AI endpoints depend on ingestion_service and retrieval_service (dev only)

---

## 🌐 Public HTTPS Access (Cloudflare Tunnel)

### How It Works
When running `make serve-cloudflare`:
- Flask API becomes accessible at: `https://xxxxx.trycloudflare.com/`
- All endpoints are accessible publicly via HTTPS
- URLs are temporary (change on restart)
- Self-signed certs verified automatically by Cloudflare

### Testing Remote Endpoints
```bash
# After running: make serve-cloudflare
URL="https://xxxxx.trycloudflare.com"

# Test API
curl -H "Accept: application/json" ${URL}/api/products

# Test OAuth redirect URI
echo "Check DevCenter ML for: ${URL}/auth/mercadolivre/callback"

# Test webhooks (from external service)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' \
  ${URL}/webhook/mercadolivre
```

### Important: HTTPS is Mandatory
- Mercado Livre OAuth **requires HTTPS** (Cloudflare provides this)
- Webhook callbacks from external services **must be HTTPS** 
- Self-signed certificates work fine (Cloudflare edge terminates SSL)
- **Do NOT use HTTP** for external integrations

## Troubleshooting Remote Access
| Error | Cause | Solution |
|-------|-------|----------|
| 502 Bad Gateway | Nginx has stale Flask IP (old behavior, now fixed) | Fixed via Docker DNS resolver — waits up to 10s for new IP |
| 502 persistente | Flask container down | `docker ps` + `make restart-site` |
| OAuth redirect fails | ML_REDIRECT_URI not updated | Run: `make check-tokens` |
| Webhook not received | Timeout or invalid endpoint | Check logs: `docker logs site` |
| Certificate error (some clients) | HTTPS mismatch | Not an issue with Cloudflare tunnel (proxy handles it) |
| nginx-react unhealthy | `/health` endpoint failing | Fixed: uses `https://127.0.0.1/health` + `--no-check-certificate` |
