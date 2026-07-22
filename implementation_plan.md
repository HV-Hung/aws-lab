# AWS Dynamic Container — Implementation Plan

> **Goal:** Learn AWS quickly by building a real, working architecture in incremental phases.
> Each phase teaches a specific AWS domain, uses Terraform to provision/destroy resources on demand, and includes a Python app to interact with the deployed services.

---

## Cost Strategy

| Principle | Detail |
|---|---|
| **Provision & Destroy** | Run `terraform apply` to learn → verify it works → `terraform destroy` when done. Never leave resources running overnight. |
| **Estimated running cost** | ~$0.12/hour while resources are up (RDS `db.t4g.micro` + Fargate 0.25 vCPU + ALB). |
| **Free-tier services** | S3, SQS, SNS cost $0 at low volumes. Secrets Manager has a 30-day free trial per secret. |
| **Destroy checklist** | After each session: `terraform destroy -auto-approve` → verify in AWS Console that no resources remain (especially ALBs, RDS, and NAT Gateways). |

---

## Prerequisites (Do Once)

- [x] **AWS Account** — Logged in as root (`arn:aws:iam::538661800758:root`), region `ap-southeast-1`. ⚠️ *Recommend creating a dedicated IAM admin user later instead of using root.*
- [x] **AWS CLI v2** — Installed and configured. Region: `ap-southeast-1`, credentials via `aws configure`.
- [x] **Terraform v1.15.8** — Installed.
- [x] **Docker v29.6.1** — Installed.
- [x] **Python 3.14.4** — Installed (use `python3` command).
- [x] **Project structure** — Created (see below):

```
aws-starting/
├── architechture.md          # (existing) Architecture design
├── implementation_plan.md    # (this file) Step-by-step plan
├── terraform/
│   ├── main.tf               # Root module — wires all child modules together
│   ├── variables.tf           # Input variables (region, project name, etc.)
│   ├── outputs.tf             # Outputs (ALB DNS, RDS endpoint, etc.)
│   ├── provider.tf            # AWS provider configuration
│   ├── terraform.tfvars       # Variable values (gitignored)
│   ├── modules/
│   │   ├── network/           # Phase 1 — VPC, subnets, SGs
│   │   ├── data/              # Phase 2 — RDS, Secrets Manager
│   │   ├── events/            # Phase 3 — S3, SQS, SNS
│   │   └── compute/           # Phase 4 — ECR, ECS Fargate, ALB
├── app/
│   ├── Dockerfile             # Container image definition
│   ├── requirements.txt       # Python dependencies
│   ├── main.py                # FastAPI app — routes for each AWS service
│   ├── routers/
│   │   ├── health.py          # GET /health — basic health check
│   │   ├── db.py              # CRUD routes for RDS/PostgreSQL
│   │   ├── storage.py         # Routes for S3 upload/download/list
│   │   ├── queue.py           # Routes for SQS send/receive
│   │   └── notify.py          # Routes for SNS publish
│   └── core/
│       ├── config.py          # Load config from env vars / Secrets Manager
│       └── aws.py             # Shared boto3 client helpers
└── scripts/
    ├── deploy.sh              # Convenience: terraform apply + docker push + ECS update
    └── destroy.sh             # Convenience: terraform destroy
```

---

## Phase 1 — Network & Security (VPC)

### What You Will Learn

- VPC, Subnets (public vs. database-private), Internet Gateway, Route Tables
- Security Groups and how inbound/outbound rules chain together
- Why we skip NAT Gateway (cost saving) and the trade-off

### Terraform Resources to Create

| Resource | Purpose |
|---|---|
| `aws_vpc` | Custom VPC with DNS support enabled |
| `aws_subnet` (×2 public) | Public subnets in 2 AZs (needed by ALB later) |
| `aws_subnet` (×2 database) | Isolated database subnets (no internet route) |
| `aws_internet_gateway` | Allows public subnets to reach the internet |
| `aws_route_table` + `aws_route` | Default route `0.0.0.0/0 → IGW` for public subnets |
| `aws_route_table_association` | Associate public subnets with the public route table |
| `aws_security_group` (ALB-SG) | Inbound: 80, 443 from `0.0.0.0/0` |
| `aws_security_group` (ECS-SG) | Inbound: app port (8000) from ALB-SG only |
| `aws_security_group` (RDS-SG) | Inbound: 5432 from ECS-SG only |

### Steps

