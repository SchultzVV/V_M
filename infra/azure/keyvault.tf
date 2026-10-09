resource "random_string" "kv_suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "random_password" "admin" {
  length  = 24
  special = false
}

resource "random_password" "media" {
  length  = 32
  special = false
}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.prefix}-${random_string.kv_suffix.result}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = var.kv_purge_protection
  tags                       = local.tags
}

# Quem aplica o Terraform administra os segredos
resource "azurerm_role_assignment" "deployer_kv_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# RBAC leva até ~1 min para propagar; evita 403 na criação dos secrets
resource "time_sleep" "kv_rbac" {
  depends_on      = [azurerm_role_assignment.deployer_kv_admin]
  create_duration = "60s"
}

resource "azurerm_key_vault_secret" "s" {
  for_each     = local.kv_secret_names
  name         = each.key
  value        = local.kv_secrets[each.key]
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"
  tags         = local.tags

  depends_on = [time_sleep.kv_rbac]

  # rotação é feita direto no Key Vault (az keyvault secret set); TF não sobrescreve
  lifecycle {
    ignore_changes = [value]
  }
}
