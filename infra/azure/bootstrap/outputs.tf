output "backend_hcl" {
  description = "Conteúdo para ../backend.hcl"
  value       = <<-EOT
    resource_group_name  = "${azurerm_resource_group.tfstate.name}"
    storage_account_name = "${azurerm_storage_account.tfstate.name}"
    container_name       = "${azurerm_storage_container.tfstate.name}"
    key                  = "${var.project}-prd.tfstate"
    use_azuread_auth     = true
  EOT
}

output "storage_account_name" {
  value = azurerm_storage_account.tfstate.name
}
