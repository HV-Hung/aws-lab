from fastapi import APIRouter, HTTPException, UploadFile, File
from core.aws import get_s3_client
from core.config import get_aws_config

router = APIRouter()

def get_bucket_name():
    config = get_aws_config()
    bucket = config.get("s3_bucket")
    if not bucket:
        raise HTTPException(status_code=500, detail="S3_BUCKET_NAME not configured")
    return bucket

@router.post("/upload", summary="Upload a file to S3")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to the S3 bucket."""
    s3 = get_s3_client()
    bucket = get_bucket_name()
    try:
        s3.upload_fileobj(file.file, bucket, file.filename)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files", summary="List files in S3")
def list_files():
    """List all objects in the S3 bucket."""
    s3 = get_s3_client()
    bucket = get_bucket_name()
    try:
        response = s3.list_objects_v2(Bucket=bucket)
        if "Contents" not in response:
            return {"files": []}
        files = [obj["Key"] for obj in response["Contents"]]
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{key}", summary="Get a presigned URL for a file")
def download_file(key: str):
    """Generate a presigned URL to download a file securely from S3."""
    s3 = get_s3_client()
    bucket = get_bucket_name()
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=3600
        )
        return {"download_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
