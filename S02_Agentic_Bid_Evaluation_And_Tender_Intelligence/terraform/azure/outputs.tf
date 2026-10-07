output "container_app_fqdn" {
  description = "Public FQDN of the S02 Tender Evaluation Container App"
  value       = azurerm_container_app.tender_engine_app.ingress[0].fqdn
}

output "storage_account_name" {
  description = "ADLS Gen2 storage account name"
  value       = azurerm_storage_account.tender_storage.name
}

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.acr.login_server
}

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.rg.name
}
