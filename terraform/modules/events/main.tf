# =============================================================================
# Module: Event-Driven Integrations (S3, SQS, SNS)
# Phase 3 — Creates object storage, message queue, and pub/sub topic
# =============================================================================

# --- S3 Bucket ---
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "aws_s3_bucket" "main" {
  bucket = "${var.project_name}-bucket-${random_string.suffix.result}"

  tags = {
    Name = "${var.project_name}-bucket"
  }
}

# Enforce security: Block public access to the bucket
resource "aws_s3_bucket_public_access_block" "main_block" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- SQS Queue ---
resource "aws_sqs_queue" "main" {
  name                      = "${var.project_name}-queue"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 345600 # 4 days
  receive_wait_time_seconds = 0

  tags = {
    Name = "${var.project_name}-queue"
  }
}

# --- SNS Topic ---
resource "aws_sns_topic" "main" {
  name = "${var.project_name}-topic"

  tags = {
    Name = "${var.project_name}-topic"
  }
}
