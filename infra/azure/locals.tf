locals {
  prefix = "${var.project}-${var.environment}" # def-prd
  flat   = "${var.project}${var.environment}"  # defprd (storage/ACR: só alfanumérico)

  tags = merge({
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
    stack       = "infra/azure"
  }, var.tags)

  rg_name   = "rg-${local.prefix}"
  web_name  = "ca-${local.prefix}-web"
  ocr_name  = "ca-${local.prefix}-ocr"
  job_names = { for k, _ in local.jobs : k => "caj-${local.prefix}-${k}" }

  image_site = "${var.image_site}:${var.image_tag}"
  image_web  = "${var.image_web}:${var.image_tag}"

  # FQDN padrão do app (conhecido antes de criar o app: <nome>.<default_domain>)
  web_default_fqdn = "${local.web_name}.${azurerm_container_app_environment.main.default_domain}"
  site_url         = var.domain != "" ? "https://${var.domain}" : "https://${local.web_default_fqdn}"

  blob_endpoint = "https://${azurerm_storage_account.main.name}.blob.core.windows.net"

  # ------------------------------------------------------------
  # Jobs (mesma imagem do site; só muda o comando). ocr=true → recebe INFO_SCRAP_URL.
  # command = entrypoint; args podem ser sobrescritos em `az containerapp job start --args`.
  # ------------------------------------------------------------
  jobs = {
    "update-ml-prices" = { command = ["python3"], args = ["scripts/update_ml_prices_right.py"], ocr = false }
    "verify-prices"    = { command = ["python3"], args = ["scripts/verify_prices.py", "--all"], ocr = true }
    "publish"          = { command = ["python3"], args = ["scripts/pipeline_publish.py"], ocr = true }
    "stage"            = { command = ["python3"], args = ["scripts/stage_products.py"], ocr = false }
    "prepare-ml"       = { command = ["python3"], args = ["scripts/prepare_ml_best.py"], ocr = true }
    "populate-mf"      = { command = ["python3"], args = ["agents/ml_populator_agent.py"], ocr = true }
    "reprice-all"      = { command = ["python3"], args = ["agents/reprice_all.py"], ocr = false } # destrutivo: nunca agendar por padrão
    "tag-classify"     = { command = ["python3"], args = ["agents/tag_classifier_agent.py", "--db"], ocr = false }
    "nightly" = {
      command = ["sh", "-c"]
      args    = ["python3 scripts/update_ml_prices_right.py && python3 scripts/verify_prices.py --all && python3 agents/tag_classifier_agent.py --db"]
      ocr     = true
    }
  }

  scheduled_jobs = { for k, s in var.schedules : k => s if s.enabled && contains(keys(local.jobs), k) }

  # ------------------------------------------------------------
  # Segredos no Key Vault (nome → valor inicial). "CHANGE-ME" = preencher depois no KV.
  # ------------------------------------------------------------
  kv_secrets = merge(
    {
      "openai-api-key"            = coalesce(var.openai_api_key, "CHANGE-ME")
      "ml-app-id"                 = coalesce(var.ml_app_id, "CHANGE-ME")
      "ml-client-secret"          = coalesce(var.ml_client_secret, "CHANGE-ME")
      "ml-seller-id"              = coalesce(var.ml_seller_id, "CHANGE-ME")
      "jwt-secret"                = coalesce(var.jwt_secret, random_password.jwt.result)
      "admin-username"            = var.admin_username
      "admin-password"            = coalesce(var.admin_password, random_password.admin.result)
      "media-token"               = coalesce(var.media_token, random_password.media.result)
      "database-url"              = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}:${urlencode(random_password.db.result)}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.produtos.name}?sslmode=require"
      "storage-connection-string" = azurerm_storage_account.main.primary_connection_string
      "storage-account-key"       = azurerm_storage_account.main.primary_access_key
    },
    var.redis_mode == "managed" ? {
      "redis-url" = "rediss://:${azurerm_redis_cache.main[0].primary_access_key}@${azurerm_redis_cache.main[0].hostname}:${azurerm_redis_cache.main[0].ssl_port}/0"
    } : {},
    var.ghcr_pat != "" ? { "ghcr-pat" = var.ghcr_pat } : {}
  )
  kv_secret_names = toset(keys(local.kv_secrets))

  # Segredos referenciados pelos apps/jobs (nome do secret no app = nome no KV)
  app_secret_names = setsubtract(local.kv_secret_names, toset(["ghcr-pat"]))

  # ------------------------------------------------------------
  # Variáveis de ambiente do Flask (plain) e as que vêm de secret
  # ------------------------------------------------------------
  site_env_plain = merge(
    {
      PORT                  = "5000"
      FLASK_ENV             = "production"
      DEBUG                 = "false"
      LOG_LEVEL             = "INFO"
      PUBLIC_BASE_URL       = local.site_url
      CORS_ORIGINS          = join(",", distinct([local.site_url, "https://${local.web_default_fqdn}"]))
      ML_REDIRECT_URI       = "${local.site_url}/auth/mercadolivre/callback"
      MINIO_ENDPOINT        = "${azurerm_storage_account.main.name}.blob.core.windows.net"
      MINIO_PUBLIC_ENDPOINT = local.blob_endpoint
      MINIO_BUCKET          = azurerm_storage_container.media.name
      MINIO_SECURE          = "true"
      MINIO_ACCESS_KEY      = azurerm_storage_account.main.name # nome da conta (não é segredo)
      AZURE_STORAGE_ACCOUNT = azurerm_storage_account.main.name
      EVENTS_QUEUE          = azurerm_storage_queue.events.name
      AZURE_CLIENT_ID       = azurerm_user_assigned_identity.app.client_id # DefaultAzureCredential → identidade user-assigned
      OPENAI_MODEL          = "gpt-4o-mini"
      LLM_PROVIDER          = var.enable_llm ? "azure-openai" : "openai"
      TZ                    = "America/Sao_Paulo"
    },
    var.enable_llm ? {
      AZURE_OPENAI_ENDPOINT   = azurerm_cognitive_account.openai[0].endpoint
      AZURE_OPENAI_DEPLOYMENT = azurerm_cognitive_deployment.gpt4o_mini[0].name
    } : {}
  )

  site_env_secret = merge(
    {
      DATABASE_URL                    = "database-url"
      AZURE_STORAGE_CONNECTION_STRING = "storage-connection-string"
      MEDIA_TOKEN                     = "media-token"
      JWT_SECRET                      = "jwt-secret"
      ADMIN_USERNAME                  = "admin-username"
      ADMIN_PASSWORD                  = "admin-password"
      OPENAI_API_KEY                  = "openai-api-key"
      ML_APP_ID                       = "ml-app-id"
      ML_CLIENT_SECRET                = "ml-client-secret"
      ML_SELLER_ID                    = "ml-seller-id"
      MINIO_SECRET_KEY                = "storage-account-key"
    },
    var.redis_mode == "managed" ? { REDIS_URL = "redis-url" } : {}
  )

  # Jobs: mesmo ambiente do site + categoria automática; OCR só para quem usa
  job_env_plain = merge(local.site_env_plain, { FORCE_CATEGORY = "auto" })
  job_env_ocr   = merge(local.job_env_plain, { INFO_SCRAP_URL = "http://${azurerm_container_app.ocr.ingress[0].fqdn}" })
}
