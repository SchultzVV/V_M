# ------------------------------------------------------------------
# Identidade
# ------------------------------------------------------------------
variable "project" {
  description = "Prefixo curto do projeto (nome da marca)."
  type        = string
  default     = "def"
}

variable "environment" {
  description = "Ambiente (prd, stg...). Entra em todos os nomes."
  type        = string
  default     = "prd"
}

variable "region" {
  description = "Região principal. sa-east-1 (São Paulo) tem tudo que é usado aqui, mas custa ~30-40% mais; a borda do CloudFront em SP compensa a latência de us-east-1."
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Tags extras aplicadas a todos os recursos."
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------------
# Domínio / CDN
# ------------------------------------------------------------------
variable "domain" {
  description = "Domínio público do site (ex.: def.com.br). Obrigatório: vira alias do CloudFront, ML_REDIRECT_URI e CORS."
  type        = string

  validation {
    condition     = length(var.domain) > 3 && !startswith(var.domain, "http")
    error_message = "Informe só o host (ex.: def.com.br), sem esquema."
  }
}

variable "create_www_alias" {
  description = "Também responder em www.<domain>."
  type        = bool
  default     = true
}

variable "manage_dns_route53" {
  description = "true: cria zona/registros no Route 53. false (padrão): você aponta o CNAME no Cloudflare (DNS only) e cria os registros de validação do ACM à mão."
  type        = bool
  default     = false
}

variable "route53_zone_id" {
  description = "Zona hospedada existente no Route 53 (só com manage_dns_route53 = true)."
  type        = string
  default     = ""
}

variable "cloudfront_price_class" {
  description = "PriceClass_All inclui as bordas da América do Sul; PriceClass_100 (só NA/EU) é mais barato mas serve o Brasil de longe."
  type        = string
  default     = "PriceClass_All"
}

variable "api_cache_ttl" {
  description = "TTL padrão (s) do cache de /api/* no CloudFront. 0 desliga."
  type        = number
  default     = 60
}

# ------------------------------------------------------------------
# Rede
# ------------------------------------------------------------------
variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "nat_mode" {
  description = "Saída para internet das subnets privadas (Lambda precisa para ML/OpenAI): fck-nat (t4g.nano, ~US$ 7/mês), gateway (NAT Gateway, ~US$ 33/mês + dados) ou none."
  type        = string
  default     = "fck-nat"

  validation {
    condition     = contains(["fck-nat", "gateway", "none"], var.nat_mode)
    error_message = "nat_mode deve ser fck-nat, gateway ou none."
  }
}

variable "fck_nat_instance_type" {
  type    = string
  default = "t4g.nano"
}

variable "jobs_public_ip" {
  description = "Jobs ECS rodam em subnets públicas com IP público (sem passar pelo NAT). false: subnets privadas via NAT."
  type        = bool
  default     = true
}

# ------------------------------------------------------------------
# Banco / cache
# ------------------------------------------------------------------
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_engine_version" {
  type    = string
  default = "16"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_max_allocated_storage" {
  description = "Teto do autoscaling de storage (GB). 0 desliga."
  type        = number
  default     = 50
}

variable "deletion_protection" {
  description = "Protege RDS (e impede force_delete no ECR) contra destroy acidental."
  type        = bool
  default     = true
}

variable "redis_mode" {
  description = "none (padrão: REDIS_URL vazio, só /instagram/* e cache do price_validator dependem dele) ou serverless (ElastiCache Serverless Valkey, ~US$ 7/mês)."
  type        = string
  default     = "none"

  validation {
    condition     = contains(["none", "serverless"], var.redis_mode)
    error_message = "redis_mode deve ser none ou serverless."
  }
}

# ------------------------------------------------------------------
# Imagens
# ------------------------------------------------------------------
variable "image_tag" {
  description = "Tag das imagens nos repositórios ECR criados aqui (SHA do commit no CI)."
  type        = string
  default     = "latest"
}

variable "image_site" {
  description = "Imagem completa do site p/ jobs ECS. Vazio = <ECR def-site>:<image_tag>."
  type        = string
  default     = ""
}

variable "image_site_lambda" {
  description = "Imagem completa do site + Lambda Web Adapter. Vazio = <ECR def-site-lambda>:<image_tag>."
  type        = string
  default     = ""
}

variable "image_ocr" {
  description = "Imagem do info-scrap (OCR), sidecar dos jobs que leem preço promo."
  type        = string
  default     = "ghcr.io/schultzvv/info_scrap:latest"
}

variable "ghcr_username" {
  description = "Usuário GitHub para puxar a imagem privada do info-scrap (vazio = imagem pública)."
  type        = string
  default     = ""
}

