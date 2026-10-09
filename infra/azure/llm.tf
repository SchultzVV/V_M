# LLM gerenciado (opcional): Azure OpenAI gpt-4o-mini no lugar de Ollama/hsmart.
# Vetores: pgvector no Flexible Server (azure.extensions=VECTOR) no lugar do Qdrant.
resource "random_string" "oai_suffix" {
  count   = var.enable_llm ? 1 : 0
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_cognitive_account" "openai" {
  count                 = var.enable_llm ? 1 : 0
  name                  = "oai-${local.prefix}"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-${local.prefix}-${random_string.oai_suffix[0].result}"
  tags                  = local.tags
}

resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  count                = var.enable_llm ? 1 : 0
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai[0].id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = var.openai_model_version
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.openai_capacity_k_tpm
  }
}
