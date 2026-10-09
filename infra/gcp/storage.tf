# ------------------------------------------------------------------
# Imagens dos produtos (público, lido pelo nginx em /media/<bucket>/...)
# Substitui o MinIO: o app continua usando o cliente MinIO (API S3/XML do
# GCS) com chave HMAC da SA de runtime.
# ------------------------------------------------------------------
resource "google_storage_bucket" "media" {
  name                        = "${local.prefix}-media"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "inherited"
  force_destroy               = !var.deletion_protection
  labels                      = local.labels

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["Content-Type", "Cache-Control"]
    max_age_seconds = 3600
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "media_public" {
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# ------------------------------------------------------------------
# Dados de trabalho (privado): staging/, uploads/, config/ml_tokens.json.
# Montado nos containers via volume GCS (gcsfuse) com only-dir=<prefixo>.
# ------------------------------------------------------------------
resource "google_storage_bucket" "appdata" {
  name                        = "${local.prefix}-appdata"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = !var.deletion_protection
  labels                      = local.labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

# "pastas" iniciais para os only-dir dos volumes
resource "google_storage_bucket_object" "appdata_dirs" {
  for_each = local.appdata_mounts

  name    = "${each.key}/.keep"
  bucket  = google_storage_bucket.appdata.name
  content = "keep"
}

# Chave HMAC (API S3) para o cliente MinIO do app
resource "google_storage_hmac_key" "runtime" {
  service_account_email = google_service_account.runtime.email
}
