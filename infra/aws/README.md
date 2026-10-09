# DEF na AWS — Terraform

Infra serverless para o catálogo DEF (Flask + React + PostgreSQL + imagens +
jobs de preparação/preço), otimizada para custo em tráfego baixo. Tudo que
hoje roda no `docker compose` (CLAUDE.md §2.1) tem um equivalente gerenciado;
os scripts dos targets do Makefile rodam como tasks ECS sem mudar o código.

```
                 Cloudflare DNS (CNAME, DNS only)
                            │
                   ┌────────▼────────┐
                   │   CloudFront    │  TLS (ACM), HSTS, HTTP/3
                   │  PriceClass_All │  borda em São Paulo
                   └──┬─────┬─────┬──┘
        /  (SPA)      │     │     │   /api /auth /webhook /ai /catalogo /secaoN ...
   ┌──────────────────▼┐  ┌─▼───┐ └───────────────────────────────┐
   │ S3 frontend (OAC) │  │ S3  │ /media/*                        │
   │ React dist        │  │media│ (OAC, prefixo removido)   ┌─────▼──────────┐
   └───────────────────┘  └──▲──┘                           │ Lambda (image) │
                             │ MinIO client (S3 API)        │ Flask+gunicorn │
                             │                              │ Web Adapter    │
   ┌─────────────────────────┼──────── VPC 10.20.0.0/16 ────┼────────────────┐
   │ públicas: jobs ECS Fargate Spot (IP público) · fck-nat │ privadas       │
   │   ┌───────────────────────────────────┐            ┌───▼───┐  ┌──────┐  │
   │   │ task <job>: site (+ ocr sidecar)  │────────────► RDS   │  │ EFS  │  │
   │   │ python3 scripts/<x>.py            │────────────► pg16  │  │ cfg/ │  │
   │   └───────────▲───────────────────────┘            └───────┘  │ stag.│  │
   │               │ RunTask                        (opc.) Valkey  │ upl. │  │
   └───────────────┼────────────────────────────────────────────────────────┘
      EventBridge Scheduler (cron, BRT) ─┐        SQS def-events ◄── /webhook (Δ código)
      Step Functions nightly / run-job ◄─┴─ EventBridge Pipes ◄──────────────┘
```

## Mapeamento compose → AWS

| compose (hoje) | AWS | Observação |
|---|---|---|
| `site` Flask (`python main.py`, HTTPS self-signed) | **Lambda** container (`def-site-lambda`) + Function URL + Lambda Web Adapter | escala a zero; free tier permanente; ~3-5 s de cold start |
| `nginx` + `frontend/dist` | **S3 frontend + CloudFront** (função de rewrite p/ SPA) | sem container de nginx |
| `db` postgres:15 | **RDS PostgreSQL 16** `db.t4g.micro`, single-AZ, 20 GB gp3 | free tier no 1º ano; `CREATE EXTENSION vector` disponível |
| `minio` | **S3 media** (bucket único, chave `<plataforma>/<arquivo>`) | o cliente MinIO fala com `s3.<região>.amazonaws.com` |
| `redis` | **ElastiCache Serverless Valkey** (`redis_mode = serverless`) ou nada | só `/instagram/*` e o cache do price_validator usam |
| `info-scrap` | **sidecar** `ocr` nas tasks ECS que fazem OCR | zero custo ocioso |
| `vector_db` / `ollama` / `hsmart` | **Bedrock** (`enable_llm`) + **pgvector** no RDS | nada de GPU; `LLM_PROVIDER=bedrock` (Δ código) |
| `make prepare-* / stage / update-ml-prices / ...` | **ECS Fargate Spot** tasks, uma task definition por job | mesma imagem, só muda o comando |
| cron (não existia) | **EventBridge Scheduler** (fuso `America/Sao_Paulo`) | `var.schedules` |
| `scripts/pipeline_publish.py` encadeando | **Step Functions** `nightly` e `run-job` (`ecs:runTask.sync`) | 4 000 transições/mês grátis |
| webhook ML inline | **SQS** `def-events` → **EventBridge Pipes** → `run-job` | a rota publica na fila (Δ código) |
| `staging/`, `uploads/`, `config/ml_tokens.json` (bind mounts) | **EFS** (3 access points) montado nas tasks e no Lambda (`/mnt/config`) | sem mudar caminhos |
| `.env` | **SSM Parameter Store** SecureString `/def/prd/*` | grátis; rotação por CLI |
| Cloudflare quick tunnel | **domínio fixo** (CNAME no Cloudflare → CloudFront) | `ML_REDIRECT_URI` estável |
| GHCR + ngrok no CI | **ECR** + **GitHub OIDC** role | sem chave estática |

