# ------------------------------------------------------------
# Identificação
# ------------------------------------------------------------
variable "subscription_id" {
  description = "ID da subscription Azure (ou exporte ARM_SUBSCRIPTION_ID)."
  type        = string
  default     = null
}

variable "project" {
  description = "Prefixo curto do projeto usado nos nomes."
  type        = string
  default     = "def"
}

variable "environment" {
  description = "Ambiente (prd, stg...). Entra em todos os nomes: rg-def-<env>."
  type        = string
  default     = "prd"
}

variable "location" {
  description = "Região Azure. eastus é a mais barata com tudo que usamos; brazilsouth tem os mesmos serviços (~40% mais caro)."
  type        = string
  default     = "eastus"
}

variable "tags" {
  description = "Tags aplicadas a todos os recursos."
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------
# Domínio / exposição
# ------------------------------------------------------------
variable "domain" {
  description = "Domínio público do site (ex.: www.def.com.br). Use subdomínio (CNAME); apex exige bind manual (README)."
  type        = string
  default     = ""
}

variable "enable_custom_domain" {
  description = "Cria o custom domain com certificado gerenciado (grátis). Exige TXT asuid.<domain> e CNAME já publicados (fluxo em 2 applies, README)."
  type        = bool
  default     = true
}

# ------------------------------------------------------------
# Imagens
# ------------------------------------------------------------
variable "image_site" {
  description = "Repositório (sem tag) da imagem Flask construída com infra/docker/Dockerfile.site."
  type        = string
  default     = "ghcr.io/schultzvv/def-site"
}

variable "image_web" {
  description = "Repositório (sem tag) da imagem Nginx+React construída com infra/docker/Dockerfile.web."
  type        = string
  default     = "ghcr.io/schultzvv/def-web"
}

variable "image_tag" {
  description = "Tag aplicada a image_site e image_web (CI passa o SHA)."
  type        = string
  default     = "latest"
}

variable "image_ocr" {
  description = "Imagem completa do OCR info-scrap."
  type        = string
  default     = "ghcr.io/schultzvv/info_scrap:latest"
}

variable "ghcr_username" {
  description = "Usuário GitHub para pull de imagens privadas no GHCR (vazio = imagens públicas)."
  type        = string
  default     = ""
}

variable "ghcr_pat" {
  description = "PAT com read:packages para pull no GHCR (vazio = sem credencial)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_acr" {
  description = "Cria um Azure Container Registry Basic (~US$ 5/mês) e dá AcrPull à identidade. Aponte image_site/image_web para <acr>.azurecr.io/... ao usar."
  type        = bool
  default     = false
}

# ------------------------------------------------------------
# Web (Container App)
# ------------------------------------------------------------
variable "web_min_replicas" {
  description = "Réplicas mínimas do site (0 = scale-to-zero, cold start ~5-10 s; 1 = sempre quente, cobrado em idle)."
  type        = number
  default     = 0
}

variable "web_max_replicas" {
  type    = number
  default = 3
}

variable "web_concurrent_requests" {
  description = "Requisições simultâneas por réplica antes de escalar."
  type        = number
  default     = 50
}

# ------------------------------------------------------------
# Jobs
# ------------------------------------------------------------
variable "job_cpu" {
  type    = number
  default = 1
}

variable "job_memory" {
  type    = string
  default = "2Gi"
}

variable "job_timeout_seconds" {
  description = "Tempo máximo de uma execução de job."
  type        = number
  default     = 3600
}

variable "job_retry_limit" {
  type    = number
  default = 1
}

variable "schedules" {
  description = <<-EOT
    Agendamentos (cron em UTC; 06:00 UTC = 03:00 BRT). Chave = nome do job em local.jobs.
    Jobs ausentes ou com enabled=false ficam com trigger manual.
  EOT
  type = map(object({
    cron_utc = string
    enabled  = bool
  }))
  default = {
    nightly       = { cron_utc = "0 6 * * *", enabled = true }
    publish       = { cron_utc = "15 */6 * * *", enabled = false }
    "populate-mf" = { cron_utc = "0 7 * * 1", enabled = false }
  }
}

variable "event_job_max_executions" {
  description = "Execuções paralelas máximas do job disparado pela fila events."
  type        = number
  default     = 5
}

# ------------------------------------------------------------
# Banco / cache
# ------------------------------------------------------------
variable "db_sku" {
  description = "SKU do PostgreSQL Flexible Server (B_Standard_B1ms = 1 vCore burstable, ~US$ 13/mês)."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "db_storage_mb" {
  type    = number
  default = 32768
}

variable "db_version" {
  type    = string
  default = "16"
}

variable "db_backup_retention_days" {
  type    = number
  default = 7
}

variable "operator_ip" {
  description = "IP público do operador para liberar o Postgres (migração com pg_dump/psql). Vazio = sem regra."
  type        = string
  default     = ""
}

variable "redis_mode" {
  description = "none = sem Redis (site funciona; agentes Instagram/price oracle ficam sem memória) | managed = Azure Cache for Redis Basic C0 (~US$ 16/mês)."
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "managed"], var.redis_mode)
    error_message = "redis_mode deve ser none ou managed."
  }
}

# ------------------------------------------------------------
# LLM gerenciado (substitui Ollama/hsmart/Qdrant)
# ------------------------------------------------------------
variable "enable_llm" {
  description = "Cria Azure OpenAI (gpt-4o-mini, GlobalStandard). A subscription precisa de acesso ao Azure OpenAI."
  type        = bool
  default     = false
}

variable "openai_model_version" {
  type    = string
  default = "2024-07-18"
}

variable "openai_capacity_k_tpm" {
  description = "Capacidade do deployment em milhares de tokens/min."
  type        = number
  default     = 10
}

# ------------------------------------------------------------
# Segredos (valores iniciais; rotação depois direto no Key Vault)
# ------------------------------------------------------------
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
  description = "Usuário do /auth/admin/login (sem default admin/admin)."
  type        = string
  default     = "operador"
}

variable "admin_password" {
  description = "Vazio = gerado aleatoriamente (leia no Key Vault)."
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

variable "kv_purge_protection" {
  description = "Purge protection do Key Vault (não pode ser desligado depois; deixe false em dev)."
  type        = bool
  default     = false
}

# ------------------------------------------------------------
# CI/CD (GitHub Actions via OIDC)
# ------------------------------------------------------------
variable "github_repo" {
  type    = string
  default = "SchultzVV/V_M"
}

variable "github_ref" {
  description = "Ref autorizada a assumir a identidade (refs/heads/main)."
  type        = string
  default     = "refs/heads/main"
}

# ------------------------------------------------------------
# Monitoramento / custo
# ------------------------------------------------------------
variable "alert_email" {
  description = "E-mail para alertas de orçamento e de erro (vazio = só Owners no orçamento, sem alertas por e-mail)."
  type        = string
  default     = ""
}

variable "budget_monthly_usd" {
  type    = number
  default = 60
}

variable "enable_job_alerts" {
  description = "Um alerta de métrica por job (execuções com state=Failed). ~US$ 0,10/alerta/mês."
  type        = bool
  default     = true
}

variable "log_daily_quota_gb" {
  type    = number
  default = 1
}
