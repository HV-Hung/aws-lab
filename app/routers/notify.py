from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.aws import get_sns_client
from core.config import get_aws_config

router = APIRouter()

class PublishMessage(BaseModel):
    message: str
    subject: str = "Notification from AWS Learning App"

def get_topic_arn():
    config = get_aws_config()
    topic_arn = config.get("sns_topic_arn")
    if not topic_arn:
        raise HTTPException(status_code=500, detail="SNS_TOPIC_ARN not configured")
    return topic_arn

@router.post("/publish", summary="Publish a message to SNS topic")
def publish_message(msg: PublishMessage):
    """Broadcast a message to all subscribers of the SNS topic."""
    sns = get_sns_client()
    topic_arn = get_topic_arn()
    try:
        response = sns.publish(
            TopicArn=topic_arn,
            Subject=msg.subject,
            Message=msg.message
        )
        return {"status": "success", "message_id": response.get("MessageId")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscriptions", summary="List topic subscriptions")
def list_subscriptions():
    """List all current subscriptions for this SNS topic."""
    sns = get_sns_client()
    topic_arn = get_topic_arn()
    try:
        response = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        return {"subscriptions": response.get("Subscriptions", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