## Pré-requisitos

- AWS CLI autenticada numa conta com permissão de admin (só para o bootstrap/apply).
- Terraform ≥ 1.10, Docker, Node 22, `jq`.
- Um domínio (ex.: `def.com.br`) cujo DNS você controla (Cloudflare serve, modo *DNS only*).
- Imagem do `info-scrap` acessível (pública ou `ghcr_username` + `ghcr_pat`).

## Passo a passo

```bash
cd infra/aws

# 1. Bucket do estado (uma vez, estado local)
terraform -chdir=bootstrap init && terraform -chdir=bootstrap apply
terraform init $(terraform -chdir=bootstrap output -raw init_command | sed 's/^terraform -chdir=.. init//')

# 2. Variáveis
cp terraform.tfvars.example terraform.tfvars   # edite domain, segredos, e-mail

# 3. Repositórios primeiro (as imagens precisam existir antes do Lambda)
terraform apply -target=aws_ecr_repository.site -target=aws_ecr_repository.site_lambda
REG=$(terraform output -json ecr_repositories | jq -r .site | cut -d/ -f1)
aws ecr get-login-password | docker login --username AWS --password-stdin "$REG"
docker build -t def-site:base --build-arg REQUIREMENTS=requirements-prd.txt ../../services/site
docker build -f ../docker/Dockerfile.site --build-arg BASE_IMAGE=def-site:base -t "$REG/def-site:latest" ../..
docker build -f docker/Dockerfile.lambda --build-arg BASE_IMAGE="$REG/def-site:latest" -t "$REG/def-site-lambda:latest" ../..
docker push "$REG/def-site:latest" && docker push "$REG/def-site-lambda:latest"

# 4. Tudo. Durante o apply, crie no Cloudflare os CNAMEs de validação do ACM
#    (terraform output acm_validation_records) — a validação espera até 75 min.
terraform apply

# 5. DNS: CNAME def.com.br (e www) → $(terraform output -raw cloudfront_domain), DNS only.
# 6. Segredos que ficaram CHANGE_ME:
aws ssm put-parameter --name /def/prd/openai_api_key --type SecureString --overwrite --value '...'
aws ssm put-parameter --name /def/prd/ml_client_secret --type SecureString --overwrite --value '...'
#    (Lambda lê do ambiente: rode `terraform apply` de novo ou `aws lambda update-function-configuration`.)
# 7. No DevCenter do Mercado Livre: redirect URI = https://<domain>/auth/mercadolivre/callback
# 8. React
cd ../../frontend && npm ci && npm run build && cd ../infra/aws
aws s3 sync ../../frontend/dist s3://$(terraform output -json buckets | jq -r .frontend) --delete
```

### Migração dos dados

