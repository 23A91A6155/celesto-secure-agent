"""Health check endpoints for control plane and container orchestration."""

from fastapi import APIRouter, Response, status
from app.schemas import HealthResponse
from app.database import check_db_health

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def health_check():
    """Liveness probe returning HTTP 200 and {"status": "ok"}."""
    return HealthResponse(status="ok")


@router.get("/health/ready")
def readiness_check(response: Response):
    """Readiness probe checking database connectivity."""
    db_ok = check_db_health()
    if db_ok:
        return {"status": "ready", "database": "healthy"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready", "database": "unreachable"}
