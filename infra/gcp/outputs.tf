output "web_url_run" {
  description = "URL direta do Cloud Run (*.run.app). Com enable_lb=true o ingress é só pelo LB."
  value       = google_cloud_run_v2_service.web.uri
}

output "lb_ip" {
  description = "IP global do LB: crie um registro A (DNS only) para o domínio no Cloudflare."
  value       = try(google_compute_global_address.lb[0].address, null)
}

output "site_url" {
  value = local.site_url
}

output "cloudsql_connection_name" {
  value = local.cloudsql_conn
}

output "buckets" {
  value = {
    media   = google_storage_bucket.media.name
    appdata = google_storage_bucket.appdata.name
  }
}

output "registry" {
  description = "Prefixo do Artifact Registry para as imagens def-site e def-web."
  value       = local.registry
}

output "images" {
  value = {
    site = local.image_site
    web  = local.image_web
    ocr  = local.image_ocr
  }
}

output "jobs" {
  value = [for k, j in google_cloud_run_v2_job.job : j.name]
}

output "pubsub_topic" {
  value = google_pubsub_topic.events.name
}

output "workflows" {
  value = {
    run_job = google_workflows_workflow.run_job.name
    nightly = google_workflows_workflow.nightly.name
  }
}

output "service_accounts" {
  value = {
    runtime = google_service_account.runtime.email
    trigger = google_service_account.trigger.email
    deploy  = google_service_account.deploy.email
  }
}

output "wif_provider" {
  description = "Use em google-github-actions/auth (workload_identity_provider)."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "admin_password_hint" {
  description = "Como ler a senha admin gerada."
  value       = "gcloud secrets versions access latest --secret=${google_secret_manager_secret.s["ADMIN_PASSWORD"].secret_id}"
}

output "handy_commands" {
  value = <<-EOT
    # preparar um produto ML
    gcloud run jobs execute ${google_cloud_run_v2_job.job["prepare-ml"].name} --region ${var.region} --args=scripts/prepare_ml_best.py,https://meli.la/xxxx --wait
    # publicar o staging no site
    gcloud run jobs execute ${google_cloud_run_v2_job.job["stage"].name} --region ${var.region} --wait
    # disparar por evento (mesmo caminho do webhook)
    gcloud pubsub topics publish ${google_pubsub_topic.events.name} --message='{"job":"api-update-ml","args":["scripts/api_update_ml.py","https://meli.la/xxxx"]}'
    # cadeia noturna agora
    gcloud workflows run ${google_workflows_workflow.nightly.name} --location ${var.region}
    # logs do site
    gcloud run services logs read ${google_cloud_run_v2_service.web.name} --region ${var.region} --limit 100
  EOT
}
