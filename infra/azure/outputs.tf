output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "web_default_fqdn" {
  description = "URL padrão do site (alvo do CNAME do domínio próprio)."
  value       = azurerm_container_app.web.ingress[0].fqdn
}

output "site_url" {
  value = local.site_url
}

output "custom_domain_dns_records" {
  description = "Registros DNS necessários ANTES de aplicar com enable_custom_domain=true."
  value = var.domain == "" ? null : {
    txt_name    = "asuid.${var.domain}"
    txt_value   = azurerm_container_app.web.custom_domain_verification_id
    cname_name  = var.domain
    cname_value = azurerm_container_app.web.ingress[0].fqdn
  }
}

output "ocr_internal_url" {
  value = "http://${azurerm_container_app.ocr.ingress[0].fqdn}"
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "postgres_admin_login" {
  value = azurerm_postgresql_flexible_server.main.administrator_login
}

output "storage_account" {
  value = azurerm_storage_account.main.name
}

output "media_public_base_url" {
  value = "${local.blob_endpoint}/${azurerm_storage_container.media.name}"
}

output "events_queue" {
  value = azurerm_storage_queue.events.name
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "identity_client_id" {
  value = azurerm_user_assigned_identity.app.client_id
}

output "job_names" {
  value = merge(local.job_names, { "api-update-ml" = azurerm_container_app_job.events.name })
}

output "acr_login_server" {
  value = var.enable_acr ? azurerm_container_registry.main[0].login_server : null
}

output "azure_openai_endpoint" {
  value = var.enable_llm ? azurerm_cognitive_account.openai[0].endpoint : null
}

output "github_oidc" {
  description = "Secrets a cadastrar no repositório GitHub."
  value = {
    AZURE_CLIENT_ID       = azuread_application.github.client_id
    AZURE_TENANT_ID       = data.azurerm_client_config.current.tenant_id
    AZURE_SUBSCRIPTION_ID = data.azurerm_client_config.current.subscription_id
  }
}

output "handy_commands" {
  value = <<-EOT
    # preparar um produto ML (args sobrescrevem os do job)
    az containerapp job start -g ${azurerm_resource_group.main.name} -n ${local.job_names["prepare-ml"]} --args "scripts/prepare_ml_best.py" "https://meli.la/xxxx"
    # publicar o staging no site
    az containerapp job start -g ${azurerm_resource_group.main.name} -n ${local.job_names["stage"]}
    # disparar o job por evento (atualiza 1 produto ML)
    az storage message put --account-name ${azurerm_storage_account.main.name} --auth-mode login --queue-name ${azurerm_storage_queue.events.name} --content '{"args":["scripts/api_update_ml.py","https://meli.la/xxxx"]}'
    # execuções e logs
    az containerapp job execution list -g ${azurerm_resource_group.main.name} -n ${local.job_names["nightly"]} -o table
    az containerapp logs show -g ${azurerm_resource_group.main.name} -n ${local.web_name} --container site --follow
    # senha do admin / segredos
    az keyvault secret show --vault-name ${azurerm_key_vault.main.name} -n admin-password --query value -o tsv
  EOT
}
