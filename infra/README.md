# infra/ — Terraform do DEF em três nuvens

Um plano por nuvem, todos serverless onde cabe, com o site (Flask + React),
os jobs da esteira (prepare → stage → preços) disparados por cron e por
evento, banco PostgreSQL gerenciado, object storage no lugar do MinIO,
segredos num cofre e deploy por GitHub Actions sem chave estática (OIDC).

A apresentação completa (diagramas, custos, comparação, Δ de código) está em
**`docs/infra-cloud.html`** (abra no navegador).

| Pasta | Nuvem | Web | Jobs | Trigger de evento | Banco | Imagens |
|---|---|---|---|---|---|---|
| `gcp/` | Google Cloud | Cloud Run (nginx + Flask sidecar) atrás de LB global + CDN | Cloud Run Jobs | Pub/Sub → Eventarc → Workflows → Job | Cloud SQL Postgres 16 | GCS (API S3 via HMAC) |
| `aws/` | AWS | Lambda (container + Web Adapter) + CloudFront, React em S3 | ECS Fargate Spot | SQS → EventBridge Pipes → Step Functions → RunTask | RDS Postgres 16 | S3 |
| `azure/` | Azure | Container Apps (nginx + Flask sidecar), domínio + cert gerenciado | Container Apps Jobs | Storage Queue → KEDA → Job | PostgreSQL Flexible Server | Blob (sem API S3: precisa adaptador) |

Arquivos compartilhados em `docker/`:

- `Dockerfile.site` — camada fina sobre `services/site/Dockerfile` que troca
  `python main.py` por **gunicorn** em HTTP na porta `$PORT`. A mesma imagem
  serve o web e todos os jobs (muda só o comando).
- `Dockerfile.web` — build do React (Vite) + Nginx em `:8080` fazendo proxy
  para o Flask em `127.0.0.1:5000` (sidecar) e `/media/` direto no bucket.
- `nginx.cloud.conf.template` — rotas idênticas a `nginx/nginx-react.conf`
  (+ `secao5`), sem TLS (termina no balanceador/ingress gerenciado).

## Uso rápido (qualquer nuvem)

```bash
cd infra/<gcp|aws|azure>
cp terraform.tfvars.example terraform.tfvars   # preencha domínio, imagens, segredos
(cd bootstrap && terraform init && terraform apply)   # bucket/conta do state remoto
terraform init                                  # backend remoto (ver backend.tf)
terraform plan -out=plan.out && terraform apply plan.out
```

Build e push das imagens (CI faz isso; à mão):

```bash
docker build -t def-site:base --build-arg REQUIREMENTS=requirements-prd.txt services/site
docker build -f infra/docker/Dockerfile.site --build-arg BASE_IMAGE=def-site:base -t <registry>/def-site:<sha> .
docker build -f infra/docker/Dockerfile.web -t <registry>/def-web:<sha> .
```

Os `README.md` de cada pasta trazem passo a passo, migração dos dados locais
(`pg_dump`, imagens do MinIO, `staging/`, `uploads/`, `config/ml_tokens.json`),
custos estimados e a lista de mudanças de código necessárias (Δ código).

## Δ código comuns às três nuvens (resumo)

1. `python main.py` (debug, HTTPS self-signed) → gunicorn via `Dockerfile.site`.
2. Cliente MinIO: `secure=False` hardcoded → `MINIO_SECURE=true` por env; um
   único bucket (`MINIO_BUCKET`) com prefixo por plataforma, em vez de bucket
   por plataforma (nomes de bucket são globais em GCS/S3).
3. `http://info-scrap:8000` hardcoded nos `*_prepare_best.py` → `INFO_SCRAP_URL`.
4. `/webhook/mercadolivre` publica o evento na fila (Pub/Sub, SQS ou Storage
   Queue) em vez de processar inline (e consertar a instância `db`, F0).
5. `REDIS_URL` opcional (o site sobe sem Redis; só agentes/oracle usam).
6. `staging/`, `uploads/`, `config/ml_tokens.json` vivem num volume
   compartilhado (GCS FUSE, EFS ou Azure Files) montado em `/app/...`.
