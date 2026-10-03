# Azure Container Apps Provisioning for Enterprise MCP Server

provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}

# 1. Resource Group
resource "azurerm_resource_group" "mcp_rg" {
  name     = "${var.project_name}-rg"
  location = var.location
}

# 2. Azure Container Registry (ACR)
resource "azurerm_container_registry" "acr" {
  name                = "${var.project_name}acr" # Alphanumeric only
  resource_group_name = azurerm_resource_group.mcp_rg.name
  location            = azurerm_resource_group.mcp_rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

# 3. User Assigned Managed Identity (Least Privilege for Azure OpenAI)
resource "azurerm_user_assigned_identity" "mcp_identity" {
  name                = "${var.project_name}-identity"
  resource_group_name = azurerm_resource_group.mcp_rg.name
  location            = azurerm_resource_group.mcp_rg.location
}

# 4. Azure OpenAI Resource & Deployment
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.project_name}-openai"
  location            = azurerm_resource_group.mcp_rg.location
  resource_group_name = azurerm_resource_group.mcp_rg.name
  kind                = "OpenAI"
  sku_name            = "S0"
}

resource "azurerm_cognitive_deployment" "gpt_model" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }
  sku {
    name     = "GlobalStandard"
    capacity = 10
  }
}

# Note: We scope the role assignment to the specific Cognitive Services account for least privilege!
resource "azurerm_role_assignment" "openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.mcp_identity.principal_id
}

# Note: We also need to give the identity permission to pull from ACR
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.mcp_identity.principal_id
}

# 4. Container Apps Environment
resource "azurerm_container_app_environment" "mcp_env" {
  name                = "${var.project_name}-env"
  location            = azurerm_resource_group.mcp_rg.location
  resource_group_name = azurerm_resource_group.mcp_rg.name
}

# 5. Azure Container App (The Web App)
resource "azurerm_container_app" "mcp_server" {
  name                         = "${var.project_name}-app"
  container_app_environment_id = azurerm_container_app_environment.mcp_env.id
  resource_group_name          = azurerm_resource_group.mcp_rg.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.mcp_identity.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.mcp_identity.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "mcp-server"
      image  = var.docker_image
      cpu    = 0.5
      memory = "1.0Gi"
      env {
        name  = "CLOUD_PROVIDER"
        value = "AZURE"
      }
      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.openai.endpoint
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.mcp_identity.client_id
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].container[0].image
    ]
  }
}
