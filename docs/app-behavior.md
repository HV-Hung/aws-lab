# App Behavior

The FastAPI application exposes REST endpoints that interact with AWS services. Each router maps to a specific AWS service.

**Base URL**: `http://<ALB_DNS_NAME>` (e.g., `http://aws-learning-alb-xxx.elb.amazonaws.com`)

**Interactive API Docs**: Visit `http://<ALB_DNS_NAME>/docs` for Swagger UI.

---

## Health Check

### `GET /health`

Used by the ALB target group to determine if the container is healthy.

```bash
curl http://<ALB_DNS>/health
```

**Response** (`200 OK`):
```json
{"status": "ok", "service": "aws-learning-app"}
```

---

## Database (RDS PostgreSQL) — `/db/*`

**File**: `app/routers/db.py`

These endpoints demonstrate CRUD operations against a managed PostgreSQL database. The app connects using credentials fetched from AWS Secrets Manager.

### `POST /db/init` — Initialize Database

Creates the `items` table if it doesn't exist. **Must be called once** before using other `/db` endpoints.

```bash
curl -X POST http://<ALB_DNS>/db/init
```

**Response** (`200 OK`):
```json
{"status": "Database initialized successfully"}
```

### `POST /db/items` — Create an Item

```bash
curl -X POST http://<ALB_DNS>/db/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "description": "MacBook Pro 16-inch"}'
```

**Request Body**:
| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | Item name |
| `description` | string | ❌ | Optional description |

**Response** (`200 OK`):
```json
{"id": 1, "name": "Laptop", "description": "MacBook Pro 16-inch"}
```

### `GET /db/items` — List All Items

```bash
curl http://<ALB_DNS>/db/items
```

**Response** (`200 OK`):
```json
[
  {"id": 1, "name": "Laptop", "description": "MacBook Pro 16-inch"},
  {"id": 2, "name": "Mouse", "description": null}
]
```

### `DELETE /db/items/{item_id}` — Delete an Item

```bash
curl -X DELETE http://<ALB_DNS>/db/items/1
```

**Response** (`200 OK`):
```json
{"status": "Item deleted", "id": 1}
```

**Error** (`404 Not Found`):
```json
{"detail": "Item not found"}
```

---

## Object Storage (S3) — `/s3/*`

**File**: `app/routers/storage.py`

These endpoints demonstrate file upload, listing, and secure download via presigned URLs.

### `POST /s3/upload` — Upload a File

Uses `multipart/form-data` to upload a file to the S3 bucket.

```bash
echo "Hello AWS!" > test.txt
curl -X POST http://<ALB_DNS>/s3/upload -F "file=@test.txt"
```

**Response** (`200 OK`):
```json
{"status": "success", "filename": "test.txt"}
```

### `GET /s3/files` — List All Files

```bash
curl http://<ALB_DNS>/s3/files
```

**Response** (`200 OK`):
```json
{"files": ["test.txt", "photo.jpg"]}
```

**Response** (empty bucket):
```json
{"files": []}
```

### `GET /s3/download/{key}` — Get a Presigned Download URL

Generates a temporary URL (valid for 1 hour) to download a file from S3 without needing AWS credentials.

```bash
curl http://<ALB_DNS>/s3/download/test.txt
```

**Response** (`200 OK`):
```json
{"download_url": "https://aws-learning-bucket-tvivgu.s3.amazonaws.com/test.txt?X-Amz-..."}
```

---

## Message Queue (SQS) — `/sqs/*`

**File**: `app/routers/queue.py`

These endpoints demonstrate producer-consumer messaging with SQS.

### `POST /sqs/send` — Send a Message

```bash
curl -X POST http://<ALB_DNS>/sqs/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Process order #12345"}'
```

**Response** (`200 OK`):
```json
{"status": "success", "message_id": "a1b2c3d4-..."}
```

### `GET /sqs/receive` — Receive and Delete a Message

Polls the queue for 1 message (2-second wait), returns it, and immediately deletes it so it won't be processed again.

```bash
curl http://<ALB_DNS>/sqs/receive
```

**Response** (`200 OK` — message found):
```json
{"status": "success", "body": "Process order #12345"}
```

**Response** (`200 OK` — queue empty):
```json
{"status": "no messages"}
```

### `GET /sqs/stats` — Get Queue Statistics

```bash
curl http://<ALB_DNS>/sqs/stats
```

**Response** (`200 OK`):
```json
{"stats": {"ApproximateNumberOfMessages": "3"}}
```

---

## Pub/Sub Notifications (SNS) — `/sns/*`

**File**: `app/routers/notify.py`

These endpoints demonstrate publish/subscribe messaging with SNS.

### `POST /sns/publish` — Publish a Message

Broadcasts a message to all subscribers of the SNS topic.

```bash
curl -X POST http://<ALB_DNS>/sns/publish \
  -H "Content-Type: application/json" \
  -d '{"message": "Server CPU at 95%!", "subject": "Alert"}'
```

**Request Body**:
| Field | Type | Required | Default |
|---|---|---|---|
| `message` | string | ✅ | — |
| `subject` | string | ❌ | `"Notification from AWS Learning App"` |

**Response** (`200 OK`):
```json
{"status": "success", "message_id": "x1y2z3-..."}
```

> **Note**: Without any active subscriptions, the message is published but not delivered anywhere. To receive messages, add an email or SQS subscription via the AWS Console or CLI.

### `GET /sns/subscriptions` — List Topic Subscriptions

```bash
curl http://<ALB_DNS>/sns/subscriptions
```

**Response** (`200 OK`):
```json
{"subscriptions": []}
```

---

## Application Startup Behavior

1. **`load_dotenv()`** is called to load `.env` file (local development only)
2. **Routers are imported** — if any dependency is missing (e.g., `python-multipart`), the app crashes at import time
3. **FastAPI app is created** with title, description, and version
4. **Routers are registered** with URL prefixes (`/db`, `/s3`, `/sqs`, `/sns`)
5. **Uvicorn starts** listening on `0.0.0.0:8000`

### Configuration Detection Logic

The app uses a dual-mode configuration system (`app/core/config.py`):

```
Is DB_SECRET_ARN set?
├── YES → Does the value start with '{'?
│         ├── YES → Parse as JSON directly (ECS injected the secret)
│         └── NO  → Treat as ARN, call Secrets Manager API
└── NO  → Use local env vars (DB_HOST, DB_PORT, etc.)
```

This allows the same codebase to run both locally and on ECS without any code changes.

---

## Error Handling

All routers follow this pattern:

- **`500 Internal Server Error`**: Unexpected errors (database connection failures, AWS API errors). The error message is returned in the `detail` field.
- **`404 Not Found`**: Resource not found (e.g., deleting a non-existent item).
- **FastAPI auto-validates** request bodies using Pydantic models and returns `422 Unprocessable Entity` for invalid input.
