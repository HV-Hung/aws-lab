"""
AWS Learning App — FastAPI application that interacts with AWS services.
Each router corresponds to an AWS service (RDS, S3, SQS, SNS).
"""

from fastapi import FastAPI
from routers import health

# --- Phase 2: Uncomment to enable DB routes ---
from routers import db

# --- Phase 3: Uncomment to enable S3/SQS/SNS routes ---
from routers import storage, queue, notify

app = FastAPI(
    title="AWS Learning App",
    description="A Python app to interact with AWS services for learning purposes",
    version="0.1.0",
)

# --- Always available ---
app.include_router(health.router)

# --- Phase 2: Uncomment ---
app.include_router(db.router, prefix="/db", tags=["Database (RDS)"])

# --- Phase 3: Uncomment ---
app.include_router(storage.router, prefix="/s3", tags=["Storage (S3)"])
app.include_router(queue.router, prefix="/sqs", tags=["Queue (SQS)"])
app.include_router(notify.router, prefix="/sns", tags=["Notifications (SNS)"])
