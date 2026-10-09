# ------------------------------------------------------------------
# Cloud Scheduler → Cloud Run Jobs (cron, fuso America/Sao_Paulo)
# Chama a API run.googleapis.com jobs.run com OAuth da SA de disparo,
# opcionalmente sobrescrevendo os args do container "site".
# ------------------------------------------------------------------
resource "google_cloud_scheduler_job" "jobs" {
  for_each = var.schedules

  name             = "${local.prefix}-${each.key}"
  region           = var.region
  description      = "DEF: executa o job ${each.value.job}"
  schedule         = each.value.cron
  time_zone        = "America/Sao_Paulo"
  attempt_deadline = "180s"
  paused           = !each.value.enabled

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.job[each.value.job].name}:run"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode(
      length(each.value.args) > 0
      ? { overrides = { containerOverrides = [{ name = "site", args = each.value.args }] } }
      : {}
    ))

    oauth_token {
      service_account_email = google_service_account.trigger.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [google_project_service.apis, google_project_iam_member.trigger_project]
}

# ------------------------------------------------------------------
# Workflow noturno: update-ml-prices → verify-prices → tag-classify
# ------------------------------------------------------------------
resource "google_workflows_workflow" "nightly" {
  name                = "${local.prefix}-nightly"
  region              = var.region
  description         = "DEF: cadeia noturna de jobs (sequencial, espera cada um)"
  service_account     = google_service_account.trigger.email
  source_contents     = file("${path.module}/workflows/nightly.yaml")
  call_log_level      = "LOG_ERRORS_ONLY"
  deletion_protection = false
  labels              = local.labels

  user_env_vars = {
    REGION       = var.region
    JOB_PREFIX   = local.prefix
    NIGHTLY_JOBS = jsonencode(var.nightly_jobs)
  }

  depends_on = [google_project_service.apis, google_project_iam_member.trigger_project]
}

resource "google_cloud_scheduler_job" "nightly" {
  count = var.nightly_cron != "" ? 1 : 0

  name             = "${local.prefix}-nightly"
  region           = var.region
  description      = "DEF: dispara o workflow noturno"
  schedule         = var.nightly_cron
  time_zone        = "America/Sao_Paulo"
  attempt_deadline = "180s"

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/${google_workflows_workflow.nightly.id}/executions"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({ argument = "{}" }))

    oauth_token {
      service_account_email = google_service_account.trigger.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}

# ------------------------------------------------------------------
# Eventos: Pub/Sub → Eventarc → Workflow run-job → Cloud Run Job
# (ex.: webhook do ML publica {"job":"api-update-ml","args":[...]})
# ------------------------------------------------------------------
resource "google_pubsub_topic" "events" {
  name   = "${local.prefix}-events"
  labels = local.labels

  message_retention_duration = "86400s"

  depends_on = [google_project_service.apis]
}

# Dead-letter: anexe à assinatura criada pelo Eventarc (ver README)
resource "google_pubsub_topic" "events_dlq" {
  name   = "${local.prefix}-events-dlq"
  labels = local.labels

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic_iam_member" "runtime_publisher" {
  topic  = google_pubsub_topic.events.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_workflows_workflow" "run_job" {
  name                = "${local.prefix}-run-job"
  region              = var.region
  description         = "DEF: executa um Cloud Run Job a partir de mensagem Pub/Sub"
  service_account     = google_service_account.trigger.email
  source_contents     = file("${path.module}/workflows/run_job.yaml")
  call_log_level      = "LOG_ERRORS_ONLY"
  deletion_protection = false
  labels              = local.labels

  user_env_vars = {
    REGION       = var.region
    JOB_PREFIX   = local.prefix
    ALLOWED_JOBS = jsonencode(keys(local.jobs))
  }

  depends_on = [google_project_service.apis, google_project_iam_member.trigger_project]
}

resource "google_eventarc_trigger" "events" {
  name            = "${local.prefix}-events"
  location        = var.region
  service_account = google_service_account.trigger.email
  labels          = local.labels

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.pubsub.topic.v1.messagePublished"
  }

  transport {
    pubsub {
      topic = google_pubsub_topic.events.id
    }
  }

  destination {
    workflow = google_workflows_workflow.run_job.id
  }

  depends_on = [
    google_project_service.apis,
    google_project_iam_member.trigger_project,
    google_project_iam_member.pubsub_token_creator,
  ]
}
