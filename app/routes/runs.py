"""API endpoints for managing and querying Celesto run ledger records."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import RunModel
from app.schemas import RunCreateRequest, RunResponse

router = APIRouter(prefix="/api/runs", tags=["Runs Ledger"])


@router.get("", response_model=List[RunResponse], status_code=status.HTTP_200_OK)
def list_runs(db: Session = Depends(get_db)):
    """Retrieve all recorded runs from the PostgreSQL ledger."""
    runs = db.query(RunModel).order_by(RunModel.created_at.asc()).all()
    return runs


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreateRequest, db: Session = Depends(get_db)):
    """Record a new agent run in the ledger with strict validation."""
    # Check for existing run_id to return clean HTTP 400
    existing = db.query(RunModel).filter(RunModel.run_id == payload.run_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "DuplicateRunId",
                "message": f"Run with run_id '{payload.run_id}' already exists in the ledger.",
            },
        )

    run_record = RunModel(
        run_id=payload.run_id,
        sandbox_name=payload.sandbox_name,
        problem_id=payload.problem_id,
        state=payload.state,
        execution_target=payload.execution_target,
    )

    try:
        db.add(run_record)
        db.commit()
        db.refresh(run_record)
        return run_record
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "DatabaseIntegrityError", "message": str(e.orig)},
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "DatabaseError", "message": "Failed to persist run to ledger."},
        )


@router.get("/{run_id}", response_model=RunResponse, status_code=status.HTTP_200_OK)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Retrieve a specific run by its run_id."""
    run_record = db.query(RunModel).filter(RunModel.run_id == run_id).first()
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NotFound", "message": f"Run '{run_id}' not found in ledger."},
        )
    return run_record
