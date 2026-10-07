terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. S3 Medallion Analytical Bucket
resource "aws_s3_bucket" "tender_lake" {
  bucket        = "acip-s02-tender-lake-${var.environment}-${var.aws_region}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "tender_lake_versioning" {
  bucket = aws_s3_bucket.tender_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 2. ECR Repository for S02 Engine
resource "aws_ecr_repository" "tender_engine_repo" {
  name                 = "acip-s02-tender-engine"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# 3. IAM Task Execution Role for ECS Fargate
resource "aws_iam_role" "ecs_execution_role" {
  name = "acip-s02-ecs-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# 4. ECS Cluster & Fargate Task Definition
resource "aws_ecs_cluster" "tender_cluster" {
  name = "acip-s02-cluster-${var.environment}"
}

resource "aws_cloudwatch_log_group" "tender_logs" {
  name              = "/ecs/acip-s02-tender-${var.environment}"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "tender_task" {
  family                   = "acip-s02-tender-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "tender-engine"
      image     = "${aws_ecr_repository.tender_engine_repo.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8085
          hostPort      = 8085
        }
      ]
      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "CLOUD_PROVIDER", value = "AWS" },
        { name = "S3_MEDALLION_BUCKET", value = aws_s3_bucket.tender_lake.bucket }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.tender_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# 5. VPC Network for ECS Fargate & ALB
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "acip-s02-vpc-${var.environment}"
  }
}

resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"

  tags = {
    Name = "acip-s02-public-subnet-1"
  }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}b"

  tags = {
    Name = "acip-s02-public-subnet-2"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "acip-s02-igw-${var.environment}"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "acip-s02-public-rt"
  }
}

resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public_rt.id
}

# 6. Security Group for ECS & ALB
resource "aws_security_group" "ecs_sg" {
  name        = "acip-s02-ecs-sg-${var.environment}"
  description = "Allow inbound traffic on port 8085 and all outbound traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 8085
    to_port     = 8085
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "acip-s02-ecs-sg"
  }
}

# 7. Application Load Balancer
resource "aws_lb" "alb" {
  name               = "acip-s02-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.ecs_sg.id]
  subnets            = [aws_subnet.public_1.id, aws_subnet.public_2.id]

  tags = {
    Name = "acip-s02-alb"
  }
}

resource "aws_lb_target_group" "target_group" {
  name        = "acip-s02-tg-${var.environment}"
  port        = 8085
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    port                = "8085"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }
}

resource "aws_lb_listener" "listener" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "8085"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.target_group.arn
  }
}

# 8. ECS Fargate Service (Continuously hosts live dashboard on AWS)
resource "aws_ecs_service" "tender_service" {
  name            = "acip-s02-service-${var.environment}"
  cluster         = aws_ecs_cluster.tender_cluster.id
  task_definition = aws_ecs_task_definition.tender_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.target_group.arn
    container_name   = "tender-engine"
    container_port   = 8085
  }

  depends_on = [aws_lb_listener.listener]
}

