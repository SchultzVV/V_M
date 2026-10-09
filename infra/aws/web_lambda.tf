# ------------------------------------------------------------------
# Site Flask como Lambda (imagem de container + Lambda Web Adapter).
# Escala a zero, free tier permanente (1 M req + 400 k GB-s/mês).
# Fica na VPC (RDS/EFS) → sai para ML/OpenAI pelo NAT (fck-nat).
# ------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name}-site"
  retention_in_days = var.log_retention_days
}

locals {
  lambda_env = merge(
    local.common_env,
    { for k, v in local.secret_values : upper(k) => v },
    {
      PORT                         = "8080"
      AWS_LWA_PORT                 = "8080"
      AWS_LWA_READINESS_CHECK_PATH = "/webhook/health"
      AWS_LWA_INVOKE_MODE          = "buffered"
      AWS_LWA_ENABLE_COMPRESSION   = "true"
    },
    var.lambda_url_auth_type == "NONE" ? { ORIGIN_VERIFY_TOKEN = random_password.origin_verify.result } : {},
  )
}

resource "aws_lambda_function" "site" {
  function_name = "${local.name}-site"
  description   = "DEF: Flask (API + Jinja) atras do CloudFront"
  role          = aws_iam_role.lambda.arn

  package_type  = "Image"
  image_uri     = local.image_site_lambda
  architectures = [var.lambda_architecture]
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_s

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  file_system_config {
    arn              = aws_efs_access_point.this["config"].arn
    local_mount_path = "/mnt/config"
  }

  environment {
    variables = { for k, v in local.lambda_env : k => v if v != "" }
  }

  logging_config {
    log_format = "JSON"
    log_group  = aws_cloudwatch_log_group.lambda.name
  }

  depends_on = [
    aws_efs_mount_target.this,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_cloudwatch_log_group.lambda,
  ]
}

resource "aws_lambda_function_url" "site" {
  function_name      = aws_lambda_function.site.function_name
  authorization_type = var.lambda_url_auth_type
  invoke_mode        = "BUFFERED"
}

# Só o CloudFront (esta distribuição) pode invocar a URL quando AWS_IAM.
resource "aws_lambda_permission" "cloudfront" {
  count = var.lambda_url_auth_type == "AWS_IAM" ? 1 : 0

  statement_id           = "AllowCloudFrontInvokeUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.site.function_name
  principal              = "cloudfront.amazonaws.com"
  source_arn             = aws_cloudfront_distribution.this.arn
  function_url_auth_type = "AWS_IAM"
}

resource "aws_lambda_permission" "public_url" {
  count = var.lambda_url_auth_type == "NONE" ? 1 : 0

  statement_id           = "AllowPublicInvokeUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.site.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

locals {
  lambda_origin_domain = trimsuffix(trimprefix(aws_lambda_function_url.site.function_url, "https://"), "/")
}
