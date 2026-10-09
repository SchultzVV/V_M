# OCR (info-scrap) interno ao ambiente: só os jobs chamam; escala a zero quando ocioso.
resource "azurerm_container_app" "ocr" {
  name                         = local.ocr_name
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

  dynamic "secret" {
    for_each = var.ghcr_pat != "" ? ["ghcr-pat"] : []
    content {
      name  = "ghcr-pat"
      value = var.ghcr_pat
    }
  }

  ingress {
    external_enabled           = false # só dentro do ambiente
    target_port                = 8000
    transport                  = "http"
    allow_insecure_connections = true # INFO_SCRAP_URL=http://...
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    http_scale_rule {
      name                = "http"
      concurrent_requests = "10"
    }

    container {
      name   = "ocr"
      image  = var.image_ocr
      cpu    = 0.5
      memory = "1Gi"
    }
  }

  depends_on = [time_sleep.app_rbac]
}
