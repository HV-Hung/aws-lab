# Cost Analysis

This document provides a detailed cost breakdown for this project. All prices are for the **ap-southeast-1 (Singapore)** region and represent **on-demand pricing** as of 2026.

> **Strategy**: Use `scripts/destroy.sh` to tear down all resources when not actively learning. This is the single most effective cost-saving measure.

---

## Cost Summary

### Running 24/7 (Worst Case)

| Service | Resource | Monthly Cost | Notes |
|---|---|---|---|
| **RDS** | db.t4g.micro PostgreSQL | ~$11.52 | 0.016 × 24 × 30 |
| **RDS Storage** | 20 GB gp3 | ~$2.30 | $0.115/GB-month |
| **ECS Fargate** | 0.25 vCPU + 0.5 GB | ~$8.30 | Compute + memory |
| **ALB** | Application Load Balancer | ~$16.43 | Fixed hourly + LCU |
| **ECR** | Container images | ~$0.10 | ~1 GB storage |
| **S3** | Bucket storage | ~$0.02 | Minimal test files |
| **SQS** | Message queue | ~$0.00 | First 1M requests free |
| **SNS** | Topic | ~$0.00 | First 1M publishes free |
| **Secrets Manager** | 1 secret | ~$0.40 | $0.40/secret/month |
| **CloudWatch Logs** | 7-day retention | ~$0.50 | Ingestion + storage |
| **VPC** | VPC, subnets, IGW | $0.00 | No charge for VPC itself |
| | | | |
| **TOTAL** | | **~$39.57/month** | Running 24/7 |

### Running 2 hours/day (Recommended for Learning)

| Service | Adjustment | Monthly Cost |
|---|---|---|
| **RDS** | 2 hrs × 30 days × $0.016 | ~$0.96 |
| **ECS Fargate** | 2 hrs × 30 days × $0.012 | ~$0.72 |
| **ALB** | 2 hrs × 30 days × $0.023 | ~$1.38 |
| **Others** | Minimal | ~$1.00 |
| | | |
| **TOTAL** | | **~$4.06/month** |

---

## Per-Service Cost Details

### RDS PostgreSQL

| Component | Rate | This Project |
|---|---|---|
| Instance (db.t4g.micro) | $0.016/hr | Cheapest Graviton option |
| Storage (gp3, 20 GB) | $0.115/GB-month | Minimum allocation |
| Backup | Free (1× storage) | No extra backup configured |
| Data Transfer | Free within VPC | ECS ↔ RDS is internal |

**Cost-saving decisions**:
- `db.t4g.micro` — Graviton (ARM) instances are ~20% cheaper than equivalent x86
- `skip_final_snapshot = true` — avoids orphaned snapshots after destroy
- `recovery_window_in_days = 0` for Secrets Manager — allows instant teardown

### ECS Fargate

| Component | Rate | This Project |
|---|---|---|
| vCPU | $0.04048/hr per vCPU | 0.25 vCPU = $0.01012/hr |
| Memory | $0.004445/hr per GB | 0.5 GB = $0.002223/hr |
| **Combined** | | **$0.01234/hr per task** |

**Cost-saving decisions**:
- `cpu = 256` (0.25 vCPU) — smallest allowed
- `memory = 512` (0.5 GB) — smallest allowed
- `desired_count = 1` — single task
- No NAT Gateway — tasks in public subnets with `assign_public_ip = true` saves ~$32/month

### Application Load Balancer

| Component | Rate | Notes |
|---|---|---|
| Hourly charge | $0.0225/hr | Fixed cost while ALB exists |
| LCU (Load Balancer Capacity Unit) | $0.008/LCU-hr | Based on new connections, bandwidth, rules |

> **This is the most expensive component** when running 24/7. The fixed hourly charge alone is ~$16.43/month even with zero traffic.

### S3

| Component | Rate | Notes |
|---|---|---|
| Storage | $0.025/GB-month (Standard) | Negligible for test files |
| PUT/POST | $0.005/1,000 requests | |
| GET | $0.0004/1,000 requests | |

For a learning project with a few test files, S3 cost is effectively **$0.00**.

### SQS

| Component | Rate | Notes |
|---|---|---|
| First 1M requests/month | Free | |
| After 1M | $0.40/million requests | |

For a learning project, SQS is **free**.

### SNS

| Component | Rate | Notes |
|---|---|---|
| First 1M publishes/month | Free | |
| Email delivery | $2.00/100,000 | Only if you add email subscribers |

For a learning project without subscribers, SNS is **free**.

### Secrets Manager

| Component | Rate |
|---|---|
| Per secret | $0.40/month |
| API calls | $0.05/10,000 calls |

Fixed cost of **$0.40/month** for the DB credentials secret.

### CloudWatch Logs

| Component | Rate |
|---|---|
| Ingestion | $0.50/GB |
| Storage | $0.03/GB-month |

With 7-day retention and a single container, expect **~$0.50/month**.

---

## Cost Optimization Strategies

### 1. Destroy When Not Using (Most Impactful)

```bash
# When done for the day
sh scripts/destroy.sh

# When ready to learn again
sh scripts/deploy.sh
```

This eliminates **100% of costs** when you're not actively learning.

### 2. No NAT Gateway (Already Applied)

A NAT Gateway costs **$0.045/hr + $0.045/GB** (~$32.40/month). We avoid this by:
- Placing ECS tasks in **public subnets** with `assign_public_ip = true`
- This allows containers to pull images from ECR and call AWS APIs directly

### 3. Single AZ for Non-Production

For a learning project, you could reduce to 1 AZ (1 public subnet, 1 DB subnet) to avoid cross-AZ data transfer charges. However, RDS requires at least 2 AZs for the subnet group, so the current 2-AZ setup is the minimum.

### 4. Use AWS Free Tier (If Available)

If your AWS account is less than 12 months old:
- **RDS**: 750 hours of db.t3.micro/month (not t4g, switch to t3.micro to use)
- **S3**: 5 GB storage
- **SQS**: 1M requests/month (always free)
- **SNS**: 1M publishes/month (always free)
- **CloudWatch**: 5 GB log ingestion

### 5. Spot Pricing for Fargate (Advanced)

ECS Fargate Spot can save up to **70%** on compute costs. Not configured in this project, but can be enabled by changing the capacity provider strategy.

---

## Cost Comparison: This Project vs. Alternatives

| Approach | Monthly Cost | Notes |
|---|---|---|
| **This project (2 hrs/day)** | ~$4 | Recommended for learning |
| **This project (24/7)** | ~$40 | Only if needed |
| **Same project + NAT Gateway** | ~$72 | NAT adds ~$32 |
| **Same project + db.t3.medium** | ~$80 | Larger RDS instance |
| **LocalStack (local mock)** | $0 | No real AWS experience |

---

## How to Monitor Your Costs

1. **AWS Cost Explorer**: `https://console.aws.amazon.com/cost-management/home`
2. **Billing Dashboard**: `https://console.aws.amazon.com/billing/home`
3. **Set a Budget Alert**:
   ```bash
   aws budgets create-budget --account-id $(aws sts get-caller-identity --query Account --output text) \
     --budget '{"BudgetName":"aws-learning","BudgetLimit":{"Amount":"10","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}' \
     --notifications-with-subscribers '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"your-email@example.com"}]}]'
   ```
