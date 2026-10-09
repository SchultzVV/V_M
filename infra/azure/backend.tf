# ============================================================
# Estado remoto no Storage Account criado por ./bootstrap.
# Configuração parcial: os valores vêm de backend.hcl
#   terraform init -backend-config=backend.hcl
# backend.hcl (copie de backend.hcl.example):
#   resource_group_name  = "rg-def-tfstate"
#   storage_account_name = "<saída storage_account_name do bootstrap>"
#   container_name       = "tfstate"
#   key                  = "def-prd.tfstate"
#   use_azuread_auth     = true   # precisa de "Storage Blob Data Contributor" no container
# Para validar/planejar sem backend: terraform init -backend=false
# ============================================================
terraform {
  backend "azurerm" {}
}
