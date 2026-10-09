resource "random_string" "storage_suffix" {
  length  = 6
  upper   = false
  special = false
}

# Blob (imagens públicas), Files (staging/uploads/config montados nos containers), Queue (eventos)
resource "azurerm_storage_account" "main" {
  name                            = "st${local.flat}${random_string.storage_suffix.result}"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = true # container `media` com leitura pública (imagens dos produtos)
  shared_access_key_enabled       = true # SMB (file shares) e connection string do adaptador Blob
  tags                            = local.tags

  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "HEAD"]
      allowed_origins    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
  }
}

resource "azurerm_storage_container" "media" {
  name                  = "media"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "blob"
}

resource "azurerm_storage_share" "shares" {
  for_each           = toset(["staging", "uploads", "config"])
  name               = each.key
  storage_account_id = azurerm_storage_account.main.id
  quota              = 5
  access_tier        = "TransactionOptimized"
}

resource "azurerm_storage_queue" "events" {
  name               = "events"
  storage_account_id = azurerm_storage_account.main.id
}

# Vincula cada file share ao ambiente (montado como volume AzureFile nos apps/jobs)
resource "azurerm_container_app_environment_storage" "shares" {
  for_each                     = azurerm_storage_share.shares
  name                         = each.key
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.main.name
  share_name                   = each.value.name
  access_key                   = azurerm_storage_account.main.primary_access_key
  access_mode                  = "ReadWrite"
}
