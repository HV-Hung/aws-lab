# Troubleshooting

Common errors encountered during this project and how to resolve them.

---

## Terraform Errors

### `ClusterNotFoundException` when running `deploy.sh`

**Error**:
```
An error occurred (ClusterNotFoundException) when calling the UpdateService operation: Cluster not found.
```

**Cause**: The `deploy.sh` script was referencing `--cluster aws-learning` instead of the actual Terraform-created cluster name `aws-learning-cluster`.

**Fix**: Ensure the cluster name in `deploy.sh` matches the name in the Terraform compute module (`${var.project_name}-cluster`).

---

### `CannotPullContainerError` — Image Not Found

**Error**:
```
CannotPullContainerError: pull image manifest has been retried 7 time(s): 
failed to resolve ref ...aws-learning-repo:latest: not found
```

**Cause**: The ECS task definition references `<ECR_URL>:latest`, but no image has been pushed to ECR yet. This happens when Terraform creates the ECS service before `deploy.sh` pushes the Docker image.

**Fix**: Run `deploy.sh` to build and push the Docker image. ECS will automatically retry and eventually pick up the new image. You can also force a redeployment:

```bash
aws ecs update-service --cluster aws-learning-cluster --service aws-app --force-new-deployment
```

---

### Secret Already Exists on Re-deploy

**Error**:
```
A secret with that name already exists. Use a different name or delete the existing one.
```

**Cause**: Secrets Manager has a recovery window (default 30 days) that prevents re-creating a secret with the same name after deletion.

**Fix**: This project sets `recovery_window_in_days = 0` to allow immediate re-creation. If you still encounter this error, manually delete the secret:

```bash
aws secretsmanager delete-secret --secret-id aws-learning/db-credentials --force-delete-without-recovery
```

---

## Application Errors

### `RuntimeError: Form data requires "python-multipart"`

**Error** (in CloudWatch Logs):
```
RuntimeError: Form data requires "python-multipart" to be installed.
```

**Cause**: The S3 upload endpoint uses FastAPI's `UploadFile` which requires the `python-multipart` package to parse `multipart/form-data` requests.

**Fix**: Ensure `python-multipart>=0.0.9` is in `app/requirements.txt`, rebuild the Docker image, and redeploy.

---

### `ValidationException` — Invalid Secret Name

**Error**:
```
botocore.exceptions.ClientError: An error occurred (ValidationException) when calling 
the GetSecretValue operation: Invalid name. Must be a valid name containing alphanumeric 
characters, or any of the following: -/_+=.@!
```

**Cause**: When using the ECS Task Definition `secrets` block, ECS injects the **actual secret value** (the JSON string) into the environment variable — not the ARN. The app was then passing a JSON string like `{"username":"postgres",...}` as a `SecretId` to `GetSecretValue()`, which is not a valid secret name.

**Fix**: The app now checks if `DB_SECRET_ARN` starts with `{`. If yes, it parses the JSON directly without calling Secrets Manager. See `app/core/config.py`.

**Key Learning**:
- ECS `environment` block: injects the value as-is (plain string)
- ECS `secrets` block: ECS **resolves** the secret ARN, fetches the value, and injects the resolved value

---

### `UndefinedTable: relation "items" does not exist`

**Error**:
```
psycopg2.errors.UndefinedTable: relation "items" does not exist
```

**Cause**: The `/db/init` endpoint was not called before attempting to insert/query items. Or, the `/db/init` call failed (e.g., hit a container that was still shutting down during a deployment).

**Fix**: Call the init endpoint first:

```bash
curl -X POST http://<ALB_DNS>/db/init
```

Then verify it returns `{"status":"Database initialized successfully"}` before using other `/db` endpoints.

---

### `ECR_URL: parameter not set` in `deploy.sh`

**Error**:
```
deploy.sh: 27: ECR_URL: parameter not set
```

**Cause**: The `set -euo pipefail` flag in the script causes the script to fail when a variable is unset. If `terraform output -raw ecr_repository_url` fails (e.g., due to expired credentials), the fallback `echo ""` is still treated as an unset variable by bash's `-u` flag.

**Fix**: Refresh your AWS credentials before running the script:

```bash
# For SSO users:
eval "$(aws configure export-credentials --profile default --format env)"

# Then re-run:
sh scripts/deploy.sh
```

---

## Deployment & Docker Errors

### Docker Build Fails — Large Context

**Symptom**: Docker build transfers 60+ MB of context.

**Cause**: The `.venv` (Python virtual environment) directory is being included in the Docker build context.

**Fix**: Create `app/.dockerignore`:

```
.venv/
__pycache__/
*.pyc
.env
```

---

### ECS Tasks Keep Crashing (Restart Loop)

**Diagnosis**: Check CloudWatch Logs:

```bash
aws logs filter-log-events \
  --log-group-name "/ecs/aws-learning-app" \
  --start-time $(date -d "10 minutes ago" +%s000) \
  --query 'events[*].message' \
  --output text
```

**Common causes**:
1. Missing Python dependency → check `requirements.txt`
2. Missing environment variable → check Task Definition
3. Database not initialized → call `/db/init`
4. Secrets not accessible → check Execution Role permissions

---

### ALB Returns `503 Service Unavailable`

**Cause**: No healthy targets registered with the target group. The ECS task either hasn't started yet or is failing health checks.

**Diagnosis**:

```bash
# Check ECS service events
aws ecs describe-services \
  --cluster aws-learning-cluster \
  --services aws-app \
  --query 'services[0].events[:5]' \
  --output table

# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names aws-learning-tg \
    --query 'TargetGroups[0].TargetGroupArn' --output text)
```

**Fix**: Wait 2-3 minutes for the container to boot and pass health checks. If it keeps failing, check CloudWatch Logs.

---

## Useful Debugging Commands

```bash
# Check ECS task status
aws ecs list-tasks --cluster aws-learning-cluster --service-name aws-app

# Describe a running task
aws ecs describe-tasks --cluster aws-learning-cluster \
  --tasks $(aws ecs list-tasks --cluster aws-learning-cluster --service-name aws-app --query 'taskArns[0]' --output text)

# View recent CloudWatch logs
aws logs tail /ecs/aws-learning-app --since 10m

# Check ALB health
curl -v http://<ALB_DNS>/health

# View Terraform state
cd terraform && terraform show

# List all resources Terraform manages
cd terraform && terraform state list
```