variable "ghcr_pat" {
  description = "PAT com read:packages para o GHCR (vazio = sem credencial)."
  type        = string
  default     = ""
  sensitive   = true
}

# ------------------------------------------------------------------
# Web (Lambda)
# ------------------------------------------------------------------
variable "lambda_memory_mb" {
  type    = number
  default = 1024
}

variable "lambda_timeout_s" {
  type    = number
  default = 30
}

variable "lambda_architecture" {
  description = "x86_64 ou arm64 (arm64 custa ~20% menos, mas a imagem precisa ser buildada para arm64)."
  type        = string
  default     = "x86_64"

  validation {
    condition     = contains(["x86_64", "arm64"], var.lambda_architecture)
    error_message = "lambda_architecture deve ser x86_64 ou arm64."
  }
}

variable "lambda_url_auth_type" {
  description = "AWS_IAM: Function URL privada, CloudFront assina via OAC (POST/PUT exigem header x-amz-content-sha256 no cliente). NONE: URL pública protegida por header secreto x-origin-verify que o Flask deve conferir."
  type        = string
  default     = "AWS_IAM"

  validation {
    condition     = contains(["AWS_IAM", "NONE"], var.lambda_url_auth_type)
    error_message = "lambda_url_auth_type deve ser AWS_IAM ou NONE."
  }
}

variable "log_retention_days" {
  type    = number
  default = 14
}

# ------------------------------------------------------------------
# Jobs (ECS Fargate Spot)
# ------------------------------------------------------------------
variable "job_cpu" {
  description = "vCPU do task (1024 = 1 vCPU). Playwright + OCR cabem em 1 vCPU / 2 GB."
  type        = number
  default     = 1024
}

variable "job_memory" {
  type    = number
  default = 2048
}

variable "schedules" {
  description = "Agendamentos (EventBridge Scheduler, fuso America/Sao_Paulo, cron de 6 campos). target = job (ECS RunTask direto) ou nightly (Step Functions encadeado)."
  type = map(object({
    target  = string
    job     = optional(string, "")
    cron    = string
    args    = optional(list(string), [])
    enabled = optional(bool, true)
  }))
  default = {
    nightly = {
      target  = "nightly"
      cron    = "cron(0 3 * * ? *)"
      enabled = true
    }
    publish = {
      target  = "job"
      job     = "publish"
      cron    = "cron(0 */6 * * ? *)"
      enabled = false
    }
    populate-mf = {
      target  = "job"
      job     = "populate-mf"
      cron    = "cron(0 5 ? * MON *)"
      args    = ["python3", "agents/ml_populator_agent.py", "--limit", "5"]
      enabled = false
    }
    reprice-all = {
      target  = "job"
      job     = "reprice-all"
      cron    = "cron(0 4 ? * SUN *)"
      enabled = false
    }
  }
}

# ------------------------------------------------------------------
# LLM gerenciado (substitui Ollama/hsmart/Qdrant)
# ------------------------------------------------------------------
variable "enable_llm" {
  description = "Libera bedrock:InvokeModel para o site e os jobs (tag classifier / price oracle via Bedrock, vetores em pgvector no RDS)."
  type        = bool
  default     = false
}

variable "bedrock_model_ids" {
  description = "IDs de modelo Bedrock liberados (qualquer modelo habilitado na conta)."
  type        = list(string)
  default     = ["amazon.nova-lite-v1:0", "amazon.titan-embed-text-v2:0"]
}

# ------------------------------------------------------------------
# Segredos (vazio = gerado/CHANGE_ME; rotacione com `aws ssm put-parameter --overwrite`)
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
  type      = string
  default   = ""
  sensitive = true
}

variable "admin_username" {
  type    = string
  default = "admin"
}

variable "admin_password" {
  type      = string
  default   = ""
  sensitive = true
}

variable "media_token" {
  type      = string
  default   = ""
  sensitive = true
}

# ------------------------------------------------------------------
# CI/CD (GitHub Actions via OIDC)
# ------------------------------------------------------------------
variable "github_repo" {
  type    = string
  default = "SchultzVV/V_M"
}

variable "github_branches" {
  description = "Branches autorizadas a assumir a role de deploy."
  type        = list(string)
  default     = ["main"]
}

variable "github_oidc_provider_arn" {
  description = "ARN de um provider OIDC do GitHub já existente na conta (vazio = cria)."
  type        = string
  default     = ""
}

# ------------------------------------------------------------------
# Orçamento / alertas
# ------------------------------------------------------------------
variable "budget_monthly_usd" {
  type    = number
  default = 60
}

variable "alert_email" {
  description = "E-mail para orçamento e alarmes (vazio = sem notificação)."
  type        = string
  default     = ""
}
