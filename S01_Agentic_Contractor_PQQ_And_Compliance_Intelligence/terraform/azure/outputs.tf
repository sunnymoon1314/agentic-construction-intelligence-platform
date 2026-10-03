output "acr_login_server" {
  description = "The login server for the Azure Container Registry. Use this to tag and push your Docker images."
  value       = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  description = "The admin username for the Azure Container Registry."
  value       = nonsensitive(azurerm_container_registry.acr.admin_username)
}

output "acr_admin_password" {
  description = "The admin password for the Azure Container Registry."
  value       = nonsensitive(azurerm_container_registry.acr.admin_password)
}

output "container_app_url" {
  description = "The public URL of the deployed Enterprise MCP Agent web app."
  value       = "https://${azurerm_container_app.mcp_server.ingress[0].fqdn}"
}

output "azure_openai_endpoint" {
  description = "The endpoint URL for the Azure OpenAI resource."
  value       = azurerm_cognitive_account.openai.endpoint
}
