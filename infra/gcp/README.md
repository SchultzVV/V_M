# DEF no Google Cloud — Terraform

Infra serverless para o catálogo DEF: **Cloud Run** (site), **Cloud Run Jobs**
(prepare/stage/preços), **Cloud Scheduler + Workflows + Eventarc** (gatilhos),
**Cloud SQL** (Postgres), **Cloud Storage** (imagens e dados de trabalho),
**Secret Manager**, **Artifact Registry** e, opcionalmente, LB global + Cloud CDN,
Memorystore e Vertex AI. Tudo escala a zero exceto o Cloud SQL.

```
                 Cloudflare DNS (A → IP do LB)        GitHub Actions (OIDC/WIF)
                            │                                   │ push imagens
                            ▼                                   ▼
   ┌─────────────────────────────────────────┐      ┌──────────────────────┐
   │ Global External ALB + Cloud CDN + cert  │      │ Artifact Registry    │
   │ (enable_lb)  — ou *.run.app / Firebase  │      │ def/def-site def-web │
   └───────────────┬─────────────────────────┘      │ ghcr/ (proxy OCR)    │
                   ▼ serverless NEG                 └──────────────────────┘
   ┌─────────────────────────────────────────┐
   │ Cloud Run service def-prd-web (min 0)   │     ┌────────────────────────┐
   │  [web] nginx+React :8080 ──► [site]     │────►│ Cloud SQL Postgres 16  │
   │        /media/* → GCS        Flask :5000│     │ db-f1-micro (socket)   │
   └───────────────┬────────────┬────────────┘     └────────────────────────┘
                   │            │ /app/config (gcsfuse)
                   │            ▼
                   │   ┌──────────────────────┐   ┌──────────────────────────┐
                   │   │ GCS def-prd-appdata  │   │ GCS def-prd-media (públ.)│
                   │   │ staging/ uploads/    │   │ imagens via API S3 (HMAC)│
                   │   │ config/ml_tokens.json│   └──────────────────────────┘
                   │   └──────────┬───────────┘
   webhook ML ─────┘              │ montado em /app/staging /app/uploads /app/config
      │ publish                   ▼
   Pub/Sub def-prd-events ─► Eventarc ─► Workflow run-job ─┐
   Cloud Scheduler (cron BRT) ─────────► Workflow nightly ──┼─► Cloud Run Jobs
   Cloud Scheduler (cron BRT) ─────────────── jobs.run ─────┘   def-prd-<job>
                                                                [site] python3 …
                                                                [ocr]  info-scrap (sidecar)
```

## Mapeamento compose → GCP

| compose | GCP | observação |
|---|---|---|
| `nginx` + `frontend/dist` | container `web` do serviço Cloud Run (`infra/docker/Dockerfile.web`) | HTTP :8080; TLS no LB |
| `site` (Flask) | sidecar `site` do mesmo serviço (`infra/docker/Dockerfile.site`, gunicorn :5000) | mesma imagem roda os jobs |
| `db` Postgres 15 | Cloud SQL Postgres 16 `db-f1-micro`, zonal, backup 7 dias | socket `/cloudsql/<conn>`; IP público sem redes autorizadas |
| `minio` | bucket `def-prd-media` + chave HMAC (API S3/XML do GCS) | cliente MinIO continua; `MINIO_ENDPOINT=storage.googleapis.com`, `MINIO_SECURE=true` |
| `redis` | nada (`redis_mode=none`) ou Memorystore BASIC 1 GB | só agentes Instagram/price oracle usam |
| `info-scrap` | sidecar `ocr` nos jobs com OCR (`ocr_mode=sidecar`) ou serviço interno | custo zero em repouso |
| `vector_db`, `ollama`, `hsmart` | Vertex AI (`enable_llm`) + pgvector no Cloud SQL | `LLM_PROVIDER=vertex`; Δ código |
| `make <job>` + `docker exec` | Cloud Run Jobs `def-prd-<job>` | `gcloud run jobs execute … --args=` |
| cron manual | Cloud Scheduler (fuso `America/Sao_Paulo`) + Workflows | `var.schedules`, `var.nightly_cron` |
| túnel Cloudflare | LB global + certificado gerenciado (ou Firebase Hosting) | domínio fixo → Graph API e webhook ML viáveis |
| `.env` | Secret Manager (`DEF_PRD_<NOME>`) + env em texto puro | rotação fora do Terraform |
| `staging/`, `uploads/`, `config/` | bucket `def-prd-appdata` montado por gcsfuse (`only-dir`) | sem mudança de caminho no código |

