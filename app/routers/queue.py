from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.aws import get_sqs_client
from core.config import get_aws_config

router = APIRouter()

class Message(BaseModel):
    message: str

def get_queue_url():
    config = get_aws_config()
    queue_url = config.get("sqs_queue_url")
    if not queue_url:
        raise HTTPException(status_code=500, detail="SQS_QUEUE_URL not configured")
    return queue_url

@router.post("/send", summary="Send a message to SQS")
def send_message(msg: Message):
    """Send a plain text message to the SQS queue."""
    sqs = get_sqs_client()
    queue_url = get_queue_url()
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=msg.message
        )
        return {"status": "success", "message_id": response.get("MessageId")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/receive", summary="Receive a message from SQS")
def receive_message():
    """Poll for a message, return it, and delete it from the queue."""
    sqs = get_sqs_client()
    queue_url = get_queue_url()
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=2
        )
        messages = response.get("Messages", [])
        if not messages:
            return {"status": "no messages"}
        
        msg = messages[0]
        # Delete message after reading so it's not processed again
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=msg["ReceiptHandle"]
        )
        return {"status": "success", "body": msg["Body"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", summary="Get SQS queue stats")
def queue_stats():
    """Get the approximate number of messages currently in the queue."""
    sqs = get_sqs_client()
    queue_url = get_queue_url()
    try:
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages"]
        )
        return {"stats": response.get("Attributes")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