```bash
# Banco: dump local → S3 → restore por uma task one-off (a imagem do site tem psql via libpq)
docker exec postgres pg_dump -U user -d produtos_db --no-owner --no-acl | gzip > produtos.sql.gz
aws s3 cp produtos.sql.gz s3://$(terraform output -json buckets | jq -r .media)/_migration/produtos.sql.gz
aws stepfunctions start-execution --state-machine-arn $(terraform output -json state_machines | jq -r .run_job) \
  --input '{"job":"stage","args":["sh","-c","pip install -q awscli && aws s3 cp s3://<media>/_migration/produtos.sql.gz - | gunzip | psql \"$DATABASE_URL\""]}'

# Imagens: MinIO → S3 (um bucket por plataforma vira prefixo)
for b in mercadolivre shopee amazon; do mc mirror local/$b s3://<media-bucket>/$b/; done   # ou: aws s3 sync

# staging/, uploads/, config/ml_tokens.json → EFS: AWS DataSync (S3→EFS) ou task one-off com `aws s3 sync` para /app/<pasta>
```

## Operação (equivalentes do Makefile)

| Makefile | AWS (`terraform output handy_commands`) |
|---|---|
| `make prepare-ml URL=...` | `aws ecs run-task ... --overrides '{"containerOverrides":[{"name":"site","command":["python3","scripts/prepare_ml_best.py","https://meli.la/xxx"]}]}'` |
| `make stage` / `restage` | `aws stepfunctions start-execution --input '{"job":"stage"}'` / `{"job":"stage","args":["python3","scripts/stage_products.py","--force"]}` |
| `make update-ml-prices` + `verify-prices` + `tag-classify-db` | `nightly` (03:00 BRT, automático) ou `start-execution` na máquina `nightly` |
| `make publish` | schedule `publish` (6/6 h, desligado por padrão) ou `{"job":"publish"}` |
| `make populate-mf` | schedule `populate-mf` (segunda 05:00, desligado) |
| `make reprice-all` | **nunca agendado**; `{"job":"reprice-all"}` à mão |
| webhook ML → atualizar item | `aws sqs send-message --message-body '{"job":"api-update-ml","args":["python3","scripts/api_update_ml.py","https://meli.la/xxx"]}'` |
| logs | `aws logs tail /ecs/def-prd --follow` |

Habilitar/alterar um agendamento: edite `schedules` no tfvars (cron de 6
campos do Scheduler, fuso BRT) e `terraform apply`.

## Custo mensal estimado (us-east-1, preços de lista, estimativas)

Premissas: ~50 mil requisições/mês, 5 GB de imagens, jobs ~1 h/dia em
1 vCPU/2 GB, logs < 5 GB.

| Item | Mínimo (`redis_mode=none`, fck-nat) | Recomendado (+ Valkey, logs, Route 53) |
|---|---|---|
| Lambda (1024 MB, free tier permanente 1 M req + 400 k GB-s) | 0 – 1 | 0 – 1 |
| CloudFront (1 TB + 10 M req grátis) | 0 | 0 |
| S3 (5 GB + requisições) | 0,5 | 0,5 |
| RDS `db.t4g.micro` + 20 GB gp3 (free tier 750 h/mês no 1º ano) | 14 (0 no 1º ano) | 14 |
| EFS (< 1 GB) | 0,3 | 0,3 |
| fck-nat t4g.nano + IPv4 público + 8 GB EBS | 7,5 | 7,5 |
| ECS Fargate Spot (30 h) + IPv4 das tasks | 1 | 1,5 |
| EventBridge Scheduler/Pipes, SQS, Step Functions, SSM, Budgets | 0 | 0 |
| ECR (~4 GB além dos 500 MB grátis) | 0,4 | 0,4 |
| CloudWatch Logs/alarmes | 0 – 1 | 2 |
| ElastiCache Serverless Valkey (mín. 100 MB) | — | 6,5 |
| Route 53 zona hospedada (opcional) | — | 0,5 |
| **Total** | **≈ US$ 24 – 26** (≈ US$ 10 no 1º ano) | **≈ US$ 33 – 35** |

Alternativas: NAT Gateway no lugar do fck-nat soma ~US$ 33 + US$ 0,045/GB;
`db.t4g.small` (+US$ 12) se o Playwright/ORM apertar; Aurora Serverless v2 com
auto-pause (0 ACU) custa ~US$ 44 a 0,5 ACU constante — só compensa se o site
ficar horas sem acesso.

