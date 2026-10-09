# ------------------------------------------------------------------
# Usuário só para o cliente MinIO (S3-compatível) do site/jobs.
# Alternativa sem chave estática: trocar minio-py por boto3 e usar a
# role do Lambda/task (Δ código).
# ------------------------------------------------------------------
resource "aws_iam_user" "media_writer" {
  name = "${local.name}-media-writer"
}

resource "aws_iam_access_key" "media_writer" {
  user = aws_iam_user.media_writer.name
}

data "aws_iam_policy_document" "media_rw" {
  statement {
    sid       = "Bucket"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.media.arn]
  }

  statement {
    sid       = "Objects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload"]
    resources = ["${aws_s3_bucket.media.arn}/*"]
  }
}

resource "aws_iam_user_policy" "media_writer" {
  name   = "media-rw"
  user   = aws_iam_user.media_writer.name
  policy = data.aws_iam_policy_document.media_rw.json
}

# ------------------------------------------------------------------
# Políticas compartilhadas
# ------------------------------------------------------------------
data "aws_iam_policy_document" "efs_client" {
  statement {
    actions   = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
    resources = [aws_efs_file_system.this.arn]
  }
}

data "aws_iam_policy_document" "sqs_send" {
  statement {
    actions   = ["sqs:SendMessage", "sqs:GetQueueUrl"]
    resources = [aws_sqs_queue.events.arn]
  }
}

# ------------------------------------------------------------------
# Lambda (site)
# ------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name}-site-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_efs" {
  name   = "efs-client"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.efs_client.json
}

resource "aws_iam_role_policy" "lambda_sqs" {
  name   = "sqs-send"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.sqs_send.json
}

resource "aws_iam_role_policy" "lambda_media" {
  name   = "media-rw"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.media_rw.json
}

# ------------------------------------------------------------------
# ECS: execution role (puxar imagem, logs, segredos) e task role (app)
# ------------------------------------------------------------------
data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ecs_execution_secrets" {
  statement {
    sid       = "SsmParams"
    actions   = ["ssm:GetParameters", "ssm:GetParameter"]
    resources = [for p in aws_ssm_parameter.secret : p.arn]
  }

  statement {
    sid       = "KmsSsm"
    actions   = ["kms:Decrypt"]
    resources = [data.aws_kms_alias.ssm.target_key_arn]
  }

  dynamic "statement" {
    for_each = var.ghcr_pat != "" ? [1] : []

    content {
      sid       = "GhcrCredential"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [aws_secretsmanager_secret.ghcr[0].arn]
    }
  }
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name   = "secrets"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.ecs_execution_secrets.json
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

resource "aws_iam_role_policy" "ecs_task_media" {
  name   = "media-rw"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.media_rw.json
}

resource "aws_iam_role_policy" "ecs_task_efs" {
  name   = "efs-client"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.efs_client.json
}

resource "aws_iam_role_policy" "ecs_task_sqs" {
  name   = "sqs-send"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.sqs_send.json
}

# ------------------------------------------------------------------
# EventBridge Scheduler → ECS RunTask / Step Functions
# ------------------------------------------------------------------
data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

data "aws_iam_policy_document" "run_tasks" {
  statement {
    sid     = "RunTask"
    actions = ["ecs:RunTask"]
    resources = [
      "arn:aws:ecs:${var.region}:${local.account_id}:task-definition/${local.name}-*",
      "arn:aws:ecs:${var.region}:${local.account_id}:task-definition/${local.name}-*:*",
    ]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.this.arn]
    }
  }

  statement {
    sid       = "PassRoles"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.ecs_execution.arn, aws_iam_role.ecs_task.arn]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "scheduler" {
  source_policy_documents = [data.aws_iam_policy_document.run_tasks.json]

  statement {
    sid       = "StartStateMachines"
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.nightly.arn, aws_sfn_state_machine.run_job.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "targets"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

# ------------------------------------------------------------------
# Step Functions (ecs:runTask.sync precisa gerir regra no EventBridge)
# ------------------------------------------------------------------
data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "${local.name}-sfn"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

data "aws_iam_policy_document" "sfn" {
  source_policy_documents = [data.aws_iam_policy_document.run_tasks.json]

  statement {
    sid       = "TrackTasks"
    actions   = ["ecs:StopTask", "ecs:DescribeTasks"]
    resources = ["*"]
  }

  statement {
    sid       = "SyncRule"
    actions   = ["events:PutTargets", "events:PutRule", "events:DescribeRule"]
    resources = ["arn:aws:events:${var.region}:${local.account_id}:rule/StepFunctionsGetEventsForECSTaskRule"]
  }
}

resource "aws_iam_role_policy" "sfn" {
  name   = "ecs-run-task"
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.sfn.json
}

# ------------------------------------------------------------------
# EventBridge Pipes: SQS → Step Functions
# ------------------------------------------------------------------
data "aws_iam_policy_document" "pipes_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["pipes.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "pipes" {
  name               = "${local.name}-pipes"
  assume_role_policy = data.aws_iam_policy_document.pipes_assume.json
}

data "aws_iam_policy_document" "pipes" {
  statement {
    sid       = "Source"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.events.arn]
  }

  statement {
    sid       = "Target"
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.run_job.arn]
  }
}

resource "aws_iam_role_policy" "pipes" {
  name   = "sqs-to-sfn"
  role   = aws_iam_role.pipes.id
  policy = data.aws_iam_policy_document.pipes.json
}
