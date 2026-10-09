output "acr_login_server" {
  description = "The login server for the Azure Container Registry"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  description = "The admin username for the Azure Container Registry"
  value       = nonsensitive(azurerm_container_registry.acr.admin_username)
}

output "acr_admin_password" {
  description = "The admin password for the Azure Container Registry"
  value       = nonsensitive(azurerm_container_registry.acr.admin_password)
}

output "container_app_url" {
  description = "The public URL of the deployed ACIP S03 Container App"
  value       = "https://${azurerm_container_app.commercial_app.ingress[0].fqdn}"
}

output "container_app_fqdn" {
  description = "The FQDN of the deployed Container App"
  value       = azurerm_container_app.commercial_app.ingress[0].fqdn
}

output "storage_account_name" {
  description = "Storage account hosting Approach 3 Parquet lakehouse"
  value       = azurerm_storage_account.commercial_storage.name
}

output "storage_container_name" {
  description = "Blob container name for Parquet files"
  value       = azurerm_storage_container.lake_container.name
}
