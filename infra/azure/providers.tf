provider "azurerm" {
  # azurerm >= 4 exige subscription_id (ou ARM_SUBSCRIPTION_ID no ambiente)
  subscription_id = var.subscription_id

  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }
}

# azuread usa a mesma sessão do `az login` (tenant atual)
provider "azuread" {}

data "azurerm_client_config" "current" {}
data "azurerm_subscription" "current" {}
