# ------------------------------------------------------------------
# Disparo dos jobs:
#   cron   → EventBridge Scheduler (fuso America/Sao_Paulo) → ECS RunTask
#            ou Step Functions "nightly"
#   evento → SQS def-events (webhook ML publica) → EventBridge Pipes
#            → Step Functions "run-job" → ECS RunTask com args da mensagem
# ------------------------------------------------------------------
resource "aws_sqs_queue" "events_dlq" {
  name                      = "${local.name}-events-dlq"
  message_retention_seconds = 1209600 # 14 dias
}

resource "aws_sqs_queue" "events" {
  name                       = "${local.name}-events"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600 # 4 dias

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.events_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_scheduler_schedule_group" "this" {
  name = local.name
}

locals {
  schedules_enabled = { for k, s in var.schedules : k => s if s.enabled }
}

resource "aws_scheduler_schedule" "this" {
  for_each = local.schedules_enabled

  name        = "${local.name}-${each.key}"
  group_name  = aws_scheduler_schedule_group.this.name
  description = "DEF ${each.key}: ${each.value.target == "nightly" ? "Step Functions nightly" : "ECS RunTask ${each.value.job}"}"

  schedule_expression          = each.value.cron
  schedule_expression_timezone = "America/Sao_Paulo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = each.value.target == "nightly" ? aws_sfn_state_machine.nightly.arn : aws_ecs_cluster.this.arn
    role_arn = aws_iam_role.scheduler.arn

    # ECS: o input é o `overrides` do RunTask; Step Functions: input da execução.
    input = each.value.target == "nightly" ? jsonencode({ source = "scheduler", schedule = each.key }) : (
      length(each.value.args) > 0 ? jsonencode({
        containerOverrides = [{ name = "site", command = each.value.args }]
      }) : null
    )

    dynamic "ecs_parameters" {
      for_each = each.value.target == "job" ? [1] : []

      content {
        task_definition_arn = aws_ecs_task_definition.job[each.value.job].arn_without_revision
        task_count          = 1
        platform_version    = "LATEST"

        capacity_provider_strategy {
          capacity_provider = "FARGATE_SPOT"
          weight            = 1
        }

        network_configuration {
          subnets          = local.jobs_subnets
          security_groups  = [aws_security_group.jobs.id]
          assign_public_ip = var.jobs_public_ip
        }
      }
    }

    retry_policy {
      maximum_retry_attempts       = 2
      maximum_event_age_in_seconds = 3600
    }
  }
}

# SQS → Step Functions run-job. O corpo da mensagem é JSON
# {"job":"api-update-ml","args":["python3","scripts/api_update_ml.py","MLB123"]}
# e chega à state machine embrulhado em {"data": <body>} (exigência do
# input transformer para manter JSON válido); a state machine desembrulha.
resource "aws_pipes_pipe" "events" {
  name     = "${local.name}-events"
  role_arn = aws_iam_role.pipes.arn
  source   = aws_sqs_queue.events.arn
  target   = aws_sfn_state_machine.run_job.arn

  source_parameters {
    sqs_queue_parameters {
      batch_size                         = 1
      maximum_batching_window_in_seconds = 0
    }
  }

  target_parameters {
    input_template = "{\"data\": <$.body>}"

    step_function_state_machine_parameters {
      invocation_type = "FIRE_AND_FORGET"
    }
  }

  depends_on = [aws_iam_role_policy.pipes]
}
