output "ecr_repository_url" {
  value       = aws_ecr_repository.agent_repo.repository_url
  description = "The URL of the ECR repository to push your Docker image to."
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_task_definition" {
  value = aws_ecs_task_definition.agent_task.family
}

output "alb_url" {
  description = "The URL of the Application Load Balancer to access the Web UI"
  value       = "http://${aws_lb.alb.dns_name}:8000"
}
