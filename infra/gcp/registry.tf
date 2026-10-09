# Repositório das imagens def-site e def-web
resource "google_artifact_registry_repository" "def" {
  location      = var.region
  repository_id = "def"
  description   = "Imagens do DEF (def-site, def-web)"
  format        = "DOCKER"
  labels        = local.labels

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-untagged-7d"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s"
    }
  }

  depends_on = [google_project_service.apis]
}

# Repositório REMOTO espelhando o ghcr.io (Cloud Run não puxa imagens
# diretamente do GitHub Container Registry). info_scrap privado → ghcr_token.
resource "google_artifact_registry_repository" "ghcr" {
  location      = var.region
  repository_id = "ghcr"
  description   = "Proxy do ghcr.io (info_scrap)"
  format        = "DOCKER"
  mode          = "REMOTE_REPOSITORY"
  labels        = local.labels

  remote_repository_config {
    description = "ghcr.io"

    docker_repository {
      custom_repository {
        uri = "https://ghcr.io"
      }
    }

    dynamic "upstream_credentials" {
      for_each = var.ghcr_token != "" ? [1] : []
      content {
        username_password_credentials {
          username                = var.ghcr_username
          password_secret_version = google_secret_manager_secret_version.ghcr[0].name
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.ghcr_ar_agent,
  ]
}