## Pré-requisitos

- Projeto GCP com faturamento; `gcloud` autenticado (`gcloud auth application-default login`).
- Terraform ≥ 1.10, Docker, domínio próprio (DNS no Cloudflare em modo **DNS only**).
- Permissões: Owner no projeto (primeiro apply habilita APIs, IAM, WIF). Orçamento exige
  `roles/billing.costsManager` na conta de faturamento.
- Se `ghcr.io/schultzvv/info_scrap` for privado: PAT GitHub com `read:packages`
  (`ghcr_username`/`ghcr_token`). Cloud Run não puxa do ghcr.io: o Artifact Registry
  `ghcr` faz proxy.

## Passo a passo

```bash
cd infra/gcp

# 1. estado remoto
terraform -chdir=bootstrap init
terraform -chdir=bootstrap apply -var project_id=SEU_PROJETO
terraform init -backend-config="bucket=$(terraform -chdir=bootstrap output -raw tfstate_bucket)"

# 2. variáveis
cp terraform.tfvars.example terraform.tfvars   # edite project_id, domain, segredos

# 3. primeiro apply (APIs, SQL, buckets, registry, IAM, WIF). As imagens ainda não existem:
#    o Cloud Run falha ao criar → por isso construa e envie as imagens ANTES do apply completo.
terraform apply -target=google_project_service.apis -target=google_artifact_registry_repository.def
gcloud auth configure-docker southamerica-east1-docker.pkg.dev
REG=southamerica-east1-docker.pkg.dev/SEU_PROJETO/def
docker build --build-arg REQUIREMENTS=requirements-prd.txt -t def-site:base ../../services/site
docker build -f ../docker/Dockerfile.site --build-arg BASE_IMAGE=def-site:base -t $REG/def-site:latest ../..
docker build -f ../docker/Dockerfile.web -t $REG/def-web:latest ../..
docker push $REG/def-site:latest && docker push $REG/def-web:latest
terraform apply

# 4. migração de dados
pg_dump -Fp --no-owner --no-acl postgresql://user:password@localhost:5432/produtos_db > dump.sql
gcloud storage cp dump.sql gs://$(terraform output -json buckets | jq -r .appdata)/dump.sql
gcloud sql import sql def-prd-pg gs://.../dump.sql --database=produtos_db --user=def_app
mc mirror local-minio/mercadolivre gs-media/def-prd-media/mercadolivre   # ou gcloud storage rsync por bucket MinIO
gcloud storage rsync -r ../../services/site/staging gs://def-prd-appdata/staging
gcloud storage rsync -r ../../services/site/uploads gs://def-prd-appdata/uploads
gcloud storage cp ../../services/site/config/ml_tokens.json gs://def-prd-appdata/config/ml_tokens.json

# 5. DNS e OAuth
terraform output lb_ip        # registro A no Cloudflare (DNS only); cert gerenciado leva ~15-60 min
#   DevCenter do Mercado Livre: redirect URI = https://<domain>/auth/mercadolivre/callback
#   Dead-letter do Eventarc (opcional):
gcloud pubsub subscriptions update $(gcloud pubsub subscriptions list --filter="name~def-prd-events" --format='value(name)') \
  --dead-letter-topic=def-prd-events-dlq --max-delivery-attempts=5

# 6. CI/CD: copie ci/deploy-gcp.yml para .github/workflows/ e configure
#    vars.GCP_PROJECT_ID, GCP_REGION, GCP_WIF_PROVIDER (output wif_provider), GCP_DEPLOY_SA
```

