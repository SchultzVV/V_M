# ------------------------------------------------------------------
# Cloud Run Jobs: um por target do Makefile, todos com a imagem def-site.
# O comando é `python3 <args>`; `args` pode ser sobrescrito na execução
# (Scheduler/Workflows/gcloud --args). Jobs com ocr=true recebem o
# info-scrap como sidecar (ocr_mode=sidecar) em 127.0.0.1:8000.
# ------------------------------------------------------------------
resource "google_cloud_run_v2_job" "job" {
  for_each = local.jobs

  name                = "${local.prefix}-${each.key}"
  location            = var.region
  deletion_protection = false
  labels              = merge(local.labels, { job = each.key })

  template {
    task_count  = 1
    parallelism = 1
    labels      = merge(local.labels, { job = each.key })

    template {
      service_account       = google_service_account.runtime.email
      timeout               = "${var.job_timeout_seconds}s"
      max_retries           = 1
      execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

      # ---- container principal (site) ---------------------------------
      containers {
        name       = "site"
        image      = local.image_site
        command    = ["python3"]
        args       = each.value.args
        depends_on = each.value.ocr && var.ocr_mode == "sidecar" ? ["ocr"] : null

        dynamic "env" {
          for_each = local.job_env
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
            cpu    = var.job_cpu
            memory = var.job_memory
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }

        dynamic "volume_mounts" {
          for_each = local.appdata_mounts
          content {
            name       = volume_mounts.key
            mount_path = volume_mounts.value
          }
        }
      }

      # ---- sidecar OCR (info-scrap) -----------------------------------
      dynamic "containers" {
        for_each = each.value.ocr && var.ocr_mode == "sidecar" ? [1] : []
        content {
          name  = "ocr"
          image = local.image_ocr

          resources {
            limits = {
              cpu    = "1"
              memory = var.ocr_memory
            }
          }

          # dependência exige startup probe no container dependido
          startup_probe {
            initial_delay_seconds = 5
            period_seconds        = 5
            timeout_seconds       = 3
            failure_threshold     = 24
            tcp_socket {
              port = 8000
            }
          }
        }
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [local.cloudsql_conn]
        }
      }

      dynamic "volumes" {
        for_each = local.appdata_mounts
        content {
          name = volumes.key
          gcs {
            bucket        = google_storage_bucket.appdata.name
            read_only     = false
            mount_options = ["only-dir=${volumes.key}"]
          }
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
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.s,
    google_secret_manager_secret_iam_member.runtime,
    google_project_iam_member.runtime_project,
    google_storage_bucket_object.appdata_dirs,
  ]
}