## Δ código necessários

1. **gunicorn / `PORT`** — `infra/docker/Dockerfile.site` já troca `python main.py`
   (debug, HTTPS self-signed) por gunicorn HTTP. Nada no código.
2. **MinIO client** (`services/minio_client.py`, `routes/media_routes.py`,
   `scripts/stage_products.py`): `secure=os.getenv("MINIO_SECURE","false")=="true"`
   e `region=os.getenv("MINIO_REGION")`. Hoje `secure=False` está fixo.
3. **Bucket único**: `stage_products.py` cria um bucket por plataforma; na AWS o
   bucket é `MINIO_BUCKET` e a plataforma vira prefixo do objeto
   (`<plataforma>/<arquivo>`). `MINIO_PUBLIC_ENDPOINT=https://<domain>/media`
   mantém as URLs `…/media/<plataforma>/<arquivo>` servidas pelo CloudFront.
4. **`INFO_SCRAP_URL`**: `prepare_ml_best.py`, `shopee_prepare_best.py`,
   `amazon_prepare_best.py` e `prepare_full.py` têm `http://info-scrap:8000`
   fixo; `verify_prices.py` já lê a env. Trocar todos por
   `os.getenv("INFO_SCRAP_URL", "http://info-scrap:8000")`.
5. **Webhook → SQS**: `routes/webhook_routes.py` deve publicar
   `{"job":"api-update-ml","args":[...]}` em `EVENTS_QUEUE_URL` (boto3) em vez
   de processar inline (e isso resolve o bug do `db` sem `init_app`).
6. **`REDIS_URL`** com TLS (`rediss://`) quando `redis_mode=serverless`; o
   código já lê `REDIS_URL`.
7. **`ml_tokens.json`**: no Lambda o filesystem é read-only exceto `/tmp`;
   `Dockerfile.lambda` faz `/app/config → /mnt/config` (EFS). Qualquer outra
   escrita do processo web (ex.: `staging/`) falharia — só os jobs escrevem.
8. **Origem protegida**: com `lambda_url_auth_type=AWS_IAM` (padrão), POST/PUT
   que passam pelo CloudFront precisam do header `x-amz-content-sha256`
   (SHA-256 do corpo) — um wrapper de `fetch` no React resolve, mas o webhook
   do Mercado Livre não envia esse header. Para o webhook funcionar, use
   `lambda_url_auth_type=NONE`: a URL fica pública e o Flask deve recusar
   requisições sem `x-origin-verify == ORIGIN_VERIFY_TOKEN` (middleware).
9. **`LLM_PROVIDER=bedrock`** (opcional): adaptador no `tag_classifier_agent`
   e `price_oracle_agent` usando `boto3.client("bedrock-runtime")`; vetores
   em pgvector no lugar do Qdrant.
10. **`ProxyFix`** no Flask (`X-Forwarded-Proto/Host`) para `url_for(_external=True)`
    gerar `https://<domain>`.

## Limitações

- Lambda: 30 s por requisição (Function URL até 15 min, mas o CloudFront corta em 60 s);
  cold start de 3-5 s na primeira visita após ociosidade (CloudFront cacheia `/api/*` por 60 s).
- `/webhook/health` é o readiness check do Web Adapter; sem ele o Lambda não sobe.
- fck-nat é uma única instância (sem HA): se cair, o Lambda perde saída para ML/OpenAI
  até o `aws_instance` ser recriado (`terraform apply -replace`).
- Fargate Spot pode interromper uma task; `run-job` tenta 3× com backoff.
- `aws_ssm_parameter` ignora mudanças de valor depois de criado (rotação só por CLI).

## Destruir

```bash
terraform apply -var deletion_protection=false   # libera RDS/ECR/S3 media
terraform destroy
terraform -chdir=bootstrap destroy               # o bucket tem prevent_destroy: remova à mão
```
