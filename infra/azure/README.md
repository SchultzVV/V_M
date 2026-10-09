# DEF na Azure — Container Apps + Jobs (Terraform)

Infra serverless para o catálogo DEF: o par `nginx+flask` do `docker-compose`
vira **um Container App** com dois containers (scale-to-zero), os `make
prepare|stage|update-ml-prices|...` viram **Container Apps Jobs** (cron em
UTC ou evento de fila), PostgreSQL gerenciado, Blob para imagens, Azure Files
para `staging/`, `uploads/` e `config/ml_tokens.json`, Key Vault para
segredos e OIDC para o GitHub Actions. Validado com `terraform validate`
(azurerm 4.x); **nunca aplicado** — custos são estimativas.

```
                 Internet                         GitHub Actions (OIDC, cicd.tf)
                    │ https://www.def.com.br            │ build → GHCR → az containerapp update
                    ▼                                   ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │ Container Apps Environment  cae-def-prd  (Consumption, Log Analytics)  │
   │                                                                        │
   │  ca-def-prd-web (0..3 réplicas, ingress :8080, cert gerenciado)        │
   │   ├─ web   nginx + React dist  ──proxy──▶  site  Flask/gunicorn :5000  │
   │   │        /media/* ──▶ Blob                       └─ /app/config (Files)│
   │                                                                        │
   │  ca-def-prd-ocr  (interno, 0..1)  ◀── INFO_SCRAP_URL ── jobs           │
   │                                                                        │
   │  caj-def-prd-*  Jobs (1 vCPU/2 GiB, Files: staging uploads config)     │
   │   nightly (cron 06:00 UTC) · publish · stage · prepare-ml · verify ... │
   │   api-update-ml (KEDA azure-queue ◀── fila `events`)                   │
   └───────┬───────────────┬───────────────┬────────────────┬───────────────┘
           ▼               ▼               ▼                ▼
   psql-def-prd      stdefprd… (Blob    kv-def-prd-…    oai-def-prd (opcional)
   Flexible B1ms     media · Files ·    Key Vault       gpt-4o-mini
   PG16 + pgvector   Queue events)      (RBAC, MI)      (substitui Ollama/hsmart)
```

## Mapeamento compose → Azure

| docker-compose | Azure | Observação |
|---|---|---|
| `nginx` + `frontend/dist` | container `web` do `ca-def-prd-web` (`infra/docker/Dockerfile.web`) | TLS, HTTP/2 e domínio pelo ingress; cert gerenciado grátis |
| `site` (Flask) | container `site` no mesmo app (`infra/docker/Dockerfile.site`, gunicorn) | `127.0.0.1:5000`; mesma imagem roda os jobs |
| `db` postgres:15 | `azurerm_postgresql_flexible_server` PG16 `B_Standard_B1ms` 32 GB | acesso público + TLS; `azure.extensions=VECTOR` (pgvector) |
| `minio` | Storage Account: container Blob `media` (leitura pública) | **Blob não tem API S3 → adaptador (Δ código)** |
| volumes `staging/`, `uploads/`, `config/` | Azure Files `staging`, `uploads`, `config` montados em `/app/...` | compartilhados entre site e jobs |
| `redis` | `redis_mode=managed` → Azure Cache for Redis Basic C0 (TLS 6380) | padrão `none`; só agentes IG/price-oracle usam |
| `info-scrap` | `ca-def-prd-ocr` (ingress interno, 0..1 réplica) | jobs chamam `INFO_SCRAP_URL` |
| `vector_db` Qdrant, `ollama`, `hsmart` | `enable_llm=true` → Azure OpenAI `gpt-4o-mini` + pgvector | sem GPU; `LLM_PROVIDER=azure-openai` (Δ código) |
| `make <alvo>` manual / `docker exec` | `azurerm_container_app_job` (cron, manual ou fila) | `az containerapp job start --args ...` |
| túnel Cloudflare | domínio próprio no ingress (`enable_custom_domain`) | URL estável para `ML_REDIRECT_URI` e Graph API |
| `.env` | Key Vault + referências por identidade gerenciada | rotação sem redeploy (`ignore_changes`) |
| GHCR (CI atual) | GHCR continua (`ghcr_pat` se privado) ou `enable_acr` | ACR Basic ≈ US$ 5/mês |

## Pré-requisitos

- `az login` (Owner ou Contributor + User Access Administrator na subscription:
  o módulo cria role assignments), Terraform ≥ 1.10.
- Providers registrados uma vez:
  ```bash
  az provider register -n Microsoft.App
  az provider register -n Microsoft.OperationalInsights
  az provider register -n Microsoft.DBforPostgreSQL
  az provider register -n Microsoft.CognitiveServices   # só se enable_llm
  ```
- Imagens publicadas (CI em `ci/deploy-azure.yml`): `ghcr.io/<org>/def-site:<tag>`
  (base `services/site/Dockerfile` + `infra/docker/Dockerfile.site`) e
  `ghcr.io/<org>/def-web:<tag>` (`infra/docker/Dockerfile.web`).
