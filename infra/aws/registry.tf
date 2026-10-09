# ------------------------------------------------------------------
# ECR: def-site (jobs ECS) e def-site-lambda (site + Lambda Web Adapter).
# O React vai para S3, não precisa de imagem. O info-scrap continua vindo
# do GHCR (credencial opcional em Secrets Manager).
# ------------------------------------------------------------------
resource "aws_ecr_repository" "site" {
  name                 = "${var.project}-site"
  image_tag_mutability = "MUTABLE"
  force_delete         = !var.deletion_protection

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "site_lambda" {
  name                 = "${var.project}-site-lambda"
  image_tag_mutability = "MUTABLE"
  force_delete         = !var.deletion_protection

  image_scanning_configuration {
    scan_on_push = true
  }
}

locals {
  ecr_keep_last = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "manter as 10 imagens mais recentes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "site" {
  repository = aws_ecr_repository.site.name
  policy     = local.ecr_keep_last
}

resource "aws_ecr_lifecycle_policy" "site_lambda" {
  repository = aws_ecr_repository.site_lambda.name
  policy     = local.ecr_keep_last
}

# Credencial do GHCR para a imagem privada do info-scrap (repositoryCredentials do ECS).
resource "aws_secretsmanager_secret" "ghcr" {
  count = var.ghcr_pat != "" ? 1 : 0

  name                    = "${local.name}/ghcr"
  description             = "Login no ghcr.io para puxar o info-scrap"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "ghcr" {
  count = var.ghcr_pat != "" ? 1 : 0

  secret_id = aws_secretsmanager_secret.ghcr[0].id
  secret_string = jsonencode({
    username = var.ghcr_username
    password = var.ghcr_pat
  })
}
