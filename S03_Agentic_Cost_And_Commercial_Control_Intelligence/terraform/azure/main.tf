terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

resource "azurerm_resource_group" "rg" {
  name     = "acip-s03-commercial-rg-${var.environment}"
  location = var.azure_location
}

# 1. Azure Storage Account & Blob Container for Approach 3 Parquet Lakehouse
resource "azurerm_storage_account" "commercial_storage" {
  name                     = "acips03lake${var.environment}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "lake_container" {
  name                  = "commercial-lake"
  storage_account_name  = azurerm_storage_account.commercial_storage.name
  container_access_type = "private"
}

# 2. Azure Container Registry (ACR)
resource "azurerm_container_registry" "acr" {
  name                = "acips03acr${var.environment}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Standard"
  admin_enabled       = true
}

# 3. Azure Container Apps Environment
resource "azurerm_log_analytics_workspace" "logs" {
  name                = "acip-s03-logs-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "env" {
  name                       = "acip-s03-env-${var.environment}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
}

# 4. Azure Container App
resource "azurerm_container_app" "commercial_app" {
  name                         = "acip-s03-commercial-cockpit"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  template {
    container {
      name   = "acip-s03-commercial-cockpit"
      image  = var.docker_image
      cpu    = 0.5
      memory = "1.0Gi"

      env {
        name  = "PORT"
        value = tostring(var.app_port)
      }

      env {
        name  = "CLOUD_PROVIDER"
        value = "AZURE"
      }

      env {
        name  = "COMMERCIAL_LAKE_BUCKET"
        value = "azure://${azurerm_storage_account.commercial_storage.name}.blob.core.windows.net/${azurerm_storage_container.lake_container.name}"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = var.app_port
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
