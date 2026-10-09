locals {
  prefix = "def-${var.environment}"

  labels = merge({
    app        = "def"
    env        = var.environment
    managed-by = "terraform"
  }, var.labels)

  site_url = "https://${var.domain}"

  # ---- imagens ---------------------------------------------------------
  registry   = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.def.repository_id}"
  image_site = var.image_site != "" ? var.image_site : "${local.registry}/def-site:${var.image_tag}"
  image_web  = var.image_web != "" ? var.image_web : "${local.registry}/def-web:${var.image_tag}"
  image_ocr  = var.image_ocr != "" ? var.image_ocr : "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.ghcr.repository_id}/schultzvv/info_scrap:latest"

  # VPC só é necessária para Memorystore ou para o OCR como serviço interno
  need_vpc = var.redis_mode == "memorystore" || var.ocr_mode == "service"

  cloudsql_conn = google_sql_database_instance.pg.connection_name

  # ---- jobs (mesma imagem do site, só muda o comando) ------------------
  # args = argumentos do `python3`; ocr = precisa do info-scrap (sidecar/serviço)
  jobs = {
    "update-ml-prices" = { args = ["scripts/update_ml_prices_right.py"], ocr = false }
    "verify-prices"    = { args = ["scripts/verify_prices.py", "--all"], ocr = true }
    "publish"          = { args = ["scripts/pipeline_publish.py"], ocr = true }
    "stage"            = { args = ["scripts/stage_products.py"], ocr = false }
    "prepare-ml"       = { args = ["scripts/prepare_ml_best.py"], ocr = true }
    "populate-mf"      = { args = ["agents/ml_populator_agent.py"], ocr = true }
    "reprice-all"      = { args = ["agents/reprice_all.py"], ocr = false }
    "tag-classify"     = { args = ["agents/tag_classifier_agent.py", "--db"], ocr = false }
    "api-update-ml"    = { args = ["scripts/api_update_ml.py"], ocr = false }
  }

  # ---- segredos (nomes = variáveis de ambiente) ------------------------
  secret_names = [
    "DATABASE_URL",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "MEDIA_TOKEN",
    "JWT_SECRET",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD",
    "OPENAI_API_KEY",
    "ML_APP_ID",
    "ML_CLIENT_SECRET",
    "ML_SELLER_ID",
  ]

  db_password  = random_password.db.result
  database_url = "postgresql://${google_sql_user.app.name}:${urlencode(local.db_password)}@/${google_sql_database.produtos.name}?host=/cloudsql/${local.cloudsql_conn}"

  secret_values = {
    DATABASE_URL     = local.database_url
    MINIO_ACCESS_KEY = google_storage_hmac_key.runtime.access_id
    MINIO_SECRET_KEY = google_storage_hmac_key.runtime.secret
    MEDIA_TOKEN      = var.media_token != "" ? var.media_token : random_password.media_token.result
    JWT_SECRET       = var.jwt_secret != "" ? var.jwt_secret : random_password.jwt.result
    ADMIN_USERNAME   = var.admin_username
    ADMIN_PASSWORD   = var.admin_password != "" ? var.admin_password : random_password.admin.result
    OPENAI_API_KEY   = var.openai_api_key
    ML_APP_ID        = var.ml_app_id
    ML_CLIENT_SECRET = var.ml_client_secret
    ML_SELLER_ID     = var.ml_seller_id
  }

  # ---- env em texto puro (web + jobs) ----------------------------------
  redis_url = var.redis_mode == "memorystore" ? "redis://${try(google_redis_instance.redis[0].host, "")}:${try(google_redis_instance.redis[0].port, 6379)}/0" : ""

  site_env = merge(
    {
      PORT                  = "5000"
      FLASK_ENV             = "production"
      DEBUG                 = "false"
      LOG_LEVEL             = "INFO"
      GOOGLE_CLOUD_PROJECT  = var.project_id
      GCP_REGION            = var.region
      PUBLIC_BASE_URL       = local.site_url
      CORS_ORIGINS          = local.site_url
      ML_REDIRECT_URI       = "${local.site_url}/auth/mercadolivre/callback"
      MINIO_ENDPOINT        = "storage.googleapis.com"
      MINIO_SECURE          = "true"
      MINIO_PUBLIC_ENDPOINT = "https://storage.googleapis.com"
      MINIO_BUCKET          = google_storage_bucket.media.name
      OPENAI_MODEL          = "gpt-4o-mini"
      LLM_PROVIDER          = var.enable_llm ? "vertex" : "openai"
      EVENTS_TOPIC          = google_pubsub_topic.events.name
    },
    var.redis_mode == "memorystore" ? { REDIS_URL = local.redis_url } : {},
    var.extra_env,
  )

  ocr_url = var.ocr_mode == "sidecar" ? "http://127.0.0.1:8000" : try(google_cloud_run_v2_service.ocr[0].uri, "")

  job_env = merge(local.site_env, {
    FORCE_CATEGORY = "auto"
    INFO_SCRAP_URL = local.ocr_url
  })

  # volumes do appdata (prefixo → ponto de montagem)
  appdata_mounts = {
    staging = "/app/staging"
    uploads = "/app/uploads"
    config  = "/app/config"
  }
}
