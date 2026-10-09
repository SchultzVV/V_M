resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "random_password" "admin" {
  length  = 24
  special = false
}

resource "random_password" "media_token" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "s" {
  for_each = toset(local.secret_names)

  secret_id = "${upper(replace(local.prefix, "-", "_"))}_${each.key}"
  labels    = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "s" {
  for_each = toset(local.secret_names)

  secret      = google_secret_manager_secret.s[each.key].id
  secret_data = local.secret_values[each.key] != "" ? local.secret_values[each.key] : "CHANGE_ME"

  lifecycle {
    # rotacione com: gcloud secrets versions add <nome> --data-file=-
    ignore_changes = [secret_data]
  }
}

# acesso de leitura da SA de runtime a cada segredo (least privilege)
resource "google_secret_manager_secret_iam_member" "runtime" {
  for_each = toset(local.secret_names)

  secret_id = google_secret_manager_secret.s[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

# ---- credencial do ghcr.io para o repositório remoto (opcional) ----------
resource "google_secret_manager_secret" "ghcr" {
  count = var.ghcr_token != "" ? 1 : 0

  secret_id = "${upper(replace(local.prefix, "-", "_"))}_GHCR_TOKEN"
  labels    = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "ghcr" {
  count = var.ghcr_token != "" ? 1 : 0

  secret      = google_secret_manager_secret.ghcr[0].id
  secret_data = var.ghcr_token

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret_iam_member" "ghcr_ar_agent" {
  count = var.ghcr_token != "" ? 1 : 0

  secret_id = google_secret_manager_secret.ghcr[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-artifactregistry.iam.gserviceaccount.com"
}
