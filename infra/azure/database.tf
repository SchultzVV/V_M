resource "random_password" "db" {
  length  = 32
  special = false
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "psql-${local.prefix}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = var.db_version
  sku_name                      = var.db_sku
  storage_mb                    = var.db_storage_mb
  backup_retention_days         = var.db_backup_retention_days
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = true # egress das Container Apps Consumption é dinâmico; TLS obrigatório
  administrator_login           = "def_app"
  administrator_password        = random_password.db.result
  tags                          = local.tags

  authentication {
    password_auth_enabled         = true
    active_directory_auth_enabled = false
  }

  lifecycle {
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "produtos" {
  name      = "produtos_db"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Libera serviços Azure (0.0.0.0 é a regra especial "Allow Azure services")
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAllAzureServicesAndResourcesWithinAzureIps"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "operator" {
  count            = var.operator_ip != "" ? 1 : 0
  name             = "operator"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = var.operator_ip
  end_ip_address   = var.operator_ip
}

# pgvector liberado (depois: CREATE EXTENSION vector; substitui o Qdrant)
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "VECTOR,PG_TRGM"
}

resource "azurerm_postgresql_flexible_server_configuration" "secure_transport" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "on"
}
