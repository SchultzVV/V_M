# ------------------------------------------------------------------
# Jobs = tasks ECS Fargate Spot (sem serviço, sem instância ociosa).
# Mesma imagem do site; comando por job; info-scrap como sidecar nos
# jobs que fazem OCR (INFO_SCRAP_URL=http://127.0.0.1:8000).
# ------------------------------------------------------------------
resource "aws_ecs_cluster" "this" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
    base              = 0
  }
}

resource "aws_cloudwatch_log_group" "jobs" {
  name              = "/ecs/${local.name}"
  retention_in_days = var.log_retention_days
}

locals {
  jobs_env = merge(local.common_env, {
    INFO_SCRAP_URL = "http://127.0.0.1:8000"
    FORCE_CATEGORY = "auto"
    PORT           = "5000"
  })

  jobs_env_list = [for k, v in local.jobs_env : { name = k, value = v } if v != ""]

  jobs_secrets_list = [
    for k, p in aws_ssm_parameter.secret : { name = upper(k), valueFrom = p.arn }
  ]

  efs_mounts = [
    for ap in ["staging", "uploads", "config"] : {
      sourceVolume  = ap
      containerPath = "/app/${ap}"
      readOnly      = false
    }
  ]

  ocr_container = merge(
    {
      name      = "ocr"
      image     = var.image_ocr
      essential = false
      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.jobs.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "ocr"
        }
      }
    },
    var.ghcr_pat != "" ? { repositoryCredentials = { credentialsParameter = aws_secretsmanager_secret.ghcr[0].arn } } : {},
  )
}

resource "aws_ecs_task_definition" "job" {
  for_each = local.jobs

  family                   = "${local.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.job_cpu
  memory                   = var.job_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode(concat(
    [
      merge(
        {
          name        = "site"
          image       = local.image_site
          essential   = true
          command     = each.value.command
          environment = local.jobs_env_list
          secrets     = local.jobs_secrets_list
          mountPoints = local.efs_mounts
          logConfiguration = {
            logDriver = "awslogs"
            options = {
              awslogs-group         = aws_cloudwatch_log_group.jobs.name
              awslogs-region        = var.region
              awslogs-stream-prefix = each.key
            }
          }
        },
        each.value.ocr ? { dependsOn = [{ containerName = "ocr", condition = "START" }] } : {},
      )
    ],
    each.value.ocr ? [local.ocr_container] : [],
  ))

  dynamic "volume" {
    for_each = toset(["staging", "uploads", "config"])

    content {
      name = volume.value

      efs_volume_configuration {
        file_system_id     = aws_efs_file_system.this.id
        transit_encryption = "ENABLED"

        authorization_config {
          access_point_id = aws_efs_access_point.this[volume.value].id
          iam             = "ENABLED"
        }
      }
    }
  }

  tags = { Name = "${local.name}-${each.key}", Job = each.key }
}
