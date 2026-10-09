# Padrão: imagens no GHCR (já usado pelo projeto; sem custo). Opcional: ACR Basic.
resource "random_string" "acr_suffix" {
  count   = var.enable_acr ? 1 : 0
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_container_registry" "main" {
  count               = var.enable_acr ? 1 : 0
  name                = "acr${local.flat}${random_string.acr_suffix[0].result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

resource "azurerm_role_assignment" "app_acr_pull" {
  count                = var.enable_acr ? 1 : 0
  scope                = azurerm_container_registry.main[0].id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

locals {
  # Bloco registry usado por web/ocr/jobs
  registries = concat(
    var.enable_acr ? [{
      server               = azurerm_container_registry.main[0].login_server
      username             = null
      password_secret_name = null
      identity             = azurerm_user_assigned_identity.app.id
    }] : [],
    var.ghcr_pat != "" ? [{
      server               = "ghcr.io"
      username             = var.ghcr_username
      password_secret_name = "ghcr-pat"
      identity             = null
    }] : []
  )
}
