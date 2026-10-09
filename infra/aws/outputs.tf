output "site_url" {
  value = local.public_url
}

output "cloudfront_domain" {
  description = "Aponte o CNAME de <domain> (e www) para cá no Cloudflare, modo DNS only."
  value       = aws_cloudfront_distribution.this.domain_name
}

output "acm_validation_records" {
  description = "CNAMEs de validação do certificado (crie no Cloudflare se manage_dns_route53 = false)."
  value = [
    for dvo in aws_acm_certificate.this.domain_validation_options : {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  ]
}

output "lambda_function_url" {
  value = aws_lambda_function_url.site.function_url
}

output "rds_endpoint" {
  value = aws_db_instance.this.endpoint
}

output "buckets" {
  value = {
    media    = aws_s3_bucket.media.bucket
    frontend = aws_s3_bucket.frontend.bucket
  }
}

output "efs_id" {
  value = aws_efs_file_system.this.id
}

output "ecr_repositories" {
  value = {
    site        = aws_ecr_repository.site.repository_url
    site_lambda = aws_ecr_repository.site_lambda.repository_url
  }
}

output "ecs_cluster" {
  value = aws_ecs_cluster.this.name
}

output "task_definitions" {
  value = { for k, td in aws_ecs_task_definition.job : k => td.arn_without_revision }
}

output "events_queue_url" {
  value = aws_sqs_queue.events.url
}

output "state_machines" {
  value = {
    run_job = aws_sfn_state_machine.run_job.arn
    nightly = aws_sfn_state_machine.nightly.arn
  }
}

output "scheduler_group" {
  value = aws_scheduler_schedule_group.this.name
}

output "github_deploy_role_arn" {
  value = aws_iam_role.github_deploy.arn
}

output "ssm_parameter_prefix" {
  value = local.ssm_prefix
}

output "handy_commands" {
  description = "Comandos do operador (equivalentes aos targets do Makefile)."
  value = {
    prepare_ml = "aws ecs run-task --cluster ${aws_ecs_cluster.this.name} --task-definition ${aws_ecs_task_definition.job["prepare-ml"].family} --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1 --network-configuration 'awsvpcConfiguration={subnets=[${join(",", local.jobs_subnets)}],securityGroups=[${aws_security_group.jobs.id}],assignPublicIp=${local.jobs_assign_public_ip}}' --overrides '{\"containerOverrides\":[{\"name\":\"site\",\"command\":[\"python3\",\"scripts/prepare_ml_best.py\",\"https://meli.la/xxx\"]}]}'"
    stage      = "aws stepfunctions start-execution --state-machine-arn ${aws_sfn_state_machine.run_job.arn} --input '{\"job\":\"stage\"}'"
    restage    = "aws stepfunctions start-execution --state-machine-arn ${aws_sfn_state_machine.run_job.arn} --input '{\"job\":\"stage\",\"args\":[\"python3\",\"scripts/stage_products.py\",\"--force\"]}'"
    nightly    = "aws stepfunctions start-execution --state-machine-arn ${aws_sfn_state_machine.nightly.arn}"
    event      = "aws sqs send-message --queue-url ${aws_sqs_queue.events.url} --message-body '{\"job\":\"api-update-ml\",\"args\":[\"python3\",\"scripts/api_update_ml.py\",\"https://meli.la/xxx\"]}'"
    logs       = "aws logs tail ${aws_cloudwatch_log_group.jobs.name} --follow"
    set_secret = "aws ssm put-parameter --name ${local.ssm_prefix}/openai_api_key --type SecureString --overwrite --value '...'"
  }
}
