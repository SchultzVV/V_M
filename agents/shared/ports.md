# Service Ports

## Entrada Pública

> **Porta pública**: **443** (Nginx HTTPS) — é por aqui que todo o tráfego entra.
> O cloudflared aponta para Nginx 443, não para Flask 5555.

## Flask Backend

- **Interno**: 5000 (Docker network — acessado pelo Nginx via `https://site:5000`)
- **Externo (debug)**: 5555 (mapeado no host, fallback apenas)
- **SSL**: Certificados self-signed (`/app/cert.pem`, `/app/key.pem`)

## Nginx Reverse Proxy

- **443** (HTTPS) — entry point principal: React SPA + proxy da API
- **80** (HTTP) — redireciona para 443
- Config: `nginx/nginx-react.conf`
- Healthcheck: `GET /health` → 200 OK (não envolve Flask)

## Frontend

### Development
- **Vite Dev Server**: 5173 (`make frontend-dev`)
  - Proxy de `/api/*`, `/auth/*`, `/webhook/*` → `https://localhost:443` (Nginx)
  - Hot reload habilitado

### Production / Túinel
- Servido via Nginx 443 (arquivos estáticos em `/app/dist/`)
- Tunnel endpoint: `https://xxxx.trycloudflare.com` (temporário) ou `https://CF_HOSTNAME` (fixo)

## Databases & Cache

- **PostgreSQL**: 5432 (`produtos_db`, user/password)
- **Redis**: 6379 (cache de API + pub/sub)
- **Qdrant (Vector DB)**: 6333 (RAG — 4 coleções, init: `make init-qdrant`)

## File Storage

- **MinIO API**: 9000 (S3-compatible — NUNCA expor ao browser diretamente)
- **MinIO Console**: 9001 (UI admin, minio/minio123)

## External Services

- **info-scrap**: 8001 (OCR + scraping de produtos)
- **ingestion_service**: 5003 (ingestão de docs no vector DB)
- **retrieval_service**: 5004 (RAG retrieval)

## Port Summary

| Service | Port | Propósito | Protocolo |
|---------|------|-----------|-----------|
| **Nginx (entry point)** | **443** | **React SPA + proxy API** | **HTTPS** |
| Nginx redirect | 80 | HTTP → HTTPS | HTTP |
| Flask (interno) | 5000 | API (via Nginx) | HTTPS |
| Flask (debug) | 5555 | Acesso direto debug | HTTPS |
| Vite Dev | 5173 | Frontend dev | HTTP |
| PostgreSQL | 5432 | Banco relacional | TCP |
| Redis | 6379 | Cache + queue | TCP |
| Qdrant | 6333 | Vector DB | HTTP |
| MinIO API | 9000 | Object storage | HTTP/S3 |
| MinIO Console | 9001 | Admin UI | HTTP |
| info-scrap | 8001 | OCR + scraping | HTTP |
| ingestion_service | 5003 | AI ingestão | HTTP |
| retrieval_service | 5004 | AI retrieval | HTTP |

## Frontend

### Development
- **Vite Dev Server**: 5173 (localhost:5173, localhost only)
  - Used by: `make frontend-dev`
  - **Proxy target**: https://localhost:443 (Nginx reverse proxy with Flask backend)
  - Hot reload enabled with HTTPS proxying

### Public Exposure (Cloudflare Tunnel)
- **Current Solution**: Nginx Reverse Proxy via port **443**
  - Tunnel endpoint: `https://xxxxx.trycloudflare.com` (temporary URLs)
  - Used by: `make serve-cloudflare` (backend) + `make serve-frontend-public` (frontend)
  - Architecture: Nginx 443 (React + API reverse proxy) → Flask 5000 via HTTPS
  - SSL: HTTPS with self-signed certificates (Flask: `/app/cert.pem`, `/app/key.pem`)
  - **Recommended for**: Dev, testing, quick demos, and public exposure
  - **Status**: ACTIVE — Nginx now standard solution for both development and Cloudflare tunnel
  - **Benefits**: Consolidated SSL, unified entry point, serves React SPA + proxies API

### Legacy Solution
- **Flask direct exposure**: port **5555** (historical, now superseded by Nginx 443)
  - Reason for change: Nginx provides better SPA handling and consolidated proxy point

## Databases & Caching

- **PostgreSQL**: 5432 (produto_db, postgresql://user:password@localhost:5432/produtos_db)
- **Redis**: 6379 (Cache and task queue)
- **Qdrant (Vector DB)**: 6333 (Vector database for RAG)

## File Storage

- **MinIO API**: 9000 (S3-compatible object storage)
- **MinIO Console**: 9001 (Web UI, minio:minio123)

## External Services

- **info-scrap**: 8001 (Product scraping, OCR, image extraction)
- **ingestion_service**: 5003 (AI document ingestion pipeline)
- **retrieval_service**: 5004 (AI RAG retrieval queries)

## Port Summary Table

| Service | Port | Purpose | Protocol |
|---------|------|---------|----------|
| Flask (internal) | 5000 | Main API | HTTPS |
| Flask (exposed) | 5555 | Direct access (debug/fallback) | HTTPS |
| Nginx React | 80 | HTTP → HTTPS redirect | HTTP |
| Nginx React | 443 | Main entry point (React SPA + API proxy) | HTTPS |
| Vite Dev Server | 5173 | Frontend development | HTTP |
| PostgreSQL | 5432 | Relational database | TCP |
| Redis | 6379 | Cache & queue | TCP |
| Qdrant | 6333 | Vector database | HTTP |
| MinIO API | 9000 | Object storage | HTTP/S3 |
| MinIO Console | 9001 | Web UI | HTTP |
| info-scrap | 8001 | Scraping service | HTTP |
| ingestion_service | 5003 | Document ingestion | HTTP |
| retrieval_service | 5004 | RAG retrieval | HTTP |

## Traffic Flow (Public → Internal)

```
Browser/Cloudflare → https://localhost:443 (Nginx)
  ├── /health          → 200 OK (local, no proxy)
  ├── /api/*           → https://site:5000  (Flask, re-resolved via Docker DNS)
  ├── /auth/*          → https://site:5000
  ├── /sync/*          → https://site:5000
  ├── /webhook/*       → https://site:5000
  └── /*               → /app/dist/ (React SPA static files)
```

### ⚠️ Nginx DNS Note
Nginx resolves `site` on startup **and** on every request after TTL (10s) using Docker's embedded DNS `127.0.0.11`. This prevents 502 errors after Flask container restarts.
