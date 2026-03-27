# Service Ports

## Flask Backend

- **Internal**: 5000 (Docker network)
- **External**: 5555 (Host machine, cloudflared tunnels here)
- **Connection**: HTTPS with self-signed certificates

## Frontend

- **Dev server**: 5173 (Vite, localhost:5173)
- **Reverse proxy**: 443 (Nginx in production)

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
| Flask (exposed) | 5555 | Cloudflare tunnel endpoint | HTTP |
| Vite Dev Server | 5173 | Frontend development | HTTP |
| PostgreSQL | 5432 | Relational database | TCP |
| Redis | 6379 | Cache & queue | TCP |
| Qdrant | 6333 | Vector database | HTTP |
| MinIO API | 9000 | Object storage | HTTP/S3 |
| MinIO Console | 9001 | Web UI | HTTP |
| info-scrap | 8001 | Scraping service | HTTP |
| ingestion_service | 5003 | Document ingestion | HTTP |
| retrieval_service | 5004 | RAG retrieval | HTTP |
