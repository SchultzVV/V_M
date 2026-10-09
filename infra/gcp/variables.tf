# ------------------------------------------------------------------
# Projeto / ambiente
# ------------------------------------------------------------------
variable "project_id" {
  description = "ID do projeto GCP."
  type        = string
}

variable "region" {
  description = "Região principal (Cloud Run, Cloud SQL, buckets). us-central1 é ~25-30% mais barata que southamerica-east1."
  type        = string
  default     = "southamerica-east1"
}

variable "environment" {
  description = "Sufixo do ambiente (prd, stg...). Prefixo dos recursos = def-<environment>."
  type        = string
  default     = "prd"
}

variable "labels" {
  description = "Labels extras aplicadas a todos os recursos."
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------------
# Domínio / borda
# ------------------------------------------------------------------
variable "domain" {
  description = "Domínio público do site (ex.: def.com.br). Usado no certificado gerenciado, CORS, ML_REDIRECT_URI e uptime check."
  type        = string

  validation {
    condition     = length(var.domain) > 0
    error_message = "Informe o domínio público (ex.: def.com.br)."
  }
}

variable "extra_domains" {
  description = "Domínios adicionais no certificado gerenciado (ex.: [\"www.def.com.br\"])."
  type        = list(string)
  default     = []
}

variable "enable_lb" {
  description = "true = Global External Application LB + Cloud CDN + certificado gerenciado (~US$ 18/mês). false = só a URL *.run.app (use Firebase Hosting ou Cloudflare na frente)."
  type        = bool
  default     = true
}

# ------------------------------------------------------------------
# Imagens
# ------------------------------------------------------------------
variable "image_tag" {
  description = "Tag das imagens def-site e def-web no Artifact Registry (ex.: SHA do commit)."
  type        = string
  default     = "latest"
}

variable "image_site" {
  description = "Imagem completa do Flask (infra/docker/Dockerfile.site). Vazio = <region>-docker.pkg.dev/<project>/def/def-site:<image_tag>."
  type        = string
  default     = ""
}

variable "image_web" {
  description = "Imagem completa do nginx+React (infra/docker/Dockerfile.web). Vazio = <region>-docker.pkg.dev/<project>/def/def-web:<image_tag>."
  type        = string
  default     = ""
}

variable "image_ocr" {
  description = "Imagem do info-scrap (OCR). Vazio = ghcr.io/schultzvv/info_scrap:latest via repositório remoto do Artifact Registry (Cloud Run não puxa do ghcr.io diretamente)."
  type        = string
  default     = ""
}

variable "ghcr_username" {
  description = "Usuário GitHub para o repositório remoto ghcr (só se info_scrap for privado)."
  type        = string
  default     = ""
}

variable "ghcr_token" {
  description = "PAT GitHub (read:packages) para o repositório remoto ghcr (só se info_scrap for privado)."
  type        = string
  default     = ""
  sensitive   = true
}

# ------------------------------------------------------------------
# Cloud Run (web)
# ------------------------------------------------------------------
variable "web_min_instances" {
  description = "Instâncias mínimas do serviço web (0 = scale-to-zero, cold start ~3-5 s; 1 = ~US$ 20-25/mês)."
  type        = number
  default     = 0
}

variable "web_max_instances" {
  description = "Instâncias máximas do serviço web."
  type        = number
  default     = 3
}

# ------------------------------------------------------------------
# Cloud Run Jobs
# ------------------------------------------------------------------
variable "job_cpu" {
  description = "vCPU do container site nos jobs."
  type        = string
  default     = "1"
}

variable "job_memory" {
  description = "Memória do container site nos jobs (Playwright precisa de >= 2Gi)."
  type        = string
  default     = "2Gi"
}

variable "job_timeout_seconds" {
  description = "Timeout de cada execução de job (máx. 86400)."
  type        = number
  default     = 3600
}

variable "ocr_mode" {
  description = "sidecar = info-scrap como sidecar dos jobs que usam OCR (custo zero em repouso). service = Cloud Run service interno def-<env>-ocr (fallback se o sidecar não encerrar junto com o job)."
  type        = string
  default     = "sidecar"

  validation {
    condition     = contains(["sidecar", "service"], var.ocr_mode)
    error_message = "ocr_mode deve ser sidecar ou service."
  }
}

variable "ocr_memory" {
  description = "Memória do container OCR."
  type        = string
  default     = "1Gi"
}

# ------------------------------------------------------------------
# Agendamentos (Cloud Scheduler → Cloud Run Jobs)
# ------------------------------------------------------------------
variable "schedules" {
  description = "Agendamentos de jobs. Chave = nome do agendamento; job = chave de local.jobs; cron no fuso America/Sao_Paulo; args sobrescreve os args do container (inclua o script)."
  type = map(object({
    job     = string
    cron    = string
    args    = optional(list(string), [])
    enabled = optional(bool, true)
  }))
  default = {
    verify-prices = {
      job  = "verify-prices"
      cron = "0 4 * * 1"
    }
    publish = {
      job     = "publish"
      cron    = "15 */6 * * *"
      enabled = false
    }
    populate-mf = {
      job     = "populate-mf"
      cron    = "0 5 * * 0"
      args    = ["agents/ml_populator_agent.py", "--limit", "5"]
      enabled = false
    }
    reprice-all = {
      job     = "reprice-all"
      cron    = "0 6 * * 0"
      enabled = false
    }
  }
}

variable "nightly_cron" {
  description = "Cron (America/Sao_Paulo) do workflow noturno update-ml-prices → verify-prices → tag-classify. Vazio desativa."
  type        = string
  default     = "0 3 * * *"
}

variable "nightly_jobs" {
  description = "Sequência de jobs do workflow noturno (chaves de local.jobs)."
  type        = list(string)
  default     = ["update-ml-prices", "verify-prices", "tag-classify"]
}

# ------------------------------------------------------------------
# Banco / cache / LLM
# ------------------------------------------------------------------
variable "db_tier" {
  description = "Tier do Cloud SQL (db-f1-micro ~US$ 8-11/mês, sem SLA; db-g1-small ~US$ 25; db-custom-1-3840 ~US$ 50)."
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_size_gb" {
  description = "Disco inicial do Cloud SQL (GB, autoresize ligado)."
  type        = number
  default     = 10
}

variable "deletion_protection" {
  description = "Protege Cloud SQL e buckets contra terraform destroy acidental."
  type        = bool
  default     = true
}

variable "redis_mode" {
  description = "none = sem Redis (REDIS_URL ausente; /instagram/* e cache ficam desligados). memorystore = Memorystore for Redis BASIC 1 GB + VPC + Direct VPC egress (~US$ 35-50/mês)."
  type        = string
  default     = "none"

  validation {
    condition     = contains(["none", "memorystore"], var.redis_mode)
    error_message = "redis_mode deve ser none ou memorystore."
  }
}

variable "enable_llm" {
  description = "Habilita Vertex AI (Gemini) e dá roles/aiplatform.user ao runtime. Substitui Ollama/hsmart/Qdrant (vetores via pgvector no Cloud SQL)."
  type        = bool
  default     = false
}

# ------------------------------------------------------------------
# Segredos (viram Secret Manager; rotacione fora do Terraform)
# ------------------------------------------------------------------
variable "openai_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "ml_app_id" {
  type      = string
  default   = ""
  sensitive = true
}

