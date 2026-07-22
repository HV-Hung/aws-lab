# AWS Learning Project

A hands-on AWS learning project that provisions real cloud infrastructure using **Terraform** and interacts with it through a **Python FastAPI** application running on **ECS Fargate**.

> **Purpose**: Learn AWS services by building, deploying, and destroying real infrastructure. Terraform enables rapid provisioning and teardown to minimize costs.

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| AWS CLI | v2+ | Authenticate and interact with AWS |
| Terraform | ≥ 1.5.0 | Infrastructure as Code |
| Docker | Latest | Build container images |
| Python | 3.11+ | Local development |

### Deploy Everything

```bash
# 1. Configure AWS credentials
aws configure
# or for SSO:
eval "$(aws configure export-credentials --profile default --format env)"

# 2. Deploy infrastructure + app
sh scripts/deploy.sh

# 3. Access the app
# URL is printed at the end of deploy.sh output
curl http://<ALB_DNS>/health
```

### Tear Down Everything

```bash
sh scripts/destroy.sh
```

---

## Project Structure

```
aws-starting/
├── app/                          # Python FastAPI application
│   ├── core/                     # Shared modules
│   │   ├── aws.py                # Boto3 client factories (S3, SQS, SNS)
│   │   └── config.py             # Configuration loader (env vars / Secrets Manager)
│   ├── routers/                  # API route handlers
│   │   ├── health.py             # GET /health
│   │   ├── db.py                 # /db/* — RDS PostgreSQL CRUD
│   │   ├── storage.py            # /s3/* — S3 upload, list, download
│   │   ├── queue.py              # /sqs/* — SQS send, receive, stats
│   │   └── notify.py             # /sns/* — SNS publish, list subscriptions
│   ├── main.py                   # FastAPI app entrypoint
│   ├── Dockerfile                # Container image definition
│   └── requirements.txt          # Python dependencies
├── terraform/                    # Infrastructure as Code
│   ├── modules/
│   │   ├── network/              # Phase 1: VPC, subnets, security groups
│   │   ├── data/                 # Phase 2: RDS, Secrets Manager
│   │   ├── events/               # Phase 3: S3, SQS, SNS
│   │   └── compute/              # Phase 4: ECR, ECS, ALB, IAM
│   ├── main.tf                   # Root module — wires child modules
│   ├── variables.tf              # Input variable declarations
│   ├── outputs.tf                # Output values (ALB URL, ECR URL, etc.)
│   ├── provider.tf               # AWS provider + Terraform version
│   └── terraform.tfvars          # Variable overrides
├── scripts/
│   ├── deploy.sh                 # Full deploy pipeline
│   └── destroy.sh                # Full teardown
├── docs/                         # ← You are here
└── .gitignore
```

---

## Documentation Index

| Document | Description |
|---|---|
| [Architecture](architecture.md) | System architecture, AWS services, and network topology |
| [Configuration](configuration.md) | All configurable variables, environment variables, and secrets |
| [App Behavior](app-behavior.md) | API endpoints, request/response examples, and app logic |
| [IAM & Access Control](iam-access-control.md) | IAM roles, policies, security groups, and least-privilege design |
| [Cost Analysis](cost-analysis.md) | Per-service cost breakdown and optimization strategies |
| [Troubleshooting](troubleshooting.md) | Common errors encountered and how to fix them |
