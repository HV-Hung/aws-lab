"""
Configuration loader.
- Locally: reads from environment variables / .env file.
- On ECS: fetches credentials from AWS Secrets Manager at runtime.
"""

import json
import os

import boto3
from dotenv import load_dotenv

load_dotenv()


def get_db_credentials() -> dict:
    """
    Fetch database credentials.
    If DB_SECRET_ARN is set, parse it if ECS injected the JSON secret directly, 
    otherwise pull from Secrets Manager.
    """
    secret_arn_or_value = os.getenv("DB_SECRET_ARN")

    if secret_arn_or_value:
        # If ECS injected the secret string directly (starts with '{')
        if secret_arn_or_value.startswith("{"):
            return json.loads(secret_arn_or_value)
            
        # Otherwise, assume it is an ARN and fetch it
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_arn_or_value)
        return json.loads(response["SecretString"])
    else:
        # Running locally — use env vars
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "dbname": os.getenv("DB_NAME", "postgres"),
            "username": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "local"),
        }


def get_aws_config() -> dict:
    """Return common AWS config values from environment."""
    return {
        "region": os.getenv("AWS_REGION", "ap-southeast-1"),
        "s3_bucket": os.getenv("S3_BUCKET_NAME", ""),
        "sqs_queue_url": os.getenv("SQS_QUEUE_URL", ""),
        "sns_topic_arn": os.getenv("SNS_TOPIC_ARN", ""),
    }
