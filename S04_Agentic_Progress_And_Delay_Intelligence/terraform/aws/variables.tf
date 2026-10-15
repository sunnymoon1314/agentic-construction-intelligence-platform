variable "aws_region" {
  description = "AWS region for ACIP S04 deployment"
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "app_port" {
  description = "User-defined port for ACIP S04 cockpit"
  type        = number
  default     = 8087
}
