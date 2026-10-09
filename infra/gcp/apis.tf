locals {
  base_apis = [
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "workflows.googleapis.com",
    "workflowexecutions.googleapis.com",
    "eventarc.googleapis.com",
    "pubsub.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "storage.googleapis.com",
  ]

  apis = concat(
    local.base_apis,
    var.redis_mode == "memorystore" ? ["redis.googleapis.com", "vpcaccess.googleapis.com"] : [],
    var.enable_llm ? ["aiplatform.googleapis.com"] : [],
    var.billing_account != "" ? ["billingbudgets.googleapis.com"] : [],
  )
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
