data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name       = "${var.project}-${var.environment}"
  account_id = data.aws_caller_identity.current.account_id
  azs        = slice(data.aws_availability_zones.available.names, 0, 2)

  tags = merge({
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)

  public_url = "https://${var.domain}"
  aliases    = var.create_www_alias ? [var.domain, "www.${var.domain}"] : [var.domain]

  image_site        = var.image_site != "" ? var.image_site : "${aws_ecr_repository.site.repository_url}:${var.image_tag}"
  image_site_lambda = var.image_site_lambda != "" ? var.image_site_lambda : "${aws_ecr_repository.site_lambda.repository_url}:${var.image_tag}"

  jobs_subnets          = var.jobs_public_ip ? aws_subnet.public[*].id : aws_subnet.private[*].id
  jobs_assign_public_ip = var.jobs_public_ip ? "ENABLED" : "DISABLED"

  # ------------------------------------------------------------------
  # Jobs = mesmos scripts do Makefile (CLAUDE.md §2.5 / §3), mesma imagem
  # do site, só muda o comando. ocr = true sobe o info-scrap como sidecar.
  # ------------------------------------------------------------------
  jobs = {
    "update-ml-prices" = { command = ["python3", "scripts/update_ml_prices_right.py"], ocr = false }
    "verify-prices"    = { command = ["python3", "scripts/verify_prices.py", "--all"], ocr = true }
    "publish"          = { command = ["python3", "scripts/pipeline_publish.py"], ocr = true }
    "stage"            = { command = ["python3", "scripts/stage_products.py"], ocr = false }
    "prepare-ml"       = { command = ["python3", "scripts/prepare_ml_best.py"], ocr = true }
    "populate-mf"      = { command = ["python3", "agents/ml_populator_agent.py"], ocr = true }
    "reprice-all"      = { command = ["python3", "agents/reprice_all.py"], ocr = false }
    "tag-classify"     = { command = ["python3", "agents/tag_classifier_agent.py", "--db"], ocr = false }
    "api-update-ml"    = { command = ["python3", "scripts/api_update_ml.py"], ocr = false }
  }

  # Variáveis de ambiente NÃO sensíveis, iguais para web e jobs.
  common_env = merge(
    {
      FLASK_ENV             = "production"
      DEBUG                 = "false"
      LOG_LEVEL             = "INFO"
      PUBLIC_BASE_URL       = local.public_url
      CORS_ORIGINS          = join(",", [for h in local.aliases : "https://${h}"])
      ML_REDIRECT_URI       = "${local.public_url}/auth/mercadolivre/callback"
      OPENAI_MODEL          = "gpt-4o-mini"
      LLM_PROVIDER          = var.enable_llm ? "bedrock" : "openai"
      MINIO_ENDPOINT        = "s3.${var.region}.amazonaws.com"
      MINIO_SECURE          = "true"
      MINIO_REGION          = var.region
      MINIO_BUCKET          = aws_s3_bucket.media.bucket
      MINIO_PUBLIC_ENDPOINT = "${local.public_url}/media"
      EVENTS_QUEUE_URL      = aws_sqs_queue.events.url
    },
    var.redis_mode == "serverless" ? { REDIS_URL = local.redis_url } : {},
  )
}