- Para **Azure OpenAI** a subscription precisa de acesso aprovado.

## Passo a passo

```bash
# 0) estado remoto
cd infra/azure/bootstrap && terraform init && terraform apply
terraform output -raw backend_hcl > ../backend.hcl && cd ..

# 1) primeira aplicação (sem domínio próprio ainda)
cp terraform.tfvars.example terraform.tfvars   # preencha subscription_id, segredos, alert_email
terraform init -backend-config=backend.hcl
terraform apply -var enable_custom_domain=false

# 2) DNS (no provedor do domínio) com os valores de `terraform output custom_domain_dns_records`
#    TXT   asuid.www.def.com.br  = <custom_domain_verification_id>
#    CNAME www.def.com.br        = ca-def-prd-web.<default_domain>
terraform apply                                   # enable_custom_domain=true → cert gerenciado

# 3) migração de dados (libere seu IP: -var operator_ip=$(curl -s ifconfig.me))
pg_dump "$DATABASE_URL_LOCAL" --no-owner --no-acl | \
  psql "postgresql://def_app:$(az keyvault secret show --vault-name $(terraform output -raw key_vault_name) -n admin-password -q)@$(terraform output -raw postgres_fqdn):5432/produtos_db?sslmode=require"
#    (a senha do banco está no secret `database-url`; o comando acima é ilustrativo)
mc mirror local/mercadolivre /tmp/media/mercadolivre          # exporta do MinIO local, 1 pasta por bucket
azcopy copy "/tmp/media/*" "https://$(terraform output -raw storage_account).blob.core.windows.net/media" --recursive
az storage file upload-batch --account-name <st…> -d staging -s services/site/staging
az storage file upload-batch --account-name <st…> -d uploads -s services/site/uploads
az storage file upload --account-name <st…> -s config --source services/site/config/ml_tokens.json

# 4) Mercado Livre DevCenter: Redirect URI = https://www.def.com.br/auth/mercadolivre/callback
# 5) GitHub: secrets AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_SUBSCRIPTION_ID (terraform output github_oidc)
```

O Terraform grava os segredos iniciais no Key Vault e depois **ignora
mudanças de valor**: rotacione com `az keyvault secret set --vault-name … -n
ml-client-secret --value …` e reinicie a revisão (`az containerapp revision
restart`). Valores vazios viram `CHANGE-ME`.

## Operação dos jobs

| Job | Comando | Trigger padrão |
|---|---|---|
| `nightly` | `update_ml_prices_right` → `verify_prices --all` → `tag_classifier --db` | cron `0 6 * * *` (03:00 BRT) |
| `publish` | `scripts/pipeline_publish.py` | manual (`schedules.publish.enabled=true` → a cada 6 h) |
| `stage` | `scripts/stage_products.py` | manual |
| `prepare-ml` | `scripts/prepare_ml_best.py <URL>` (`FORCE_CATEGORY=auto`) | manual com `--args` |
| `update-ml-prices`, `verify-prices`, `tag-classify`, `populate-mf` | idem Makefile | manual / cron opcional |
| `reprice-all` | `agents/reprice_all.py` (**apaga** preço 0) | manual, nunca agendado |
| `api-update-ml` | `infra_scripts/run_from_queue.py` → `scripts/api_update_ml.py <URL>` | fila `events` (KEDA) |

```bash
az containerapp job start -g rg-def-prd -n caj-def-prd-prepare-ml --args "scripts/prepare_ml_best.py" "https://meli.la/xxxx"
az containerapp job start -g rg-def-prd -n caj-def-prd-stage
az storage message put --account-name <st…> --auth-mode login --queue-name events \
   --content '{"args":["scripts/api_update_ml.py","https://meli.la/xxxx"]}'
az containerapp job execution list -g rg-def-prd -n caj-def-prd-nightly -o table
az containerapp job logs show -g rg-def-prd -n caj-def-prd-nightly --container site
```

Trocar o cron ou ligar/desligar um agendamento recria o job (trigger é
imutável na API) — sem impacto nos dados, que vivem nos file shares.

## Custo mensal estimado (USD, eastus, preços de lista 2026 — estimativa)

Premissas: ~50 mil requisições/mês, 5 GB de imagens, jobs ≈ 1 h/dia a
1 vCPU/2 GiB, OCR ≈ 20 min/dia, logs < 1 GB.

