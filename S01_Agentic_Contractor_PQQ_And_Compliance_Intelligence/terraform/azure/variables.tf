variable "project_name" {
  description = "The name of the project (used for resource names)"
  type        = string
  default     = "enterprisemcpagent"
}

variable "location" {
  description = "The Azure Region"
  type        = string
  default     = "East US"
}

variable "docker_image" {
  description = "The Docker image for the MCP server. Defaults to a placeholder until you push your real image."
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}
