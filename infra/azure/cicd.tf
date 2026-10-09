# ============================================================
# GitHub Actions → Azure por OIDC (sem segredo de longa duração).
# Secrets no repo: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID (outputs).
# ============================================================
resource "azuread_application" "github" {
  display_name = "gh-${local.prefix}-deploy"
}

resource "azuread_service_principal" "github" {
  client_id = azuread_application.github.client_id
}

resource "azuread_application_federated_identity_credential" "github_main" {
  application_id = azuread_application.github.id
  display_name   = "github-${replace(var.github_repo, "/", "-")}-main"
  description    = "Deploy do DEF a partir do GitHub Actions"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repo}:ref:${var.github_ref}"
}

# Contributor no RG: atualizar imagens de apps/jobs e rodar `terraform apply`
# (role assignments novas exigiriam Owner/User Access Administrator; fazer local).
resource "azurerm_role_assignment" "github_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github.object_id
}

resource "azurerm_role_assignment" "github_acr_push" {
  count                = var.enable_acr ? 1 : 0
  scope                = azurerm_container_registry.main[0].id
  role_definition_name = "AcrPush"
  principal_id         = azuread_service_principal.github.object_id
}
