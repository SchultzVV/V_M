# ============================================================
# Site: Nginx+React (ingress :8080) + Flask (sidecar :5000) no mesmo pod,
# espelhando docker-compose.react.yaml. TLS/HTTP2 vem do ingress gerenciado.
# ============================================================
resource "azurerm_container_app" "web" {
  name                         = local.web_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  dynamic "registry" {
    for_each = local.registries
    content {
      server               = registry.value.server
      username             = registry.value.username
      password_secret_name = registry.value.password_secret_name
      identity             = registry.value.identity
    }
  }

  # Segredos: referência ao Key Vault via identidade (rotação sem redeploy)
  dynamic "secret" {
    for_each = local.app_secret_names
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.app.id
      key_vault_secret_id = azurerm_key_vault_secret.s[secret.key].versionless_id
    }
  }

  dynamic "secret" {
    for_each = var.ghcr_pat != "" ? ["ghcr-pat"] : []
    content {
      name  = "ghcr-pat"
      value = var.ghcr_pat
    }
  }

  ingress {
    external_enabled           = true
    target_port                = 8080
    transport                  = "auto"
    allow_insecure_connections = false
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = var.web_min_replicas
    max_replicas = var.web_max_replicas

    http_scale_rule {
      name                = "http"
      concurrent_requests = tostring(var.web_concurrent_requests)
    }

    # --- nginx + React -------------------------------------------------
    container {
      name   = "web"
      image  = local.image_web
      cpu    = 0.25
      memory = "0.5Gi"

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
        value = local.blob_endpoint
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/health"
        initial_delay           = 5
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }
      readiness_probe {
        transport = "HTTP"
        port      = 8080
        path      = "/health"
      }
    }

    # --- Flask (gunicorn) ----------------------------------------------
    container {
      name   = "site"
      image  = local.image_site
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = local.site_env_plain
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.site_env_secret
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      # ml_tokens.json (OAuth do ML) compartilhado com os jobs
      volume_mounts {
        name = "config"
        path = "/app/config"
      }

      startup_probe {
        transport               = "TCP"
        port                    = 5000
        failure_count_threshold = 10
        interval_seconds        = 5
      }
    }

    volume {
      name         = "config"
      storage_name = azurerm_container_app_environment_storage.shares["config"].name
      storage_type = "AzureFile"
    }
  }

  depends_on = [time_sleep.app_rbac]
}

# Domínio próprio com certificado gerenciado (grátis). Pré-requisitos no DNS:
#   TXT  asuid.<domain>  = output custom_domain_verification_id
#   CNAME <domain>       = output web_default_fqdn
# O provider cria o managed certificate (validação CNAME) e faz o bind SNI.
resource "azurerm_container_app_custom_domain" "web" {
  count            = var.enable_custom_domain && var.domain != "" ? 1 : 0
  name             = var.domain
  container_app_id = azurerm_container_app.web.id

  lifecycle {
    # valores alterados pelo Azure após emissão do certificado gerenciado
    ignore_changes = [certificate_binding_type, container_app_environment_certificate_id]
  }
}
