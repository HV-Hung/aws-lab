# AWS Learning Project

A hands-on project for learning AWS by building, deploying, and tearing down real cloud infrastructure using **Terraform** and a **Python FastAPI** application on **ECS Fargate**.

```
Internet → ALB (HTTP:80) → ECS Fargate (FastAPI) → RDS / S3 / SQS / SNS
```

---

## What You'll Learn

| Phase | AWS Services | Concepts |
|---|---|---|
| **1. Network** | VPC, Subnets, IGW, Security Groups | Network isolation, chained security groups |
| **2. Data** | RDS PostgreSQL, Secrets Manager | Managed databases, secret injection |
| **3. Events** | S3, SQS, SNS | Object storage, message queues, pub/sub |
| **4. Compute** | ECR, ECS Fargate, ALB, IAM, CloudWatch | Containers, load balancing, least-privilege IAM |

---

## Quick Start

### Prerequisites

- **AWS CLI** v2+ (configured with `aws configure`)
- **Terraform** ≥ 1.5.0
- **Docker** (for building container images)
- **Python** 3.11+ (for local development)

### Deploy

```bash
# Deploy infrastructure + build Docker image + launch on ECS
sh scripts/deploy.sh
```

The script will output your app URL at the end:
```
App URL: http://aws-learning-alb-xxxxx.ap-southeast-1.elb.amazonaws.com
```

### Test

```bash
ALB="http://aws-learning-alb-xxxxx.ap-southeast-1.elb.amazonaws.com"

# Health check
curl $ALB/health

# Initialize database table (required once)
curl -X POST $ALB/db/init

# Create an item in RDS
curl -X POST $ALB/db/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "description": "Stored in RDS!"}'

# Upload a file to S3
echo "Hello AWS!" > test.txt
curl -X POST $ALB/s3/upload -F "file=@test.txt"

# Send a message to SQS
curl -X POST $ALB/sqs/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Background job #1"}'

# Receive the message from SQS
curl $ALB/sqs/receive

# Publish to SNS
curl -X POST $ALB/sns/publish \
  -H "Content-Type: application/json" \
  -d '{"message": "Alert!", "subject": "Test"}'
```

### Destroy (Stop All Costs)

```bash
sh scripts/destroy.sh
```

---

## Project Structure

```
aws-starting/
├── app/                        # Python FastAPI application
│   ├── core/                   # Config loader + boto3 client factories
│   ├── routers/                # API routes (health, db, storage, queue, notify)
│   ├── main.py                 # App entrypoint
│   ├── Dockerfile              # Container image
│   └── requirements.txt        # Python deps
├── terraform/                  # Infrastructure as Code
│   ├── modules/
│   │   ├── network/            # VPC, subnets, security groups
│   │   ├── data/               # RDS, Secrets Manager
│   │   ├── events/             # S3, SQS, SNS
│   │   └── compute/            # ECR, ECS, ALB, IAM
│   ├── main.tf                 # Root module
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # Output values
│   └── provider.tf             # AWS provider config
├── scripts/
│   ├── deploy.sh               # Full deploy pipeline
│   └── destroy.sh              # Full teardown
└── docs/                       # Documentation
    ├── architecture.md          # System design & network topology
    ├── configuration.md         # All variables & env config
    ├── app-behavior.md          # API endpoints & examples
    ├── iam-access-control.md    # IAM roles, policies, security groups
    ├── cost-analysis.md         # Per-service cost breakdown
    └── troubleshooting.md       # Common errors & fixes
```

---

## API Endpoints

| Method | Path | Service | Description |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `POST` | `/db/init` | RDS | Create the items table |
| `POST` | `/db/items` | RDS | Create an item |
| `GET` | `/db/items` | RDS | List all items |
| `DELETE` | `/db/items/{id}` | RDS | Delete an item |
| `POST` | `/s3/upload` | S3 | Upload a file |
| `GET` | `/s3/files` | S3 | List files |
| `GET` | `/s3/download/{key}` | S3 | Get presigned download URL |
| `POST` | `/sqs/send` | SQS | Send a message |
| `GET` | `/sqs/receive` | SQS | Receive & delete a message |
| `GET` | `/sqs/stats` | SQS | Queue statistics |
| `POST` | `/sns/publish` | SNS | Publish a broadcast |
| `GET` | `/sns/subscriptions` | SNS | List subscriptions |

Interactive Swagger docs available at `http://<ALB_DNS>/docs`.

---

## Cost

| Usage | Estimated Monthly Cost |
|---|---|
| **2 hours/day** (recommended) | **~$4** |
| **24/7** | ~$40 |
| **Destroyed** | $0 |

The most expensive component is the ALB (~$16/month if running 24/7). Always run `destroy.sh` when done.

See [docs/cost-analysis.md](docs/cost-analysis.md) for a full breakdown.

---

## Architecture

![Architecture Diagram](docs/architecture-diagram.png)

```
Internet ──► ALB-SG (80/443) ──► ECS-SG (8000) ──► RDS-SG (5432)
                                      │
                                      ├──► S3  (file storage)
                                      ├──► SQS (message queue)
                                      └──► SNS (pub/sub)
```

- **Security groups are chained**: each layer only accepts traffic from the previous one
- **RDS is doubly isolated**: private subnet + SG restriction
- **No NAT Gateway**: ECS tasks use public IPs to save ~$32/month
- **IAM follows least privilege**: Task Role only grants the specific API actions the app uses

See [docs/architecture.md](docs/architecture.md) for full details.

---

## Documentation

| Document | What's Inside |
|---|---|
| [Architecture](docs/architecture.md) | Diagrams, service map, network topology, data flows |
| [Configuration](docs/configuration.md) | Terraform variables, env vars, container config |
| [App Behavior](docs/app-behavior.md) | Every endpoint with curl examples |
| [IAM & Access Control](docs/iam-access-control.md) | Roles, policies, security groups, access matrix |
| [Cost Analysis](docs/cost-analysis.md) | Per-service pricing, optimization tips |
| [Troubleshooting](docs/troubleshooting.md) | Common errors and solutions |

---

## License

This project is for educational purposes.