variable "ml_client_secret" {
  type      = string
  default   = ""
  sensitive = true
}

variable "ml_seller_id" {
  type      = string
  default   = ""
  sensitive = true
}

variable "jwt_secret" {
  description = "Vazio = gerado aleatoriamente."
  type        = string
  default     = ""
  sensitive   = true
}

variable "admin_username" {
  type    = string
  default = "def_admin"
}

variable "admin_password" {
  description = "Vazio = gerado aleatoriamente (veja output admin_password_hint)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "media_token" {
  description = "Vazio = gerado aleatoriamente."
  type        = string
  default     = ""
  sensitive   = true
}

variable "extra_env" {
  description = "Variáveis de ambiente extras (texto puro) para web e jobs. Sobrescrevem as padrão (ex.: ML_REDIRECT_URI, AFFILIATE_URL, MERCADO_LIVRE_AFFILIATE_ID)."
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------------
# CI/CD (GitHub Actions via Workload Identity Federation)
# ------------------------------------------------------------------
variable "github_repository" {
  description = "Repositório GitHub autorizado a assumir a SA de deploy (owner/repo)."
  type        = string
  default     = "SchultzVV/V_M"
}

# ------------------------------------------------------------------
# Orçamento / alertas
# ------------------------------------------------------------------
variable "billing_account" {
  description = "ID da conta de faturamento (XXXXXX-XXXXXX-XXXXXX) para o orçamento mensal. Vazio = sem orçamento."
  type        = string
  default     = ""
}

variable "budget_monthly_usd" {
  description = "Teto mensal em USD para alertas (50 %, 90 %, 100 %)."
  type        = number
  default     = 60
}

variable "alert_email" {
  description = "E-mail para alertas de orçamento e uptime. Vazio = sem canal."
  type        = string
  default     = ""
}
