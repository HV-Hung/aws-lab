# --- Network Outputs ---
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.network.vpc_id
}

# --- Data Outputs ---
# Uncomment when Phase 2 is enabled
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.data.rds_endpoint
}

# --- Events Outputs ---
# Uncomment when Phase 3 is enabled
output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = module.events.s3_bucket_name
}
output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = module.events.sqs_queue_url
}
output "sns_topic_arn" {
  description = "SNS topic ARN"
  value       = module.events.sns_topic_arn
}

# --- Compute Outputs ---
# Uncomment when Phase 4 is enabled
output "alb_dns_name" {
  description = "ALB DNS name — use this to access the app"
  value       = module.compute.alb_dns_name
}
output "ecr_repository_url" {
  description = "ECR repository URL for pushing Docker images"
  value       = module.compute.ecr_repository_url
}