| Item | Mínimo | Recomendado | Nota |
|---|---:|---:|---|
| Container App web (0,75 vCPU / 1,5 GiB) | ~3 | ~12 | min 0 réplicas vs min 1 (idle cobra ~1/8 do ativo); 180 k vCPU-s + 360 k GiB-s grátis/mês |
| Jobs (≈ 30 h/mês) | ~2 | ~2 | mesmo free tier; `nightly` ≈ 15 min |
| OCR `ca-def-prd-ocr` | ~1 | ~1 | escala a zero |
| PostgreSQL Flexible `B1ms` + 32 GB + backup 7 d | ~16 | ~16 | brazilsouth ≈ 22; parar o servidor fora de uso: `az postgres flexible-server stop` |
| Storage (Blob 5 GB + 3 Files 5 GB + fila) | ~2 | ~2 | Files transaction-optimized ~US$ 0,06/GB |
| Log Analytics (≤ 1 GB, quota diária 1 GB) | ~0 | ~2 | 5 GB grátis nos primeiros 31 dias; depois ~US$ 2,30/GB |
| Key Vault, identidade, orçamento, alertas | ~1 | ~2 | ~US$ 0,10/alerta/mês |
| Redis Basic C0 (`redis_mode=managed`) | — | 16 | opcional |
| ACR Basic (`enable_acr`) | — | 5 | opcional; GHCR = 0 |
| Azure OpenAI gpt-4o-mini (`enable_llm`) | — | ~1–5 | por token (US$ 0,15/1 M entrada); sem custo fixo |
| Front Door Standard (CDN/WAF) | — | ~35 + | **não incluído**; cert gerenciado do ingress é grátis |
| **Total** | **≈ 25** | **≈ 35–55** | sem Front Door; com Redis+ACR+LLM ≈ 60 |

## Δ código necessários

1. **gunicorn/`PORT`** — já resolvido por `infra/docker/Dockerfile.site`
   (`python main.py` roda com `debug=True` e cert self-signed).
2. **Adaptador Blob (maior Δ)** — `services/minio_client.py`,
   `routes/media_routes.py` e `scripts/stage_products.py` usam o cliente
   MinIO (S3). O Blob **não** fala S3: criar `services/storage.py` com
   `azure-storage-blob` (`AZURE_STORAGE_CONNECTION_STRING` ou identidade via
   `AZURE_CLIENT_ID`) e URL pública `MINIO_PUBLIC_ENDPOINT/media/<obj>`.
   Alternativa sem Δ: subir o MinIO como Container App com Azure Files
   (não recomendado: +US$ 10/mês e imagem `bitnamilegacy`).
3. **`INFO_SCRAP_URL`** — `prepare_ml_best.py`, `shopee_prepare_best.py`,
   `amazon_prepare_best.py`, `prepare_full.py` têm `http://info-scrap:8000`
   fixo; ler do env (como `verify_prices.py` já faz).
4. **Webhook ML → fila** — `/webhook/mercadolivre` deve enfileirar
   `{"args":["scripts/api_update_ml.py","<url|id>"]}` em `events`
   (`azure-storage-queue`, `EVENTS_QUEUE`), além de consertar o bug do `db`
   (CLAUDE.md §2.3).
5. **`run_from_queue.py` na imagem** — `COPY infra/azure/scripts
   /app/infra_scripts` + `pip install azure-identity azure-storage-queue`.
6. **`REDIS_URL` com TLS** — `rediss://` (o código monta `REDIS_HOST/PORT`
   em alguns pontos; usar `redis.from_url`).
7. **`ml_tokens.json`** — continua em `/app/config` (file share
   compartilhado); nada muda no código, mas o arquivo sai do git (F0).
8. **`LLM_PROVIDER=azure-openai`** (se `enable_llm`) — `AzureChatOpenAI`
   com `AZURE_OPENAI_ENDPOINT` + identidade (`DefaultAzureCredential`) em
   vez de `hsmart`/Ollama; vetores em pgvector (`CREATE EXTENSION vector`).

## Limitações e decisões

- **Domínio**: o provider emite o certificado gerenciado com validação
  **CNAME** → use subdomínio (`www.`). Para apex (`def.com.br`) faça
  `az containerapp hostname bind … --validation-method TXT` à mão (A record
  no `static_ip_address` do ambiente) ou redirecione o apex no DNS.
- **Azure Files (SMB)** é lento para muitos arquivos pequenos; `staging/`
  tem ~100 JSONs, aceitável. Não monte sobre `/app` inteiro.
- **Cron em UTC**; a execução é limitada por `replica_timeout_in_seconds`
  (3600) — `populate-mf` com `LIMIT` alto pode estourar.
- **Job por evento** não recebe o payload: o wrapper tira a mensagem da
  fila (visibility timeout 25 min; falha → a mensagem volta).
- **Postgres público** com TLS e firewall "Azure services": egress das
  Container Apps Consumption não tem IP fixo. Para rede privada: VNet +
  `infrastructure_subnet_id` + Private DNS (≈ +US$ 0, mas workload profile
  Dedicated custa a partir de ~US$ 70).
- **Scale-to-zero** do site custa ~5–10 s no primeiro acesso; `web_min_replicas=1`
  resolve por ~US$ 10/mês.
- **RBAC** demora a propagar: há `time_sleep` de 60/90 s no primeiro apply.
- **Alertas**: 5xx do site (>20 em 5 min) e `Executions{state=Failed}` por job.

## Destruir

```bash
terraform destroy          # apaga RG inteiro (banco, blobs, file shares!)
az keyvault purge --name <kv-def-prd-…>   # se purge protection estiver desligado
cd bootstrap && terraform destroy          # estado remoto (por último)
```
