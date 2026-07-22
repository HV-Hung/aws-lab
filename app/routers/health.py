"""Health check router — always available, no AWS dependencies."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint. Returns 200 if the app is running."""
    return {
        "status": "ok",
        "service": "aws-learning-app",
    }
