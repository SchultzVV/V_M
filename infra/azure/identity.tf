# Identidade única usada pelo site, OCR e jobs: lê segredos do KV, grava blobs, consome a fila
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${local.prefix}-app"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_role_assignment" "app_kv_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "app_blob_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "app_queue_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "app_openai_user" {
  count                = var.enable_llm ? 1 : 0
  scope                = azurerm_cognitive_account.openai[0].id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

# Os apps validam o acesso ao KV na criação → esperar a propagação do RBAC
resource "time_sleep" "app_rbac" {
  depends_on = [
    azurerm_role_assignment.app_kv_secrets_user,
    azurerm_role_assignment.app_blob_contributor,
    azurerm_role_assignment.app_queue_contributor,
  ]
  create_duration = "90s"
}
