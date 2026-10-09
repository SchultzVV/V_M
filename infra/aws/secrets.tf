# ------------------------------------------------------------------
# Segredos em SSM Parameter Store (SecureString, sem custo no tier
# standard). O Terraform só cria o parâmetro; o valor é ignorado depois
# da criação para que a rotação seja feita fora do estado:
#   aws ssm put-parameter --name /def/prd/openai_api_key --type SecureString \
#       --value '...' --overwrite
# Vazio no tfvars vira valor gerado (jwt/admin/media) ou "CHANGE_ME".
# ------------------------------------------------------------------
resource "random_password" "jwt_secret" {
  length  = 48
  special = false
}

resource "random_password" "admin_password" {
  length  = 24
  special = false
}

resource "random_password" "media_token" {
  length  = 32
  special = false
}

resource "random_password" "origin_verify" {
  length  = 32
  special = false
}

locals {
  secret_values = {
    openai_api_key   = var.openai_api_key
    ml_app_id        = var.ml_app_id
    ml_client_secret = var.ml_client_secret
    ml_seller_id     = var.ml_seller_id
    jwt_secret       = coalesce(var.jwt_secret, random_password.jwt_secret.result)
    admin_username   = var.admin_username
    admin_password   = coalesce(var.admin_password, random_password.admin_password.result)
    media_token      = coalesce(var.media_token, random_password.media_token.result)
    database_url     = local.database_url
    minio_access_key = aws_iam_access_key.media_writer.id
    minio_secret_key = aws_iam_access_key.media_writer.secret
  }

  ssm_prefix = "/${var.project}/${var.environment}"
}

resource "aws_ssm_parameter" "secret" {
  for_each = local.secret_values

  name  = "${local.ssm_prefix}/${each.key}"
  type  = "SecureString"
  value = each.value != "" ? each.value : "CHANGE_ME"

  lifecycle {
    ignore_changes = [value]
  }
}

data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}
