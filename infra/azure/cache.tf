# Redis opcional (redis_mode = "managed"): Basic C0 250 MB, só TLS (6380).
resource "azurerm_redis_cache" "main" {
  count                         = var.redis_mode == "managed" ? 1 : 0
  name                          = "redis-${local.prefix}"
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  capacity                      = 0
  family                        = "C"
  sku_name                      = "Basic"
  non_ssl_port_enabled          = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = true
  tags                          = local.tags
}
