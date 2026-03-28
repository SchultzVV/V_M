# Docker Services

## Core Services (docker-compose.yaml)

### site
- **Type**: Flask application (Python)
- **Port**: 5555 (external) → 5000 (internal)
- **Container**: site
- **Role**: Main backend API, handles all product/sync/auth/webhook endpoints
- **Depends on**: db, minio, redis

### db
- **Type**: PostgreSQL 15
- **Port**: 5432
- **Database**: produtos_db
- **Credentials**: user/password
- **Role**: Relational database for products, orders, metadata

### minio
- **Type**: MinIO (S3-compatible object storage)
- **Ports**: 9000 (API), 9001 (Console)
- **Credentials**: minio/minio123
- **Role**: Image and file storage for products

### redis
- **Type**: Redis 7
- **Port**: 6379
- **Role**: Cache layer and task queue

### info-scrap
- **Type**: External service (ghcr.io/schultzvv/info_scrap)
- **Port**: 8001
- **Role**: Product data scraping, image extraction, OCR

## Development Services (docker-compose.dev.yaml overlay)

Added when using `docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml`:

### nginx-react (New in Nginx-based architecture)
- **Type**: Nginx reverse proxy
- **Port**: 443 (HTTPS)
- **Traffic Flow**: 
  - `/api/*` → Flask https://localhost:5000 (via HTTPS with self-signed certs)
  - `/*` → React SPA from dist/
- **SSL Certs**: Self-signed (Nginx container)
- **Status**: ACTIVE when `make serve-frontend-public` or `make serve-cloudflare` runs
- **Config**: `nginx/nginx-react.conf`
- **Role**: Reverse proxy for React SPA + API consolidation

### vector_db
- **Type**: Qdrant
- **Port**: 6333
- **Role**: Vector database for AI RAG (semantic search)

### ingestion_service
- **Type**: External service (ghcr.io/schultzvv/hsmart-ingestion_service)
- **Port**: 5003
- **Role**: AI document ingestion pipeline for product descriptions

### retrieval_service
- **Type**: External service (ghcr.io/schultzvv/hsmart-retrieval_service)
- **Port**: 5004
- **Role**: AI RAG retrieval for queries and recommendations

## Production Services (docker-compose.prd.yaml)

Minimal setup for production:
- site (Flask)
- db (PostgreSQL)
- minio (object storage)
- No AI services, no Redis, no info-scrap

## Frontend Services (docker-compose.react.yaml)

For React frontend deployment:

### nginx
- **Type**: Nginx reverse proxy
- **Ports**: 80 → 443 (HTTP redirect to HTTPS)
- **Role**: Serves React SPA (static files in /app/dist)
- **Proxy rules**: /api/* → Flask backend
- **Depends on**: site (Flask backend)

## Service Dependencies

```
site (Flask)
├── depends_on: db, minio, redis, info-scrap
└── in dev: also ingestion_service, retrieval_service

nginx (React)
├── depends_on: site
└── serves: frontend/dist with reverse proxy to /api
```

## Network

- All services connected via `backend` bridge network
- Internal communication: service_name:internal_port
- External communication: localhost:host_port
