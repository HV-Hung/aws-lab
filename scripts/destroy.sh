#!/usr/bin/env bash
# destroy.sh — Tear down ALL AWS resources to stop incurring costs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Destroying all Terraform-managed resources ==="
echo "⚠️  This will delete EVERYTHING (VPC, RDS, ECS, ALB, S3, SQS, SNS)."
echo ""

cd "$PROJECT_ROOT/terraform"
terraform destroy -auto-approve

echo ""
echo "=== Done! ==="
echo "✅ All resources destroyed. Verify in the AWS Console that nothing remains."
echo "   Pay special attention to: EC2 > Load Balancers, RDS > Databases, ECR > Repositories"
