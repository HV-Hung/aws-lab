#!/usr/bin/env bash
# deploy.sh — Full deploy: terraform apply → docker build & push → ECS update
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Step 1: Terraform Apply ==="
cd "$PROJECT_ROOT/terraform"
terraform init -upgrade
terraform apply -auto-approve

echo ""
echo "=== Step 2: Get ECR URL ==="
ECR_URL=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "")
if [ -z "$ECR_URL" ]; then
    echo "ECR not provisioned yet (Phase 4). Skipping Docker push."
    exit 0
fi

REGION=$(terraform output -raw region 2>/dev/null || echo "ap-southeast-1")
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo ""
echo "=== Step 3: Docker Build & Push ==="
cd "$PROJECT_ROOT/app"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URL"
docker build -t aws-app .
docker tag aws-app:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

echo ""
echo "=== Step 4: Force ECS Redeployment ==="
aws ecs update-service \
    --cluster aws-learning-cluster \
    --service aws-app \
    --force-new-deployment \
    --region "$REGION" \
    --no-cli-pager

echo ""
echo "=== Done! ==="
ALB_DNS=$(cd "$PROJECT_ROOT/terraform" && terraform output -raw alb_dns_name 2>/dev/null || echo "N/A")
echo "App URL: http://$ALB_DNS"
