"""
Shared boto3 client/resource helpers.
Centralizes AWS client creation to avoid duplication across routers.
"""

import boto3
from core.config import get_aws_config


def get_s3_client():
    """Return a boto3 S3 client."""
    config = get_aws_config()
    return boto3.client("s3", region_name=config["region"])


def get_sqs_client():
    """Return a boto3 SQS client."""
    config = get_aws_config()
    return boto3.client("sqs", region_name=config["region"])


def get_sns_client():
    """Return a boto3 SNS client."""
    config = get_aws_config()
    return boto3.client("sns", region_name=config["region"])
