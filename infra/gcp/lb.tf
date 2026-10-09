# ------------------------------------------------------------------
# Global External Application Load Balancer → serverless NEG (Cloud Run)
# + Cloud CDN + certificado gerenciado + redirecionamento HTTP→HTTPS.
# Custo fixo ≈ US$ 18/mês (regra de encaminhamento). Alternativa US$ 0:
# enable_lb=false + Firebase Hosting com rewrite para o Cloud Run (README).
# ------------------------------------------------------------------
resource "google_compute_global_address" "lb" {
  count = var.enable_lb ? 1 : 0

  name       = "${local.prefix}-lb-ip"
  ip_version = "IPV4"

  depends_on = [google_project_service.apis]
}

resource "google_compute_region_network_endpoint_group" "web" {
  count = var.enable_lb ? 1 : 0

  name                  = "${local.prefix}-web-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.web.name
  }
}

resource "google_compute_backend_service" "web" {
  count = var.enable_lb ? 1 : 0

  name                  = "${local.prefix}-web-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"
  enable_cdn            = true

  backend {
    group = google_compute_region_network_endpoint_group.web[0].id
  }

  cdn_policy {
    cache_mode = "CACHE_ALL_STATIC"
    cache_key_policy {
      include_host         = true
      include_protocol     = true
      include_query_string = true
    }
    default_ttl       = 3600
    client_ttl        = 3600
    max_ttl           = 86400
    negative_caching  = true
    serve_while_stale = 86400
  }

  log_config {
    enable      = true
    sample_rate = 0.1
  }
}

resource "google_compute_managed_ssl_certificate" "web" {
  count = var.enable_lb ? 1 : 0

  name = "${local.prefix}-cert"

  managed {
    domains = concat([var.domain], var.extra_domains)
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_url_map" "https" {
  count = var.enable_lb ? 1 : 0

  name            = "${local.prefix}-https"
  default_service = google_compute_backend_service.web[0].id
}

resource "google_compute_target_https_proxy" "web" {
  count = var.enable_lb ? 1 : 0

  name             = "${local.prefix}-https-proxy"
  url_map          = google_compute_url_map.https[0].id
  ssl_certificates = [google_compute_managed_ssl_certificate.web[0].id]
}

resource "google_compute_global_forwarding_rule" "https" {
  count = var.enable_lb ? 1 : 0

  name                  = "${local.prefix}-https"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_protocol           = "TCP"
  port_range            = "443"
  target                = google_compute_target_https_proxy.web[0].id
  ip_address            = google_compute_global_address.lb[0].id
  labels                = local.labels
}

# HTTP → HTTPS
resource "google_compute_url_map" "http_redirect" {
  count = var.enable_lb ? 1 : 0

  name = "${local.prefix}-http-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "redirect" {
  count = var.enable_lb ? 1 : 0

  name    = "${local.prefix}-http-proxy"
  url_map = google_compute_url_map.http_redirect[0].id
}

resource "google_compute_global_forwarding_rule" "http" {
  count = var.enable_lb ? 1 : 0

  name                  = "${local.prefix}-http"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_protocol           = "TCP"
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect[0].id
  ip_address            = google_compute_global_address.lb[0].id
  labels                = local.labels
}
