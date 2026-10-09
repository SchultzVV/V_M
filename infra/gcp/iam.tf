# ------------------------------------------------------------------
# SA de runtime (Cloud Run service + jobs)
# ------------------------------------------------------------------
resource "google_service_account" "runtime" {
  account_id   = "${local.prefix}-run"
  display_name = "DEF runtime (Cloud Run web + jobs)"

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "runtime_project" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# buckets: objectAdmin (put/get/delete) + legacyBucketReader (HEAD bucket /
# list, exigido pelo bucket_exists() do cliente MinIO)
resource "google_storage_bucket_iam_member" "runtime_buckets" {
  for_each = {
    media_admin    = { bucket = google_storage_bucket.media.name, role = "roles/storage.objectAdmin" }
    media_reader   = { bucket = google_storage_bucket.media.name, role = "roles/storage.legacyBucketReader" }
    appdata_admin  = { bucket = google_storage_bucket.appdata.name, role = "roles/storage.objectAdmin" }
    appdata_reader = { bucket = google_storage_bucket.appdata.name, role = "roles/storage.legacyBucketReader" }
  }

  bucket = each.value.bucket
  role   = each.value.role
  member = "serviceAccount:${google_service_account.runtime.email}"
}

# ------------------------------------------------------------------
# SA de disparo (Scheduler, Workflows, Eventarc) — executa jobs
# ------------------------------------------------------------------
resource "google_service_account" "trigger" {
  account_id   = "${local.prefix}-trigger"
  display_name = "DEF trigger (Scheduler/Workflows/Eventarc)"

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "trigger_project" {
  for_each = toset([
    "roles/run.invoker",       # run.jobs.run + run.jobs.runWithOverrides
    "roles/workflows.invoker", # Scheduler → Workflows, Eventarc → Workflows
    "roles/eventarc.eventReceiver",
    "roles/logging.logWriter", # sys.log nos workflows
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.trigger.email}"
}

# Eventarc com transporte Pub/Sub precisa que o agente do Pub/Sub crie tokens
resource "google_project_iam_member" "pubsub_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"

  depends_on = [google_project_service.apis]
}
