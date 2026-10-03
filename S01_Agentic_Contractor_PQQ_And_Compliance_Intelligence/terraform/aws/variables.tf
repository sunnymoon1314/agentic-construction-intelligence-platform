variable "aws_region" {
  description = "The AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "enterprise-mcp-agent"
}

variable "openai_api_key" {
  description = "API Key for OpenAI (if using an external API instead of local Ollama)"
  type        = string
  default     = ""
  sensitive   = true
}
