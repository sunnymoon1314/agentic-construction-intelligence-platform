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
  features {}
}

# 1. Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "rg-acip-s02-${var.environment}"
  location = var.location
}

# 2. ADLS Gen2 Storage Account (Medallion Lake)
resource "azurerm_storage_account" "tender_storage" {
  name                     = "acips02${var.environment}lake"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
}


# 3. Azure Container Registry (ACR)
resource "azurerm_container_registry" "acr" {
  name                = "acips02registry${var.environment}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Standard"
  admin_enabled       = true
}

# 4. Azure Container Apps Environment
resource "azurerm_container_app_environment" "app_env" {
  name                = "acip-s02-env-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

# 5. Azure Container App (S02 Engine)
resource "azurerm_container_app" "tender_engine_app" {
  name                         = "acip-s02-engine-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.app_env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  template {
    container {
      name   = "tender-engine"
      image  = var.docker_image
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "CLOUD_PROVIDER"
        value = "AZURE"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8085
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
