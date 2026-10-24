"""FastAPI Application Entrypoint for Celesto Secure Agent Control Plane."""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.routes.health import router as health_router
from app.routes.runs import router as runs_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("celesto.control_plane")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager handling startup and shutdown events."""
    logger.info("Initializing Celesto Secure Agent Control Plane...")
    try:
        init_db()
        logger.info("Database schema and initial seed verified.")
    except Exception as e:
        logger.warning(
            f"Database initialization deferred or running in fallback mode: {e}"
        )
    yield
    logger.info("Shutting down Celesto Secure Agent Control Plane...")


app = FastAPI(
    title="Celesto Secure Agent Run Ledger & Control Plane",
    description="Trusted control plane managing isolated Celesto microVM execution, command auditing, and run records.",
    version="1.0.0",
    lifespan=lifespan,
)

# Custom validation error handler to ensure clear JSON 400 responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg", ""), "type": err.get("type", "")}
        for err in exc.errors()
    ]
    messages = [f"{err.get('loc', ['field'])[-1]}: {err.get('msg', '')}" for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "ValidationError",
            "message": "; ".join(messages),
            "details": details,
        },
    )


# Include routes
app.include_router(health_router)
app.include_router(runs_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.API_PORT, reload=False)
