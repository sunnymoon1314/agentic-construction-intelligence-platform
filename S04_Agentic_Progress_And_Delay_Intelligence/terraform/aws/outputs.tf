output "delay_lake_bucket" {
  description = "S3 bucket storing Approach 3 partitioned Parquet lakehouse"
  value       = aws_s3_bucket.delay_lake.bucket
}

output "ecr_repository_url" {
  description = "ECR Docker repository URL"
  value       = aws_ecr_repository.delay_engine_repo.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.delay_cluster.name
}

output "aws_region" {
  description = "AWS region deployed"
  value       = var.aws_region
}

output "alb_url" {
  description = "Public URL of the AWS Application Load Balancer"
  value       = "http://${aws_lb.alb.dns_name}:${var.app_port}"
}