Os `MINIO_*` antigos: o app continua usando o cliente MinIO, mas agora contra
`storage.googleapis.com` com a chave HMAC gerada (segredos `DEF_PRD_MINIO_ACCESS_KEY`
/`_SECRET_KEY`). Cada bucket do MinIO (`mercadolivre`, `shopee`, `amazon`) vira um
**prefixo** dentro de `def-prd-media` (nomes de bucket no GCS são globais).

## Jobs: à mão, por cron e por evento

| job | comando | OCR | como dispara |
|---|---|---|---|
| `prepare-ml` | `scripts/prepare_ml_best.py <URL>` | sidecar | `gcloud run jobs execute def-prd-prepare-ml --args=scripts/prepare_ml_best.py,https://meli.la/xxx --wait` |
| `stage` | `scripts/stage_products.py` | — | manual / após prepare |
| `publish` | `scripts/pipeline_publish.py` | sidecar | Scheduler `publish` (desligado por padrão) |
| `update-ml-prices` | `scripts/update_ml_prices_right.py` | — | workflow `nightly` 03:00 BRT |
| `verify-prices` | `scripts/verify_prices.py --all` | sidecar | `nightly` + Scheduler seg 04:00 |
| `tag-classify` | `agents/tag_classifier_agent.py --db` | — | `nightly` |
| `populate-mf` | `agents/ml_populator_agent.py --limit 5` | sidecar | Scheduler dom 05:00 (desligado) |
| `reprice-all` | `agents/reprice_all.py` | — | **nunca agendado** (apaga preço 0); manual |
| `api-update-ml` | `scripts/api_update_ml.py <URL>` | — | Pub/Sub `def-prd-events` → Eventarc → Workflow `run-job` |

Evento (mesmo caminho que o webhook do ML deve usar):

```bash
gcloud pubsub topics publish def-prd-events \
  --message='{"job":"api-update-ml","args":["scripts/api_update_ml.py","https://meli.la/xxx"]}'
```

Para adicionar um job: nova entrada em `local.jobs` (`locals.tf`) e, se for cron,
em `var.schedules`. `args` do Scheduler/evento **substituem** os args do container,
então inclua o script.

**Sidecar OCR nos jobs.** O info-scrap sobe como sidecar (`ocr`) com startup probe
TCP :8000 e o container `site` declara `depends_on = ["ocr"]`, como exige a
documentação de sidecars em jobs. A tarefa é dada como concluída pelo código de
saída do container principal; o sidecar é encerrado junto com a instância. Se em
algum momento a execução ficar "pendurada" esperando o sidecar, troque para
`ocr_mode = "service"`: o OCR vira um serviço Cloud Run interno (min 0) alcançado
pelos jobs por Direct VPC egress, e `INFO_SCRAP_URL` passa a apontar para ele.
Há ainda um problema conhecido documentado pelo Google envolvendo jobs com
múltiplos containers **e** a conexão Cloud SQL embutida; se aparecer, o caminho
alternativo é Cloud SQL com IP privado + Direct VPC egress (`DATABASE_URL` com o
IP privado), sem o volume `/cloudsql`.

## Custos mensais estimados (USD, lista pública, **estimativa**)

Premissas: ~50 mil requisições/mês, 5 GB de imagens, jobs ~1 h/dia (2 vCPU / 3 GiB
com o sidecar), `southamerica-east1` (us-central1 ≈ 25-30 % mais barato).

