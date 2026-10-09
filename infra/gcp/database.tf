resource "random_password" "db" {
  length  = 32
  special = false
}

resource "google_sql_database_instance" "pg" {
  name                = "${local.prefix}-pg"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = var.deletion_protection

  settings {
    tier              = var.db_tier
    edition           = "ENTERPRISE"
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = var.db_disk_size_gb
    disk_autoresize   = true
    user_labels       = local.labels

    deletion_protection_enabled = var.deletion_protection

    # IP público SEM redes autorizadas: só se conecta pelo conector/volume
    # Cloud SQL (socket /cloudsql/<conn>) com IAM roles/cloudsql.client.
    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "06:00" # 03:00 BRT
      point_in_time_recovery_enabled = false
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7 # domingo
      hour         = 8 # 05:00 BRT
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled = false
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "produtos" {
  name     = "produtos_db"
  instance = google_sql_database_instance.pg.name
}

resource "google_sql_user" "app" {
  name     = "def_app"
  instance = google_sql_database_instance.pg.name
  password = local.db_password
}
