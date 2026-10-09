# ------------------------------------------------------------------
# Serviço web: nginx (React + proxy) como container de ingress e o
# Flask como sidecar em 127.0.0.1:5000 — mesma topologia do compose.
# ------------------------------------------------------------------
resource "google_cloud_run_v2_service" "web" {
  name                = "${local.prefix}-web"
  location            = var.region
  ingress             = var.enable_lb ? "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" : "INGRESS_TRAFFIC_ALL"
  deletion_protection = false
  labels              = local.labels

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "120s"
    max_instance_request_concurrency = 80
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    labels                           = local.labels

    scaling {
      min_instance_count = var.web_min_instances
      max_instance_count = var.web_max_instances
    }

    # ---- nginx + React (ingress) --------------------------------------
    containers {
      name       = "web"
      image      = local.image_web
      depends_on = ["site"]

      ports {
        container_port = 8080
      }

      env {
        name  = "PORT"
        value = "8080"
      }
      env {
        name  = "BACKEND"
        value = "127.0.0.1:5000"
      }
      env {
        name  = "MEDIA_ORIGIN"
        value = "https://storage.googleapis.com"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      startup_probe {
        initial_delay_seconds = 1
        period_seconds        = 2
        timeout_seconds       = 2
        failure_threshold     = 15
        http_get {
          path = "/health"
          port = 8080
        }
      }
    }

    # ---- Flask (sidecar) ----------------------------------------------
    containers {
      name  = "site"
      image = local.image_site

      dynamic "env" {
        for_each = local.site_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = toset(local.secret_names)
        content {
          name = env.value
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.s[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      volume_mounts {
        name       = "config"
        mount_path = "/app/config"
      }

      startup_probe {
        initial_delay_seconds = 3
        period_seconds        = 3
        timeout_seconds       = 3
        failure_threshold     = 20
        tcp_socket {
          port = 5000
        }
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [local.cloudsql_conn]
      }
    }

    # config/ml_tokens.json (escrito pelo callback OAuth do ML, lido pelos jobs)
    volumes {
      name = "config"
      gcs {
        bucket        = google_storage_bucket.appdata.name
        read_only     = false
        mount_options = ["only-dir=config"]
      }
    }

    dynamic "vpc_access" {
      for_each = local.need_vpc ? [1] : []
      content {
        egress = "PRIVATE_RANGES_ONLY"
        network_interfaces {
          network    = google_compute_network.vpc[0].id
          subnetwork = google_compute_subnetwork.run[0].id
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.s,
    google_secret_manager_secret_iam_member.runtime,
    google_project_iam_member.runtime_project,
  ]
}

# site público (o LB é não autenticado; a autenticação é da aplicação)
resource "google_cloud_run_v2_service_iam_member" "web_public" {
  name     = google_cloud_run_v2_service.web.name
  location = google_cloud_run_v2_service.web.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ------------------------------------------------------------------
# OCR como serviço interno (fallback do sidecar) — ocr_mode = "service"
# Alcançado pelos jobs via Direct VPC egress; ingress interno.
# ------------------------------------------------------------------
resource "google_cloud_run_v2_service" "ocr" {
  count = var.ocr_mode == "service" ? 1 : 0

  name                = "${local.prefix}-ocr"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = false
  labels              = local.labels

  template {
    service_account       = google_service_account.runtime.email
    timeout               = "180s"
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      name  = "ocr"
      image = local.image_ocr

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = var.ocr_memory
        }
        cpu_idle = true
      }
    }

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = google_compute_network.vpc[0].id
        subnetwork = google_compute_subnetwork.run[0].id
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "ocr_internal" {
  count = var.ocr_mode == "service" ? 1 : 0

  name     = google_cloud_run_v2_service.ocr[0].name
  location = google_cloud_run_v2_service.ocr[0].location
  role     = "roles/run.invoker"
  member   = "allUsers" # ingress interno: só a VPC alcança
}