| item | mínimo | recomendado | nota |
|---|---|---|---|
| Cloud Run web (2 containers, min 0, cpu_idle) | 0-3 | 0-5 | dentro do free tier (2 M req, 360 k GiB-s); `web_min_instances=1` ≈ +20-25 |
| Cloud Run Jobs (~30 h/mês) | 4-8 | 4-8 | 2 vCPU ativos + memória |
| Cloud SQL `db-f1-micro` + 10 GB SSD + backups | 11-15 | 11-15 | sem SLA; `db-g1-small` ≈ 30 |
| GCS (media + appdata, 5 GB + egress) | 1 | 1 | 5 GB-mês grátis em regiões US |
| LB global + Cloud CDN + cert gerenciado | 0 (`enable_lb=false`) | 19-21 | regra de encaminhamento US$ 0,025/h |
| Scheduler, Workflows, Pub/Sub, Eventarc, Secret Manager, Artifact Registry, Logging | 0-2 | 0-2 | free tiers cobrem (3 jobs, 5 k passos, 10 GB, 6 versões, 0,5 GB) |
| Memorystore Redis BASIC 1 GB (`redis_mode=memorystore`) | — | +35-50 | opcional |
| Vertex AI Gemini Flash-Lite (`enable_llm`) | — | +0-3 | por token |
| **Total** | **≈ 16-29** | **≈ 35-52** | com Memorystore + min 1: ≈ 95-125 |

Sem LB (`enable_lb=false`): use **Firebase Hosting** (custom domain, TLS e CDN
grátis) com `rewrites` de tudo para o serviço Cloud Run, ou Cloudflare proxied
apontando para um domain mapping (preview, não disponível em southamerica-east1).

## Δ código necessários (fora deste módulo)

1. **gunicorn/PORT** — `infra/docker/Dockerfile.site` troca `python main.py` (debug,
   HTTPS self-signed) por `gunicorn … main:app` em HTTP na porta `PORT`.
2. **Cliente MinIO** — `secure=False` está fixo em `services/minio_client.py`,
   `routes/media_routes.py` e `scripts/stage_products.py`; ler
   `MINIO_SECURE=true` do ambiente (GCS exige HTTPS).
3. **Bucket único** — `stage_products.py` usa `bucket_name = platform`; passar a
   usar `MINIO_BUCKET` com prefixo `<platform>/…`. `MINIO_PUBLIC_ENDPOINT` já é lido.
4. **`INFO_SCRAP_URL`** — `prepare_ml_best.py`, `shopee_prepare_best.py`,
   `amazon_prepare_best.py`, `prepare_full.py` têm `http://info-scrap:8000` fixo;
   `verify_prices.py` já lê a variável. Padrão: `http://127.0.0.1:8000`.
5. **Webhook ML → Pub/Sub** — `/webhook/mercadolivre` deve publicar
   `{"job":"api-update-ml","args":[…]}` em `EVENTS_TOPIC` (`google-cloud-pubsub`)
   em vez de processar inline (e corrigir a instância `db` do `marketplace_service`).
6. **`REDIS_URL` opcional** — `agents/__init__.py`, `instagram_routes.py` e
   `price_validator/ml_api.py` precisam tolerar ausência de Redis.
7. **`ml_tokens.json`** — continua em `config/`, agora em `/app/config` montado do
   bucket (gcsfuse reescreve o objeto inteiro a cada gravação: OK para um arquivo pequeno).
8. **LLM** — com `enable_llm`, `LLM_PROVIDER=vertex` precisa de um provider Vertex no
   lugar de `hsmart`/Ollama; vetores com `CREATE EXTENSION vector` no Cloud SQL.

## Limitações

- Cloud Run Jobs: timeout máx. 24 h por tarefa; Playwright precisa de ≥ 2 GiB.
- gcsfuse: sem bloqueio de arquivo e latência de listagem; `staging/.processed` é
  reescrito inteiro (OK). Não use para SQLite.
- `db-f1-micro` não tem SLA e compartilha vCPU; suba para `db-g1-small` se a API
  ficar lenta.
- Certificado gerenciado só fica ativo depois que o DNS aponta para `lb_ip`.
- Org policies (`iam.allowedPolicyMemberDomains`) podem bloquear `allUsers`.

## Destruir

```bash
terraform apply -var deletion_protection=false   # libera Cloud SQL e buckets
terraform destroy
terraform -chdir=bootstrap destroy               # bucket de estado (force_destroy=false: esvazie antes)
```
