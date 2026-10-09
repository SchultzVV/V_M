# ------------------------------------------------------------------
# VPC (só quando precisa: Memorystore ou OCR como serviço interno)
# Cloud Run usa Direct VPC egress (sem conector, sem custo fixo).
# ------------------------------------------------------------------
resource "google_compute_network" "vpc" {
  count = local.need_vpc ? 1 : 0

  name                    = "${local.prefix}-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "run" {
  count = local.need_vpc ? 1 : 0

  name                     = "${local.prefix}-run"
  region                   = var.region
  network                  = google_compute_network.vpc[0].id
  ip_cidr_range            = "10.10.0.0/24"
  private_ip_google_access = true
}

# ------------------------------------------------------------------
# Memorystore for Redis (BASIC, 1 GB) — redis_mode = "memorystore"
# ------------------------------------------------------------------
resource "google_redis_instance" "redis" {
  count = var.redis_mode == "memorystore" ? 1 : 0

  name               = "${local.prefix}-redis"
  region             = var.region
  tier               = "BASIC"
  memory_size_gb     = 1
  redis_version      = "REDIS_7_0"
  authorized_network = google_compute_network.vpc[0].id
  connect_mode       = "DIRECT_PEERING"
  labels             = local.labels

  depends_on = [google_project_service.apis]
}
