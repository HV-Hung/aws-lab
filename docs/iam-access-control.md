# IAM & Access Control

This document explains every layer of access control in the project: IAM roles, IAM policies, security groups, and network isolation.

---

## IAM Roles Overview

ECS Fargate uses **two distinct IAM roles** for separation of concerns. This is a critical AWS security concept:

```
┌────────────────────────────────────┐
│         ECS Task Definition        │
│                                    │
│  execution_role_arn ──► Execution  │  Used by the ECS Agent (AWS infrastructure)
│                         Role       │  to pull images, write logs, fetch secrets
│                                    │
│  task_role_arn ──────► Task Role   │  Used by your application code
│                                    │  to call S3, SQS, SNS
└────────────────────────────────────┘
```

---

## Task Execution Role

**Name**: `aws-learning-ecs-exec-role`  
**Used by**: The ECS Agent (not your code)  
**When**: Before and during container startup

### Trust Policy (Who Can Assume This Role)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Action": "sts:AssumeRole",
    "Effect": "Allow",
    "Principal": {
      "Service": "ecs-tasks.amazonaws.com"
    }
  }]
}
```

Only the `ecs-tasks.amazonaws.com` service can assume this role. No users, no other services.

### Attached Policies

| Policy | Type | Purpose |
|---|---|---|
| `AmazonECSTaskExecutionRolePolicy` | AWS Managed | Pull images from ECR, write logs to CloudWatch |
| `ecs-exec-secrets-policy` | Inline | Read the specific DB credentials secret from Secrets Manager |

### Secrets Policy (Inline) — Least Privilege

```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": ["arn:aws:secretsmanager:...:secret:aws-learning/db-credentials-*"]
}
```

This policy **only** allows reading the specific secret created by Terraform. It cannot list, create, or delete other secrets.

---

## Task Role

**Name**: `aws-learning-ecs-task-role`  
**Used by**: Your application code (the FastAPI container)  
**When**: At runtime, when the app calls AWS APIs via boto3

### Trust Policy

Same as the Execution Role — only `ecs-tasks.amazonaws.com` can assume it.

### Inline Policy — Per-Service Permissions

The Task Role follows the **principle of least privilege**. Each AWS service has only the specific actions needed:

#### S3 Permissions

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::aws-learning-bucket-*",
    "arn:aws:s3:::aws-learning-bucket-*/*"
  ]
}
```

| Action | Used By | Purpose |
|---|---|---|
| `s3:PutObject` | `POST /s3/upload` | Upload files |
| `s3:GetObject` | `GET /s3/download/{key}` | Generate presigned URLs |
| `s3:ListBucket` | `GET /s3/files` | List objects in bucket |

**Not granted**: `s3:DeleteObject`, `s3:DeleteBucket`, `s3:PutBucketPolicy` — the app cannot delete files or change bucket settings.

#### SQS Permissions

```json
{
  "Effect": "Allow",
  "Action": [
    "sqs:SendMessage",
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:GetQueueAttributes"
  ],
  "Resource": ["arn:aws:sqs:...:aws-learning-queue"]
}
```

| Action | Used By | Purpose |
|---|---|---|
| `sqs:SendMessage` | `POST /sqs/send` | Send messages to queue |
| `sqs:ReceiveMessage` | `GET /sqs/receive` | Poll for messages |
| `sqs:DeleteMessage` | `GET /sqs/receive` | Remove message after processing |
| `sqs:GetQueueAttributes` | `GET /sqs/stats` | Get approximate message count |

**Not granted**: `sqs:PurgeQueue`, `sqs:DeleteQueue`, `sqs:SetQueueAttributes` — the app cannot purge, delete, or reconfigure the queue.

#### SNS Permissions

```json
{
  "Effect": "Allow",
  "Action": [
    "sns:Publish",
    "sns:ListSubscriptionsByTopic"
  ],
  "Resource": ["arn:aws:sns:...:aws-learning-topic"]
}
```

| Action | Used By | Purpose |
|---|---|---|
| `sns:Publish` | `POST /sns/publish` | Broadcast messages |
| `sns:ListSubscriptionsByTopic` | `GET /sns/subscriptions` | List active subscriptions |

**Not granted**: `sns:Subscribe`, `sns:Unsubscribe`, `sns:DeleteTopic`, `sns:SetTopicAttributes` — the app cannot manage subscriptions or delete the topic.

---

## Security Groups (Network-Level Access Control)

Security groups act as virtual firewalls at the network level, controlling which traffic is allowed in and out of each resource.

### Chain Architecture

```
Internet ──► ALB-SG ──► ECS-SG ──► RDS-SG
  (anyone)    (HTTP)     (app port)  (postgres)
```

### ALB Security Group (`aws-learning-alb-sg`)

| Direction | Port | Source | Purpose |
|---|---|---|---|
| **Inbound** | 80 (TCP) | `0.0.0.0/0` | HTTP from anywhere |
| **Inbound** | 443 (TCP) | `0.0.0.0/0` | HTTPS from anywhere |
| **Outbound** | All | `0.0.0.0/0` | Allow all outbound |

### ECS Security Group (`aws-learning-ecs-sg`)

| Direction | Port | Source | Purpose |
|---|---|---|---|
| **Inbound** | 8000 (TCP) | `alb-sg` (SG reference) | App traffic from ALB **only** |
| **Outbound** | All | `0.0.0.0/0` | AWS API calls, ECR pull, etc. |

> **Key Point**: Inbound uses a **security group reference**, not a CIDR block. This means even if someone knows the container's public IP, they cannot reach port 8000 directly — only traffic originating from the ALB security group is allowed.

### RDS Security Group (`aws-learning-rds-sg`)

| Direction | Port | Source | Purpose |
|---|---|---|---|
| **Inbound** | 5432 (TCP) | `ecs-sg` (SG reference) | PostgreSQL from ECS **only** |
| **Outbound** | All | `0.0.0.0/0` | Allow all outbound |

> **Key Point**: The database is **doubly protected**:
> 1. It is in an **isolated subnet** with no internet route
> 2. Its security group only allows port 5432 from the ECS security group

---

## Network Isolation

### Public Subnets (ALB + ECS)
- Have a route to the Internet Gateway (`0.0.0.0/0 → IGW`)
- ECS tasks get `assign_public_ip = true` (needed to pull images from ECR without a NAT Gateway)

### Database Subnets (RDS)
- **No route to the Internet Gateway**
- Route table is empty (only local VPC routes)
- RDS has `publicly_accessible = false`

This means:
- ✅ ECS → RDS (within VPC, allowed by SG)
- ❌ Internet → RDS (no route, no SG rule, not publicly accessible)
- ❌ RDS → Internet (no route in its route table)

---

## What Each Entity Can Do — Summary Matrix

| Entity | Can Access | Cannot Access |
|---|---|---|
| **Internet User** | ALB (HTTP:80) | ECS directly, RDS, S3, SQS, SNS |
| **ALB** | ECS (port 8000) | RDS, S3, SQS, SNS |
| **ECS Container** | RDS (port 5432), S3, SQS, SNS (via IAM) | Secrets Manager (only Execution Role can) |
| **ECS Agent** | ECR (pull images), CloudWatch (logs), Secrets Manager | S3, SQS, SNS |
| **RDS** | Nothing outbound (isolated) | Internet, other AWS services |
