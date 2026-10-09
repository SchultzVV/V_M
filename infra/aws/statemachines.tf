# ------------------------------------------------------------------
# Step Functions (Standard; 4 000 transições/mês grátis):
#   run-job : {"job": "<nome>", "args": [...]} → ECS RunTask .sync
#   nightly : update-ml-prices → verify-prices → tag-classify
# ------------------------------------------------------------------
locals {
  sfn_network = {
    AwsvpcConfiguration = {
      Subnets        = local.jobs_subnets
      SecurityGroups = [aws_security_group.jobs.id]
      AssignPublicIp = local.jobs_assign_public_ip
    }
  }

  sfn_retry = [
    {
      ErrorEquals     = ["ECS.AmazonECSException", "ECS.ServerException", "ECS.ThrottlingException"]
      IntervalSeconds = 30
      MaxAttempts     = 3
      BackoffRate     = 2
    },
  ]

  # Parameters do ecs:runTask por job (comando padrão)
  sfn_params_default = {
    for name, job in local.jobs : name => {
      Cluster                  = aws_ecs_cluster.this.arn
      TaskDefinition           = aws_ecs_task_definition.job[name].arn_without_revision
      CapacityProviderStrategy = [{ CapacityProvider = "FARGATE_SPOT", Weight = 1 }]
      NetworkConfiguration     = local.sfn_network
      Overrides                = { ContainerOverrides = [{ Name = "site", Command = job.command }] }
    }
  }

  # Idem, com o comando vindo do input ($.args)
  sfn_params_custom = {
    for name, job in local.jobs : name => merge(local.sfn_params_default[name], {
      Overrides = { ContainerOverrides = [{ Name = "site", "Command.$" = "$.args" }] }
    })
  }

  sfn_run_states = merge(
    { for name, p in local.sfn_params_default : "Run-${name}-default" => {
      Type       = "Task"
      Resource   = "arn:aws:states:::ecs:runTask.sync"
      Parameters = p
      Retry      = local.sfn_retry
      End        = true
    } },
    { for name, p in local.sfn_params_custom : "Run-${name}-custom" => {
      Type       = "Task"
      Resource   = "arn:aws:states:::ecs:runTask.sync"
      Parameters = p
      Retry      = local.sfn_retry
      End        = true
    } },
  )
}

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/states/${local.name}"
  retention_in_days = var.log_retention_days
}

resource "aws_sfn_state_machine" "run_job" {
  name     = "${local.name}-run-job"
  role_arn = aws_iam_role.sfn.arn
  type     = "STANDARD"

  definition = templatefile("${path.module}/statemachines/run_job.asl.json", {
    job_names  = sort(keys(local.jobs))
    run_states = local.sfn_run_states
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = false
    level                  = "ERROR"
  }

  depends_on = [aws_iam_role_policy.sfn, aws_iam_role_policy.sfn_logs]
}

resource "aws_sfn_state_machine" "nightly" {
  name     = "${local.name}-nightly"
  role_arn = aws_iam_role.sfn.arn
  type     = "STANDARD"

  definition = templatefile("${path.module}/statemachines/nightly.asl.json", {
    params = local.sfn_params_default
    retry  = local.sfn_retry
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = false
    level                  = "ERROR"
  }

  depends_on = [aws_iam_role_policy.sfn, aws_iam_role_policy.sfn_logs]
}

# Logs do Step Functions (CloudWatch Logs delivery exige estas permissões amplas)
data "aws_iam_policy_document" "sfn_logs" {
  statement {
    actions = [
      "logs:CreateLogDelivery", "logs:GetLogDelivery", "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery", "logs:ListLogDeliveries", "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies", "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn_logs" {
  name   = "logs"
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.sfn_logs.json
}
