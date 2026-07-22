# Configuration

All configurable values in this project, organized by layer.

---

## Terraform Variables

Defined in `terraform/variables.tf`, overridden in `terraform/terraform.tfvars`.

| Variable | Type | Default | Description |
|---|---|---|---|
| `region` | `string` | `ap-southeast-1` | AWS region to deploy into |
| `project_name` | `string` | `aws-learning` | Used as prefix for all resource names and tags |
| `vpc_cidr` | `string` | `10.0.0.0/16` | CIDR block for the VPC |
| `public_subnet_cidrs` | `list(string)` | `["10.0.1.0/24", "10.0.2.0/24"]` | Public subnet CIDRs (one per AZ) |
| `db_subnet_cidrs` | `list(string)` | `["10.0.101.0/24", "10.0.102.0/24"]` | Database subnet CIDRs (isolated, one per AZ) |
| `db_instance_class` | `string` | `db.t4g.micro` | RDS instance type (cheapest Graviton option) |
| `container_port` | `number` | `8000` | Port the FastAPI app listens on inside the container |

### How to Override

Edit `terraform/terraform.tfvars`:

```hcl
region           = "us-east-1"
project_name     = "my-project"
db_instance_class = "db.t4g.small"
```

Or pass on the command line:

```bash
terraform apply -var="region=us-west-2"
```

---

## Default Tags

All AWS resources are tagged automatically via the provider configuration in `terraform/provider.tf`:

| Tag | Value |
|---|---|
| `Project` | Value of `var.project_name` (default: `aws-learning`) |
| `Environment` | `learning` |
| `ManagedBy` | `terraform` |

---

## Application Environment Variables

These environment variables are injected into the ECS container by the Task Definition.

### Standard Environment Variables

Set via the `environment` block in the Task Definition:

| Variable | Source | Example Value |
|---|---|---|
| `AWS_REGION` | `data.aws_region.current.name` | `ap-southeast-1` |
| `S3_BUCKET_NAME` | `module.events.s3_bucket_name` | `aws-learning-bucket-tvivgu` |
| `SQS_QUEUE_URL` | `module.events.sqs_queue_url` | `https://sqs.ap-southeast-1.amazonaws.com/...` |
| `SNS_TOPIC_ARN` | `module.events.sns_topic_arn` | `arn:aws:sns:ap-southeast-1:...` |

### Secrets (Injected by ECS)

Set via the `secrets` block in the Task Definition. ECS automatically fetches the value from Secrets Manager at task launch time:

| Variable | Source | Injected Value |
|---|---|---|
| `DB_SECRET_ARN` | Secrets Manager ARN | `{"username":"postgres","password":"...","host":"...","port":5432,"dbname":"awslearning"}` |

> **Important**: Despite the name `DB_SECRET_ARN`, when using the ECS `secrets` block, the actual JSON string is injected — not the ARN. The app detects this by checking if the value starts with `{` and parses it directly.

### Local Development Environment Variables

When running locally (without ECS), the app reads from a `.env` file or shell environment:

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `postgres` | Database name |
| `DB_USER` | `postgres` | Database username |
| `DB_PASSWORD` | `local` | Database password |
| `AWS_REGION` | `ap-southeast-1` | AWS region for boto3 clients |
| `S3_BUCKET_NAME` | (empty) | S3 bucket name |
| `SQS_QUEUE_URL` | (empty) | SQS queue URL |
| `SNS_TOPIC_ARN` | (empty) | SNS topic ARN |

---

## Terraform Outputs

After running `terraform apply`, these values are available:

| Output | Description | Example |
|---|---|---|
| `vpc_id` | VPC identifier | `vpc-082869ca56b5e01df` |
| `rds_endpoint` | RDS connection endpoint | `aws-learning-db.xxx.rds.amazonaws.com:5432` |
| `s3_bucket_name` | S3 bucket name | `aws-learning-bucket-tvivgu` |
| `sqs_queue_url` | SQS queue URL | `https://sqs.ap-southeast-1.amazonaws.com/...` |
| `sns_topic_arn` | SNS topic ARN | `arn:aws:sns:ap-southeast-1:...` |
| `alb_dns_name` | ALB DNS — your app URL | `aws-learning-alb-xxx.elb.amazonaws.com` |
| `ecr_repository_url` | ECR repo URL for Docker push | `538661800758.dkr.ecr.ap-southeast-1.amazonaws.com/aws-learning-repo` |

Retrieve any output:

```bash
cd terraform
terraform output alb_dns_name
```

---

## Container Configuration

Defined in the ECS Task Definition (`terraform/modules/compute/main.tf`):

| Parameter | Value | Notes |
|---|---|---|
| CPU | 256 (0.25 vCPU) | Smallest Fargate option |
| Memory | 512 MB | Smallest Fargate option |
| Launch Type | FARGATE | Serverless — no EC2 instances to manage |
| Desired Count | 1 | Single task for learning |
| Platform Version | LATEST | Currently 1.4.0 |
| Log Driver | `awslogs` | Sends stdout/stderr to CloudWatch |
| Log Retention | 7 days | Keeps costs minimal |
| Health Check Path | `/health` | ALB checks every 10 seconds |

---

## RDS Configuration

| Parameter | Value | Notes |
|---|---|---|
| Engine | PostgreSQL 16 | Latest stable version |
| Instance Class | `db.t4g.micro` | Graviton, cheapest option (~$0.016/hr) |
| Storage | 20 GB gp3 | General purpose SSD |
| Publicly Accessible | `false` | Only reachable from ECS-SG |
| Skip Final Snapshot | `true` | Required for easy teardown in learning mode |
| Password | Auto-generated | 16 characters via `random_password` |
| Secret Recovery Window | 0 days | Allows instant delete/recreate cycles |
