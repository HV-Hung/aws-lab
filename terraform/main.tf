# =============================================================================
# Root Module — Wire all child modules together
# Enable each module as you progress through the phases.
# =============================================================================

# --- Phase 1: Network & Security ---
module "network" {
  source = "./modules/network"

  project_name        = var.project_name
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidrs = var.public_subnet_cidrs
  db_subnet_cidrs     = var.db_subnet_cidrs
  container_port      = var.container_port
}

# --- Phase 2: Data Tier (RDS + Secrets Manager) ---
# Uncomment when ready for Phase 2
module "data" {
  source = "./modules/data"

  project_name   = var.project_name
  vpc_id         = module.network.vpc_id
  db_subnet_ids  = module.network.db_subnet_ids
  rds_sg_id      = module.network.rds_sg_id
  instance_class = var.db_instance_class
}

# --- Phase 3: Event-Driven Integrations (S3, SQS, SNS) ---
# Uncomment when ready for Phase 3
module "events" {
  source = "./modules/events"

  project_name = var.project_name
}

# --- Phase 4: Compute & Application (ECR, ECS, ALB) ---
# Uncomment when ready for Phase 4
module "compute" {
  source = "./modules/compute"

  project_name        = var.project_name
  vpc_id              = module.network.vpc_id
  public_subnet_ids   = module.network.public_subnet_ids
  alb_sg_id           = module.network.alb_sg_id
  ecs_sg_id           = module.network.ecs_sg_id
  container_port      = var.container_port
  rds_secret_arn      = module.data.secret_arn
  s3_bucket_arn       = module.events.s3_bucket_arn
  sqs_queue_arn       = module.events.sqs_queue_arn
  sns_topic_arn       = module.events.sns_topic_arn
  s3_bucket_name      = module.events.s3_bucket_name
  sqs_queue_url       = module.events.sqs_queue_url
}