1. **Create `terraform/provider.tf`** — Configure the AWS provider with your region.
2. **Create `terraform/variables.tf`** — Define variables: `region`, `project_name`, `vpc_cidr`, `public_subnet_cidrs`, `db_subnet_cidrs`.
3. **Create `terraform/modules/network/`** — Implement all VPC resources listed above. Export VPC ID, subnet IDs, and security group IDs as outputs.
4. **Create `terraform/main.tf`** — Call the `network` module.
5. **Run:**
   ```bash
   cd terraform
   terraform init
   terraform plan        # Review what will be created
   terraform apply       # Create the VPC
   ```
6. **Verify in AWS Console:**
   - Go to VPC → Your VPCs → confirm the new VPC exists.
   - Go to Subnets → confirm 4 subnets (2 public, 2 database).
   - Go to Security Groups → confirm 3 SGs with correct rules.
7. **Learning checkpoint:** Manually try to launch an EC2 instance in a database subnet — can it reach the internet? (Answer: no, because there's no route to the IGW.)
8. **Destroy:** `terraform destroy -auto-approve`

### Python App (Phase 1)

No AWS interaction yet. Scaffold the app locally:

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn boto3 psycopg2-binary python-dotenv
pip freeze > requirements.txt
```

Create `main.py` with a basic FastAPI app and a `GET /health` endpoint that returns `{"status": "ok"}`. Test locally with `uvicorn main:app --reload`.

---

## Phase 2 — Data Tier (RDS + Secrets Manager)

### What You Will Learn

- Amazon RDS (PostgreSQL) — instance classes, storage, single-AZ vs. multi-AZ
- DB Subnet Groups — how RDS decides which subnets to deploy into
- AWS Secrets Manager — auto-generated passwords, secret rotation concepts
- How an application fetches secrets at runtime (zero-trust, no hardcoded passwords)

### Terraform Resources to Create

| Resource | Purpose |
|---|---|
| `aws_db_subnet_group` | Groups the 2 database subnets for RDS placement |
| `random_password` | Generate a secure DB password via Terraform |
| `aws_secretsmanager_secret` + `aws_secretsmanager_secret_version` | Store DB credentials (host, port, dbname, username, password) as JSON |
| `aws_db_instance` | PostgreSQL 16, `db.t4g.micro`, 20 GB gp3, single-AZ, no public access |

### Steps

1. **Create `terraform/modules/data/`** — Implement RDS + Secrets Manager resources. Accept VPC ID, database subnet IDs, and RDS-SG ID as inputs.
2. **Wire into `terraform/main.tf`** — Call the `data` module, passing outputs from `network`.
3. **Run `terraform apply`** — This takes ~5-8 minutes (RDS creation is slow).
4. **Verify:**
   - AWS Console → RDS → confirm the instance is "Available".
   - AWS Console → Secrets Manager → confirm the secret exists and contains valid JSON credentials.
   - The RDS instance should NOT be publicly accessible (verify "Publicly Accessible: No").
5. **Learning checkpoint:** Try to connect to the RDS instance from your local machine — it should fail (no public access, no route). Understand why this is secure.
6. **Destroy:** `terraform destroy -auto-approve`

### Python App (Phase 2)

Add database interaction routes:

- **`app/core/config.py`** — Write a function that uses `boto3` to fetch the secret from Secrets Manager and parse the JSON credentials.
- **`app/routers/db.py`** — Create routes:
  - `POST /db/init` — Create a sample `items` table.
  - `POST /db/items` — Insert an item.
  - `GET /db/items` — List all items.
  - `DELETE /db/items/{id}` — Delete an item.
- Test locally by pointing to a local PostgreSQL (Docker: `docker run -p 5432:5432 -e POSTGRES_PASSWORD=local postgres:16`). The real Secrets Manager fetch will work when deployed in Phase 4.

---

## Phase 3 — Event-Driven Integrations (S3, SQS, SNS)

### What You Will Learn

- Amazon S3 — buckets, objects, presigned URLs, bucket policies
- Amazon SQS — standard queues, message visibility, polling
- Amazon SNS — topics, subscriptions, fan-out pattern
- IAM policies — how to grant least-privilege access to each service
- All three services are **free at low volume** — ideal for learning

### Terraform Resources to Create

| Resource | Purpose |
|---|---|
| `aws_s3_bucket` | Object storage bucket |
| `aws_s3_bucket_public_access_block` | Block all public access (security best practice) |
| `aws_sqs_queue` | Standard message queue |
| `aws_sns_topic` | Notification topic |
| `aws_sns_topic_subscription` | (Optional) Email subscription to see notifications arrive |

### Steps

1. **Create `terraform/modules/events/`** — Implement S3, SQS, SNS resources. Export bucket name, queue URL, topic ARN.
2. **Wire into `terraform/main.tf`**.
3. **Run `terraform apply`** — Almost instant (these are serverless/free-tier).
4. **Verify:**
   - AWS Console → S3 → confirm bucket exists, public access is blocked.
   - AWS Console → SQS → confirm queue exists.
   - AWS Console → SNS → confirm topic exists. If you added an email subscription, confirm it via email.
5. **Learning checkpoint:** Use the AWS CLI to test each service manually:
   ```bash
   # S3
   echo "hello" > /tmp/test.txt
   aws s3 cp /tmp/test.txt s3://YOUR_BUCKET/test.txt
   aws s3 ls s3://YOUR_BUCKET/

   # SQS
   aws sqs send-message --queue-url YOUR_QUEUE_URL --message-body "test message"
   aws sqs receive-message --queue-url YOUR_QUEUE_URL

   # SNS
   aws sns publish --topic-arn YOUR_TOPIC_ARN --message "hello from CLI"
   ```
6. **Destroy:** `terraform destroy -auto-approve`

### Python App (Phase 3)

Add routes that use `boto3` to interact with each service:

- **`app/routers/storage.py`** (S3):
  - `POST /s3/upload` — Upload a file to S3.
  - `GET /s3/files` — List objects in the bucket.
  - `GET /s3/download/{key}` — Download / generate presigned URL.
- **`app/routers/queue.py`** (SQS):
  - `POST /sqs/send` — Send a message to the queue.
  - `GET /sqs/receive` — Receive and delete a message from the queue.
  - `GET /sqs/stats` — Get queue attributes (approximate message count).
- **`app/routers/notify.py`** (SNS):
  - `POST /sns/publish` — Publish a message to the topic.
  - `GET /sns/subscriptions` — List current subscriptions.

Test locally using your AWS CLI credentials (boto3 will pick them up from `~/.aws/credentials`).

---

## Phase 4 — Compute & Application (ECR + ECS Fargate + ALB)

### What You Will Learn

- Docker image building and pushing to ECR
- ECS concepts: Cluster, Task Definition, Service, Fargate launch type
- Application Load Balancer — target groups, health checks, listeners
- IAM Roles for ECS: Task Execution Role vs. Task Role (critical distinction)
- CloudWatch Logs — where your container stdout/stderr goes
- How environment variables and secrets are injected into containers

### Terraform Resources to Create

| Resource | Purpose |
|---|---|
| `aws_ecr_repository` | Private Docker image registry |
| `aws_ecs_cluster` | Logical grouping for ECS services |
| `aws_iam_role` (Task Execution Role) | Allows Fargate to pull images, write logs, read secrets |
| `aws_iam_role` (Task Role) | Allows app code to call S3, SQS, SNS |
| `aws_iam_role_policy` / `aws_iam_policy_attachment` | Attach permissions to each role |
| `aws_cloudwatch_log_group` | Log destination for container output |
| `aws_ecs_task_definition` | Container config: image, CPU, memory, env vars, secrets, ports |
| `aws_lb` (ALB) | Internet-facing load balancer in public subnets |
| `aws_lb_target_group` | Health-checked target for ECS tasks (IP type) |
| `aws_lb_listener` | HTTP:80 → forward to target group |
| `aws_ecs_service` | Runs 1 Fargate task, registers with ALB target group |

### Steps

1. **Create `app/Dockerfile`:**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   EXPOSE 8000
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```
2. **Test locally:** `docker build -t aws-app . && docker run -p 8000:8000 aws-app` → hit `http://localhost:8000/health`.
3. **Create `terraform/modules/compute/`** — Implement all resources above. Accept outputs from `network`, `data`, and `events` modules.
4. **Wire into `terraform/main.tf`**.
5. **Run `terraform apply`** — Creates ECR, ECS cluster, ALB, IAM roles, etc.
6. **Build & Push the Docker image:**
   ```bash
   # Login to ECR
   aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

   # Build & push
   docker build -t aws-app ./app
   docker tag aws-app:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/aws-app:latest
   docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/aws-app:latest
   ```
7. **Force ECS service to pick up the new image** (if task definition already references `latest`):
   ```bash
   aws ecs update-service --cluster aws-learning --service aws-app --force-new-deployment
   ```
8. **Verify:**
   - Get the ALB DNS from Terraform output: `terraform output alb_dns_name`
   - `curl http://ALB_DNS/health` → should return `{"status": "ok"}`
   - `curl http://ALB_DNS/db/items` → should connect to RDS and return data
   - `curl -X POST http://ALB_DNS/sqs/send -d '{"message":"hello"}'` → sends to SQS
   - Check CloudWatch Logs → you should see FastAPI request logs
9. **Learning checkpoint:**
   - SSH into the container? No — Fargate is serverless, you can't SSH. Use `aws ecs execute-command` (requires enabling `execute_command` in the service).
   - What happens if you stop the task? ECS service will automatically relaunch it (desired count = 1).
10. **Destroy:** `terraform destroy -auto-approve`

---

## Phase 5 — End-to-End Validation & Cleanup

### What You Will Learn

- How all the pieces fit together end-to-end
- Debugging common issues (security group misconfigs, IAM permission denials, ECS task failures)
- Reading CloudWatch Logs to troubleshoot
- The full lifecycle: provision → deploy → test → destroy

### Steps

1. **Full deploy:** Run all phases together:
   ```bash
   cd terraform
   terraform apply -auto-approve
   # Wait for RDS (~5 min), then push Docker image, then force ECS redeployment
   ```
2. **Run through every API endpoint** — Use the Python app's interactive docs at `http://ALB_DNS/docs` (FastAPI auto-generates Swagger UI).
3. **Intentionally break things and observe:**
   - Remove the S3 permission from the Task Role → try uploading → see the IAM `AccessDenied` error.
   - Change the RDS-SG to block ECS → watch the DB connection fail.
   - Scale the ECS service to 0 → watch the ALB return 503.
4. **Final destroy:**
   ```bash
   terraform destroy -auto-approve
   ```
5. **Console audit** — Manually check the AWS Console to confirm zero remaining resources. Pay special attention to:
   - EC2 → Load Balancers (ALBs sometimes linger)
   - RDS → Databases (check for snapshots)
   - ECR → Repositories (delete images)
   - CloudWatch → Log Groups

---

## Quick Reference — Terraform Workflow

```bash
# Always run from the terraform/ directory

# Initialize (first time or after adding modules)
terraform init

# Preview changes
terraform plan

# Apply changes
terraform apply

# Destroy everything (ALWAYS do this when you're done learning for the day)
terraform destroy -auto-approve

# Show current state
terraform state list

# Show specific resource details
terraform state show aws_db_instance.this
```

---

## Quick Reference — Estimated Time Per Phase

| Phase | Focus | Estimated Time | AWS Cost While Running |
|---|---|---|---|
| Phase 1 | VPC, Subnets, Security Groups | 1–2 hours | $0 (VPC is free) |
| Phase 2 | RDS, Secrets Manager | 2–3 hours | ~$0.02/hr (db.t4g.micro) |
| Phase 3 | S3, SQS, SNS | 1–2 hours | $0 (free tier) |
| Phase 4 | ECR, ECS Fargate, ALB | 3–4 hours | ~$0.10/hr (Fargate + ALB) |
| Phase 5 | End-to-end testing | 1–2 hours | ~$0.12/hr (everything) |
| **Total** | | **8–13 hours** | |

---

## Key AWS Concepts Cheat Sheet

| Concept | One-Line Explanation |
|---|---|
| **VPC** | Your private, isolated network in AWS — like your own data center in the cloud. |
| **Subnet** | A range of IPs within a VPC. Public subnets have a route to the internet; private ones don't. |
| **Security Group** | A virtual firewall around a resource. Rules are stateful (allow out = allow response in). |
| **Internet Gateway** | The "door" that connects your VPC to the public internet. |
| **RDS** | Managed relational database. AWS handles backups, patching, and failover. |
| **Secrets Manager** | Secure vault for credentials. Apps fetch secrets at runtime, never hardcode them. |
| **S3** | Infinitely scalable object storage. Think of it as a key-value store for files. |
| **SQS** | Message queue that decouples producers from consumers. |
| **SNS** | Pub/Sub messaging — one message, many subscribers. |
| **ECR** | Private Docker registry hosted by AWS. |
| **ECS Fargate** | Run containers without managing servers. You define CPU/RAM; AWS handles the rest. |
| **ALB** | Layer 7 load balancer that routes HTTP requests to your containers. |
| **IAM Role** | An identity with permissions that AWS services can "assume" — no passwords needed. |
| **CloudWatch Logs** | Centralized log storage. Container stdout/stderr is automatically streamed here. |
| **Terraform** | Infrastructure as Code — define your infrastructure in `.tf` files, apply/destroy with one command. |
